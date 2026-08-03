.PHONY: dev stop migrate seed test test-rls test-load lint typecheck clean

# ─── Development ──────────────────────────────────────────────────────────────

dev:
	docker compose up postgres redis pgbouncer pubsub-emulator

dev-all:
	docker compose up

stop:
	docker compose down

# ─── Database ─────────────────────────────────────────────────────────────────

migrate:
	cd migrations && alembic upgrade head

migrate-down:
	cd migrations && alembic downgrade -1

seed:
	python migrations/seed.py

# ─── Testing ──────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v --tb=short

test-unit:
	pytest tests/ -v --tb=short -m unit

test-integration:
	pytest tests/integration/ -v --tb=short -m integration

test-rls:
	pytest tests/security/ -v --tb=short -m rls
	@echo "✓ RLS isolation verified for all tenant-isolated tables"

test-load:
	k6 run tests/load/phase0_baseline.js

# ─── Code Quality ─────────────────────────────────────────────────────────────

lint:
	ruff check services/ shared/ --ignore E501

typecheck:
	mypy services/ shared/ --ignore-missing-imports

# ─── Utilities ────────────────────────────────────────────────────────────────

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

shell-postgres:
	docker compose exec postgres psql -U greenpm -d greenpm

shell-redis:
	docker compose exec redis redis-cli
