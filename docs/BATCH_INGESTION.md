# Batch ingestion and data-quality reports

The batch CLI imports real regular-season PlayerGameLog responses sequentially, reusing the single-player transaction and upserts. No additional services or paid APIs are required.

## Start or resume

Start PostgreSQL with `make db`. In the repository root, load your environment, then enter the API directory:

```sh
set -a
source .env
set +a
cd apps/api
```

Start a small explicit cohort using NBA external player IDs:

```sh
.venv/bin/python -m scripts.batch_import_game_logs \
  --players 201939 2544 203999 --season 2025-26 \
  --checkpoint ../../data/ingestion/pilot-2025-26.json
```

Omit `--players` to use the bundled `nba_api` current active-player directory. `--limit 10` limits the initial cohort for a small trial; omit it for all active identities. The checkpoint freezes the target list. On resume, that saved list is reused even if the installed directory changes. A changed season or explicitly changed cohort requires another checkpoint file. Seed identities with `python -m scripts.seed_players` if preflight reports missing players.

Rerun the same command after interruption. Successful/empty outcomes are skipped only after their saved source game IDs match those currently stored for that player and season. Missing/restored records trigger a refetch. Error and pending targets retry. A crash between database commit and checkpoint save is safe: the next run upserts the same rows again. `--refresh` refetches successful and empty outcomes too, for upstream corrections or additional games; it restarts that refresh across the cohort if interrupted.

Defaults: one-second pause between players, two retries (three attempts total), exponential retry backoff, and a stop after three consecutive exhausted upstream failures. Validation/database failures are recorded without automatic retries, allowing other players to proceed. Error messages in checkpoints omit exception details that could contain credentials. Investigate rejected inputs/schema using the single-player importer; raw exception details are not retained by the batch command.

The checkpoint is atomically replaced after each outcome, and a local lock prevents two processes using the same file simultaneously. Use one checkpoint per cohort/season and one batch writer at a time for the same data. Keep the JSON and its lock in place to resume; `.lock` files may remain after exit and are harmless. Local checkpoints, logs, and reports under `data/ingestion/` are ignored by Git. They are operational state, not a database backup.

## Report coverage and quality

After the batch exits:

```sh
.venv/bin/python -m scripts.ingestion_quality --season 2025-26 \
  --checkpoint ../../data/ingestion/pilot-2025-26.json \
  --output ../../data/ingestion/pilot-quality.json
```

The JSON includes per-player stored appearance counts/date ranges; missing minutes, source dates, and provenance; invalid counts/shooting relationships/non-finite minutes/team assignments; target success/empty/error/pending counts; and missing/unexpected database game IDs compared with the latest successful or empty response. The report includes all stored players for that season, with non-target players marked `untracked`. Without a checkpoint, it audits stored rows only.

Batch exit code 1 means failures or unattempted targets remain. Report exit code 1 means errors, pending targets, invalid stat rows, or source/database ID mismatches exist. Missing metadata/minutes and empty outcomes remain explicit warnings in JSON rather than fabricated values. Report output must use a different file from the checkpoint. Run the report after ingestion finishes for a stable comparison.

## Interpretation limits

- The bundled active directory is a current metadata snapshot, **not the 2025–26 season roster**. It may omit retired participants or include players with no appearances that season.
- `success` means a returned response was persisted, not that the upstream supplied a complete season. `empty` is an observed empty response, not proof of a zero-game season.
- Source-ID reconciliation catches persistence/restore differences; independent completeness is always reported as unverified. It cannot detect an upstream response that is consistently incomplete.
- Upserts preserve records absent from a later response. Unexpected stored game IDs are reported for investigation; no records are automatically deleted.
- Resume compares IDs, so same-ID stat corrections require `--refresh`.

## Tests

`RUN_POSTGRES_TESTS=1 make test` runs retry/resume/interruption/circuit-breaker/locking/checkpoint tests, isolated PostgreSQL reconciliation tests, and the existing API/web checks. Integration fixtures use disposable UUID schemas and never reset application tables or volumes.
