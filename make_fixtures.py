import json
from pathlib import Path
from src.gate import make_source, make_audit
root = Path(__file__).parent / 'fixtures'
source = make_source('POLICY-DEMO-01', 'v1',
    'For this fictional example, the applicant must provide an explicit surface water drainage plan before approval.',
    'England', '2025-01-01', '2027-12-31')
safe = {
    'assessment_id': 'SYNTHETIC-001', 'assessment_date': '2026-10-21', 'jurisdiction': 'England',
    'sources': [source],
    'findings': [{'statement': 'Request a surface water drainage plan.',
                  'citations': [{'source_id': 'POLICY-DEMO-01', 'source_version': 'v1',
                                 'quote': 'the applicant must provide an explicit surface water drainage plan'}]}],
    'human_signoff': {'approved': True, 'officer_id': 'officer-demo',
                      'role': 'lead_local_flood_authority_officer', 'signed_at': '2026-10-21T08:00:00Z'},
    'audit_events': make_audit(['reviewed', 'approved'])
}
(root / 'safe.json').write_text(json.dumps(safe, indent=2) + '\n')
unsafe = json.loads(json.dumps(safe))
unsafe['assessment_id'] = 'SYNTHETIC-002'
unsafe['findings'][0]['citations'][0]['quote'] = 'a hallucinated quote'
unsafe['human_signoff']['approved'] = False
unsafe['audit_events'][1]['action'] = 'approved_without_review'
(root / 'unsafe.json').write_text(json.dumps(unsafe, indent=2) + '\n')
