import copy
import json
import unittest
from pathlib import Path
from src.gate import check_assessment, digest, make_audit, make_source, markdown

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / 'fixtures' / 'safe.json').read_text())


class EvidenceGateTests(unittest.TestCase):
    def test_safe(self):
        self.assertEqual(check_assessment(fixture())['status'], 'PASS')

    def test_unknown_source(self):
        d = fixture(); d['findings'][0]['citations'][0]['source_id'] = 'missing'
        self.assertIn('MISSING_EVIDENCE', codes(d))

    def test_bad_quote(self):
        d = fixture(); d['findings'][0]['citations'][0]['quote'] = 'Invented rule that does not exist'
        self.assertIn('BAD_QUOTE', codes(d))

    def test_wrong_version(self):
        d = fixture(); d['findings'][0]['citations'][0]['source_version'] = 'v0'
        self.assertIn('MISSING_POLICY_VERSION', codes(d))

    def test_stale_policy(self):
        d = fixture(); d['assessment_date'] = '2026-10-21'
        d['sources'][0]['effective_to'] = '2025-12-31'
        d['sources'][0]['sha256'] = digest({k:v for k,v in d['sources'][0].items() if k != 'sha256'})
        self.assertIn('STALE_POLICY', codes(d))

    def test_wrong_jurisdiction(self):
        d = fixture(); d['jurisdiction'] = 'Scotland'
        self.assertIn('WRONG_JURISDICTION', codes(d))

    def test_tampered_evidence(self):
        d = fixture(); d['sources'][0]['text'] = 'changed'
        self.assertIn('INVALID_SOURCE_HASH', codes(d))

    def test_missing_signoff(self):
        d = fixture(); d['human_signoff']['approved'] = False
        self.assertIn('NO_HUMAN_SIGNOFF', codes(d))

    def test_bad_approver_role(self):
        d = fixture(); d['human_signoff']['role'] = 'ai_agent'
        self.assertIn('INVALID_OFFICER_ROLE', codes(d))

    def test_broken_audit_chain(self):
        d = fixture(); d['audit_events'][0]['action'] = 'silently_changed'
        self.assertIn('INCOMPLETE_AUDIT', codes(d))

    def test_missing_review_event(self):
        d = fixture(); d['audit_events'] = make_audit(['approved'])
        self.assertIn('INCOMPLETE_AUDIT', codes(d))

    def test_empty_findings(self):
        d = fixture(); d['findings'] = []
        self.assertIn('UNSUPPORTED_FINDING', codes(d))

    def test_duplicate_source_ids(self):
        d = fixture(); d['sources'].append(copy.deepcopy(d['sources'][0]))
        self.assertIn('DUPLICATE_SOURCE', codes(d))

    def test_deterministic_report(self):
        d = fixture(); self.assertEqual(check_assessment(d)['report_sha256'], check_assessment(d)['report_sha256'])

    def test_markdown(self):
        self.assertIn('PASS', markdown(check_assessment(fixture())))


def codes(data):
    return {x['code'] for x in check_assessment(data)['issues']}


if __name__ == '__main__':
    unittest.main()
