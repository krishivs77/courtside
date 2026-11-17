.PHONY: dev stop db test

db:
	@colima status >/dev/null 2>&1 || colima start
	@docker compose up -d --wait db

dev: db
	@set -a; \
	. ./.env; \
	set +a; \
	trap 'kill $$(jobs -pr) 2>/dev/null || true' EXIT INT TERM; \
	(cd apps/api && .venv/bin/fastapi dev app/main.py) & \
	(cd apps/web && npm run dev) & \
	wait

test:
	@set -a; \
	. ./.env; \
	set +a; \
	(cd apps/api && .venv/bin/python -m pytest -q) && \
	(cd apps/web && npm run lint && npx tsc --noEmit)

stop:
	@docker compose down
	@colima stop
