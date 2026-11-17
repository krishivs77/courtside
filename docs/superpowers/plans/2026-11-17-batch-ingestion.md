# Batch ingestion and quality reporting

Goal: Expand real player coverage with resumable, rate-limited imports and honest quality reporting.

Architecture: Reuse transactional single-player persistence; separate NBA retrieval; persist an atomic JSON checkpoint containing season, frozen active-player cohort and per-player outcomes. Report observed source/database ID differences and data-quality issues without claiming independent completeness.

1. Test retry behavior, interruption/resume, empty/error outcomes, source ID reconciliation, and checkpoint validation.
2. Add retrieval helper and batch CLI: current bundled active cohort or explicit NBA IDs; sequential requests; bounded retries/backoff; atomic checkpoint after each result; resume successes; force refresh; stop after consecutive upstream failures. No credentials in state.
3. Add database quality report CLI: per-player counts/date range, missing minutes/provenance, invalid shot/count/team values; checkpoint outcomes and source-ID differences. JSON output suitable for automation.
4. Run isolated PostgreSQL tests, full project checks, live small batch then expanded bounded batch if upstream remains healthy. Verify repeat resume and real records. Commit meaningful milestones and open a PR, preserving main.

Constraints: $0 additional services; never reset data or volumes; source cohort is current bundled active-player metadata, not a season roster. Empty responses are explicit and not certified zero-game seasons. Checkpoints do not substitute for database reconciliation.
