# Player analytics

## Run and import

Use `make dev` for PostgreSQL, FastAPI and Next.js. Before using this feature on an existing database, load the root `.env` in your shell and run `cd apps/api && .venv/bin/alembic upgrade head`.

From `apps/api` with `DATABASE_URL` set:

```sh
.venv/bin/python -m scripts.import_game_logs --player 201939 --season 2025-26
```

Seed teams and player identities first. This command fetches NBA.com PlayerGameLog regular-season appearances and commits the entire response atomically. An unavailable upstream or invalid/missing counting statistic fails without persisting partial imports. Repeating a successful import updates the existing game and player/game records. No statistics are inferred as zero. Missing minutes remain null.

Source matchup strings identify the player's represented team, not their current team. `game_date` retains the source calendar date. `scheduled_at` remains a compatibility date-only midnight placeholder for new imports, with `timestamp_precision=date`; it is not a verified tipoff time. Existing scheduled timestamps are preserved on conflict. Player stat rows record the source and retrieval timestamp. Older records are not assigned invented provenance by the additive migration.

## API and UI

Routes use internal database player IDs, not NBA external IDs. Search `/api/v1/players?search=Stephen%20Curry` to resolve identities. In the verified local database, Curry is `/players/1008`; that ID may differ in another database.

- `GET /api/v1/players/{id}` returns the profile, or 404.
- `GET /api/v1/players/{id}/games?limit=20&offset=0&season=2025-26` returns the latest bounded window in ascending chronological order, the filtered total, and profile. Limit: 1–200; offset: 0–100000. Season is optional and restricts to regular-season records. Offset counts backward from the newest appearance. Unknown players return 404; known players with no matching history return an empty array.
- `/players/{id}` displays the latest 5, 10 or 20 imported appearances, game logs, per-game means, and metric charts. Rolling means include the current and up to four earlier appearances within the displayed window. These are descriptive, not predictive; initial points use fewer observations.

Imported history can be incomplete; the UI labels totals as imported appearances. The current ingestion path supports regular-season logs and modern seeded franchise abbreviations, not exhaustive historical team aliases.

## Verification on 2026-11-17

NBA.com returned 43 Curry 2025–26 appearances dated 2025-10-21 through 2026-04-12. Two reimports preserved exactly 43 distinct games. This confirms the returned records were ingested; it is not an independent completeness audit.

`RUN_POSTGRES_TESTS=1 make test` enables PostgreSQL tests in temporary UUID schemas. Those schemas are removed after testing; application tables and volumes are preserved. Without the flag, database integration tests skip explicitly. Frontend rolling-mean tests run with `make test` too. `npm --prefix apps/web run build` verifies production compilation.

Browser checks covered Curry search/card navigation, all recent windows, metric switching, empty and unknown histories, Teams Explorer, and a 390px phone viewport. Full code review found an extended-season cutoff issue; a regression test and fix now allow 2020 bubble dates while validating regular-season game ID season prefixes.

The dependency audit reports seven moderate findings in the ESLint development dependency chain, rooted in minimatch; these were not changed by a broad dependency upgrade in this feature.
