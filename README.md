# Stratum-inspired Flood Evidence Gate

**Independent technical demonstration, not affiliated with Stratum. Synthetic data only. NOT a flood-risk assessment, regulatory interpretation, planning advice, or professional sign-off.**

## Observed product problem

Stratum describes its Flood-Review/Flood-Agent workflows as agentic AI producing *cited, auditable* flood-risk assessment outputs while keeping qualified human officers in control. Its Founding Engineer description explicitly mentions production agent workflows, Python/GCP and regulatory-grade precision. This demonstration explores one narrow production reliability concern: **how can a CI/CD release gate detect broken provenance, stale or mismatched policy sources, invented citations, and missing human approval in a model-generated assessment?**

Sources (retrieved 21 October 2026):
- https://uk.linkedin.com/company/stratum-tech
- https://www.jackandjill.ai/jobs/engineer/founding-software-engineer-100k-equity-at-stratum-4ae9fc8c-7893-4f19-aa81-e76da3e2a98f
- https://geovation.uk/startups/stratum/

## Assumptions

- Inputs are structured JSON from an upstream retrieval + generation workflow.
- Policy sources are **fictional**, versioned and hash-pinned; the gate does not fetch or interpret real legislation.
- An officer has reviewed the findings externally; the demonstration only validates recorded sign-off fields, not the officer's identity.
- A successful gate is **necessary but not sufficient** for safe deployment or a lawful planning decision.

## Architecture

```text
Synthetic agent output + source registry
              |
              v
       deterministic gate
       |  |  |  |  |
       |  |  |  |  +-- human sign-off and hash-chained audit
       |  |  |  +----- source validity on assessment date
       |  |  +-------- jurisdiction and version match
       |  +----------- exact citation quote grounding
       +-------------- immutable source SHA-256 check
              |
              v
       JSON/Markdown report + nonzero exit status
              |
              v
       CI/CD release gate (GitHub Actions)
```

All checks are offline and deterministic; no API keys, packages, network, proprietary data or LLM calls are required. The CLI returns **0** for PASS and **2** for FAIL. Reports include a SHA-256 fingerprint.

## Run

Requires Python 3.10+.

```bash
python -m unittest discover -s tests -v
python -m src.gate fixtures/safe.json --out out/safe
python -m src.gate fixtures/unsafe.json --out out/unsafe  # intentionally exits 2
cat out/safe/report.md
cat out/unsafe/report.md
```

`make_fixtures.py` regenerates the deterministic sample fixtures.

## Key tradeoffs

- **Exact quote matching** is fast and reproducible, but will reject legitimate paraphrases and cannot establish semantic support. In production, pair retrieval provenance with human review and a separately calibrated entailment evaluation.
- **Local hash chain** demonstrates tamper detection but not tamper resistance against an attacker who can rewrite all events. Persist append-only records in independently controlled storage with signing and trusted timestamps.
- **Source hash** pins source content but does not verify provenance or authenticity. Production needs trusted source ingestion, signed snapshots, licences and version histories.
- **Static allowlist for officer roles** is not identity verification. Production requires RBAC, SSO, authentication, separation of duties and audit retention.
- **Fail closed** intentionally sacrifices availability to protect decisions with regulatory implications.

## Deliberately excluded (2–3 hour maximum scope)

No hydrology modelling, geospatial calculations, Ordnance Survey/Environment Agency APIs, real flood policy, OCR/PDF parsing, GCP deployment, LLM agent, RAG, semantic citation verification, live regulatory data or real human-signature service. No claims about Stratum's internal implementation are made.

## Production roadmap

1. Ingest verified, licensed geospatial and policy datasets with provenance, versioning and freshness SLAs.
2. Separate agent retrieval/generation from an independent evaluation service and human decision workflow.
3. Evaluate *semantic support* and citation coverage using gold-standard examples reviewed by flood-risk professionals; track false positives and false negatives.
4. Persist tamper-evident audit records in WORM/object-lock storage; sign decision artifacts and officer approvals.
5. Add tenant isolation, least-privilege access, PII controls, secure secrets and threat modelling.
6. Deploy stateless validator to Cloud Run; queue jobs in Pub/Sub; use Postgres for durable assessments and a controlled rollout strategy.
7. Instrument error rates, invalid citation frequency, human override rates, latency and evaluation drift; test rollback and replay.

## Interview discussion

A CTO should challenge the false confidence of a deterministic citation gate. Passing proves the *quoted text exists in the pinned fictional source*, not that the engineering claim is correct. The production engineering challenge is combining provenance, semantic evaluations, licensed data, expert oversight and defensible audit trails.
