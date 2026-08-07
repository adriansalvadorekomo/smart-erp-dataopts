# Verification Guide — check each phase's work

A quick, copy-paste reference for **confirming the work of each phase is correct**
before merging. Run commands from the **repo root** unless noted. If a check
fails, the phase is not done — fix it before opening/merging the PR.

> Prefer the CI badges in `README.md` for automation; this page is for local,
> manual verification and for understanding *what each phase proves*.

---

## Phase 1 — Business model

**What it proves:** the business spec matches the real data, and there is a single
source of truth for phases 2–9.

```bash
# 1. The doc exists and is linked from the README
test -f docs/business-model.md && echo "OK: doc present"

# 2. Key baseline numbers match the source CSV (quick spot-check, 1st row only)
head -2 data/amazon-e-commerce/amazon_ecommerce_1M.csv

# 3. README shows Phase 1 as 🟢 Done and links the doc
grep -n "business-model" README.md
```

**Green when:** `docs/business-model.md` has §1–§7, its scale figures match the CSV,
and Phase 1 is `🟢` in `README.md`.

---

## Phase 2 — Database schema

**What it proves:** migrations apply cleanly to a fresh PostgreSQL and the six
core tables exist with the invariants enforced.

```bash
# 1. Apply migrations (idempotent — safe to re-run)
./database/apply.sh

# 2. All tables exist in the right schemas
PGPASSWORD=… psql -h <host> -U <user> -d smart -c "\dt public.*" -c "\dt raw.*" -c "\dt staging.*"
#   expect: customers, sellers, products, inventory, orders, order_items (public)
#           purchases (raw, staging)

# 3. The final_price invariant CHECK is present (tolerance ±₹5.00)
PGPASSWORD=… psql -h <host> -U <user> -d smart -c \
  "SELECT conname FROM pg_constraint WHERE conrelid='order_items'::regclass AND conname='chk_order_items_final_price';"

# 4. The delivery_status CHECK is present
PGPASSWORD=… psql -h <host> -U <user> -d smart -c \
  "SELECT conname FROM pg_constraint WHERE conrelid='orders'::regclass AND conname LIKE '%delivery_status%';"
```

**Green when:** `apply.sh` exits 0 and prints `✓ Phase 2 migrations applied.`,
and both CHECKs resolve.

---

## Phase 3 — Seed / ingestion

**What it proves:** the 1M-row CSV was loaded through raw → staging → the six
tables, exactly matching the §6 acceptance contract, and is idempotent.

```bash
# 1. Ingest (full refresh, ~80 s)
python3 scripts/seed/ingest.py                      # or add --dsn "…"
#   expect: raw: 1000000  staging: 1000000  /  Normalization complete.

# 2. Acceptance checks (read-only; exit code 0 = pass)
python3 scripts/seed/acceptance.py
#   expect: ✅ ACCEPTANCE PASSED
#           orders=1,000,000 customers=603,815 sellers=9,000 products=89,999
#           revenue=₹9,938,876,984.90

# 3. Idempotency: run ingest a SECOND time, then acceptance again
python3 scripts/seed/ingest.py
python3 scripts/seed/acceptance.py                  # must still pass

# 4. Spot-check invariants directly (optional)
PGPASSWORD=… psql -h <host> -U <user> -d smart -c \
  "SELECT count(*) FROM order_items WHERE abs(final_price - round(unit_price*(1-discount_pct/100),2)) > 5.00;"
#   expect: 0
```

**Green when:** `acceptance.py` prints `✅ ACCEPTANCE PASSED` **twice in a row**
(after two consecutive ingests).

---

## Phase 4 — Backend (when implemented)

**What it proves:** the API starts, connects to the DB, and enforces the
`delivery_status` lifecycle contract.

```bash
# 1. Start the API
uv run uvicorn backend.app.main:app --reload

# 2. Health check
curl -fsS http://127.0.0.1:8000/health && echo OK

# 3. Try an illegal transition: IN TRANSIT → RETURNED must be rejected
#    (the API contract in docs/business-model.md §3)
curl -sS -X PATCH http://127.0.0.1:8000/orders/<id> -d '{"delivery_status":"RETURNED"}' -H 'Content-Type: application/json'
#   expect: 409/422, NOT a state change

# 4. Tests
uv run pytest backend/
```

**Green when:** `/health` returns 200, pytest is green, and the illegal
transition is rejected.

---

## Phase 5 — Frontend (when implemented)

```bash
cd frontend && npm ci && npm run build && npm run lint
#   expect: build succeeds with no lint errors
```

---

## Phase 6 — Data pipeline (dbt)

**What it proves:** the dbt project parses, resolves its profile, and models build
& pass data tests.

```bash
cd data/dbt
uv run dbt parse          # syntax/config valid
uv run dbt debug          # profile + connection resolve
uv run dbt run            # build models
uv run dbt test           # run data tests
cd ../..
```

**Green when:** all four commands exit 0.

---

## Phase 7 — BI (when implemented)

```bash
# Metabase reachable & connected to the analytics schema
curl -fsS http://localhost:3000/api/health
# Dashboards exported / committed under bi/
ls bi/
```

---

## Phase 8 — ML (when implemented)

```bash
uv run pytest ml/
# MLflow experiment logged for a train run
uv run mlflow experiments list | grep -q smart-erp && echo "OK: experiment tracked"
```

---

## Phase 9 — RAG (when implemented)

```bash
uv run pytest rag/
# A query returns an answer grounded in ERP data
uv run python -m rag.cli "What was revenue last month?"
```

---

## Phase 10 — Deploy (when implemented)

```bash
# Tag a release candidate (creates a GitHub Release via release.yml)
git tag v0.1.0 && git push origin v0.1.0
# Confirm the release action ran green and an artifact was published
gh run list --workflow=release.yml
```

---

## Cross-phase: CI

```bash
# Every PR and push to main must be green on the ci.yml matrix
gh pr checks
```

**Green when:** `lockfile`, `lint`, `dbt-validate`, `database-sanity`, and
`dbt-test` all pass.