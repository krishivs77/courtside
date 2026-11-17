# Player Analytics Implementation Plan

Goal: Repair historical ingestion and deliver database-backed player analytics.
Architecture: Keep nba_api retrieval separate from transactional persistence; expose bounded chronological game logs in FastAPI; render a Recharts dashboard through the existing Next.js server proxy.
Spec: User-supplied COURTSIDE continuation brief (2026-11-17).

Constraints: Preserve existing records and explorers. No fabricated statistics, secrets, paid services, or volume resets. Use a feature branch and meaningful commits.

1. Add importer regression tests for home/away parsing, missing/invalid stats, minutes, rollback and repeat imports. Add explicit date/provenance fields via migration. Fetch Curry 2025-26 logs, verify PostgreSQL and repeat safety. Commit ingestion milestone.
2. Add typed player detail and game-log routes (internal database player IDs), latest bounded window ordered chronologically, season filter and offset. Test known/unknown/empty histories, bounds and opponent joins. Commit API milestone.
3. Add individual player route, proxy, loading/error/empty states, real game table, metric charts and trailing averages with 5/10/20 windows. Link player cards. Run lint, types and build. Commit web milestone.
4. Run full checks and live integration smoke checks, review changes, document upstream limitations and push feature branch for a PR.

Review focus: Upstream failure must not mutate data; missing stats must not become zeros; latest windows must use dates rather than source order; overlapping imports must retain one shared game; date-only source data must never be presented as verified tipoff times.

Execution: Inline, as requested in the brief; implementation choices follow the existing stack.
