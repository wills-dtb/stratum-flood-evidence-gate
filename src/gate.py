"""Synthetic flood-assessment evidence gate. Not engineering or planning advice."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Any

OFFICER_ROLES = {'lead_local_flood_authority_officer', 'chartered_flood_engineer'}
FATAL_CODES = {'MISSING_EVIDENCE', 'BAD_QUOTE', 'STALE_POLICY', 'WRONG_JURISDICTION',
               'INVALID_SOURCE_HASH', 'UNSUPPORTED_FINDING', 'NO_HUMAN_SIGNOFF',
               'INVALID_OFFICER_ROLE', 'MISSING_POLICY_VERSION', 'INCOMPLETE_AUDIT'}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def make_source(source_id: str, version: str, text: str, jurisdiction: str,
                effective_from: str, effective_to: str | None = None) -> dict:
    base = dict(id=source_id, version=version, text=text, jurisdiction=jurisdiction,
                effective_from=effective_from, effective_to=effective_to)
    return {**base, 'sha256': digest(base)}


def source_content(source: dict) -> dict:
    return {key: source[key] for key in ('id', 'version', 'text', 'jurisdiction',
                                          'effective_from', 'effective_to')}


def issue(code: str, path: str, explanation: str) -> dict:
    return dict(code=code, path=path, explanation=explanation, severity='blocker')


def check_assessment(data: dict) -> dict:
    """Fail-closed validation of generated findings and a human approval trail.

    Inputs are untrusted. Validation does not establish substantive engineering truth.
    """
    issues = []
    sources = {s.get('id'): s for s in data.get('sources', []) if s.get('id')}
    when = data.get('assessment_date', '')
    jurisdiction = data.get('jurisdiction', '')
    try:
        assessment_day = date.fromisoformat(when)
    except (TypeError, ValueError):
        assessment_day = None
        issues.append(issue('INVALID_DATE', 'assessment_date', 'Assessment date must be ISO 8601.'))
    if len(sources) != len(data.get('sources', [])):
        issues.append(issue('DUPLICATE_SOURCE', 'sources', 'Source IDs must be unique and nonempty.'))
    for idx, source in enumerate(data.get('sources', [])):
        path = f'sources[{idx}]'
        try:
            if digest(source_content(source)) != source.get('sha256'):
                issues.append(issue('INVALID_SOURCE_HASH', path, 'Evidence changed after hashing.'))
        except KeyError:
            issues.append(issue('INVALID_SOURCE_HASH', path, 'Missing required source fields.'))
        if not source.get('version'):
            issues.append(issue('MISSING_POLICY_VERSION', path, 'Source version required.'))
        if source.get('jurisdiction') != jurisdiction:
            issues.append(issue('WRONG_JURISDICTION', path, 'Source jurisdiction differs from assessment.'))
        try:
            start = date.fromisoformat(source['effective_from'])
            end = date.fromisoformat(source['effective_to']) if source.get('effective_to') else None
            if assessment_day and (assessment_day < start or (end and assessment_day > end)):
                issues.append(issue('STALE_POLICY', path, 'Policy not effective on assessment date.'))
        except (ValueError, TypeError, KeyError):
            issues.append(issue('STALE_POLICY', path, 'Policy effective dates invalid.'))
    findings = data.get('findings', [])
    if not findings:
        issues.append(issue('UNSUPPORTED_FINDING', 'findings', 'At least one finding required.'))
    for idx, finding in enumerate(findings):
        path = f'findings[{idx}]'
        citations = finding.get('citations', [])
        if not finding.get('statement') or not citations:
            issues.append(issue('UNSUPPORTED_FINDING', path, 'Finding needs a statement and citation.'))
        for ci, citation in enumerate(citations):
            cp = f'{path}.citations[{ci}]'
            source = sources.get(citation.get('source_id'))
            if source is None:
                issues.append(issue('MISSING_EVIDENCE', cp, 'Cited source does not exist.'))
                continue
            if citation.get('source_version') != source.get('version'):
                issues.append(issue('MISSING_POLICY_VERSION', cp, 'Citation must pin the exact source version.'))
            quote = citation.get('quote', '')
            if not isinstance(quote, str) or len(quote.strip()) < 8 or quote not in source.get('text', ''):
                issues.append(issue('BAD_QUOTE', cp, 'Quote must match the cited source exactly.'))
    signoff = data.get('human_signoff', {})
    if not signoff.get('approved') or not signoff.get('officer_id') or not signoff.get('signed_at'):
        issues.append(issue('NO_HUMAN_SIGNOFF', 'human_signoff', 'Human approval and identity required.'))
    if signoff.get('role') not in OFFICER_ROLES:
        issues.append(issue('INVALID_OFFICER_ROLE', 'human_signoff.role', 'Approver must have an allowed professional role.'))
    # Hash-chain integrity; events should be persisted externally in production.
    previous = 'GENESIS'
    events = data.get('audit_events', [])
    if len(events) < 2 or [e.get('action') for e in events[-2:]] != ['reviewed', 'approved']:
        issues.append(issue('INCOMPLETE_AUDIT', 'audit_events', 'Audit must end with reviewed -> approved.'))
    for idx, event in enumerate(events):
        payload = {k: v for k, v in event.items() if k != 'hash'}
        if event.get('previous_hash') != previous or event.get('hash') != digest(payload):
            issues.append(issue('INCOMPLETE_AUDIT', f'audit_events[{idx}]', 'Audit hash-chain broken.'))
        previous = event.get('hash', '')
    report = dict(assessment_id=data.get('assessment_id'), status='FAIL' if issues else 'PASS',
                  issues=issues, finding_count=len(findings), evidence_count=len(sources),
                  audit_tip=previous, ruleset_version='0.1.0-synthetic')
    report['report_sha256'] = digest(report)
    return report


def make_audit(actions: list[str]) -> list[dict]:
    chain = []
    previous = 'GENESIS'
    for i, action in enumerate(actions):
        event = dict(sequence=i + 1, action=action, actor='officer-demo',
                     previous_hash=previous)
        event['hash'] = digest(event)
        chain.append(event)
        previous = event['hash']
    return chain


def markdown(report: dict) -> str:
    lines = [f"# Evidence gate: {report['status']}", '',
             f"Assessment: `{report['assessment_id']}`",
             f"Findings: {report['finding_count']} | Sources: {report['evidence_count']}",
             f"Report SHA-256: `{report['report_sha256']}`", '', '## Issues', '']
    lines += [f"- **{x['code']}** `{x['path']}` — {x['explanation']}" for x in report['issues']] or ['No gate violations detected.']
    lines += ['', '> A passing gate does not verify hydrology, regulatory compliance, or engineering safety.']
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description='Deterministic synthetic assessment evidence gate')
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', type=Path, default=Path('out'))
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding='utf-8'))
    report = check_assessment(data)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (args.out / 'report.md').write_text(markdown(report), encoding='utf-8')
    print(f"{report['status']}: {len(report['issues'])} issues; {args.out / 'report.md'}")
    return 0 if report['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
