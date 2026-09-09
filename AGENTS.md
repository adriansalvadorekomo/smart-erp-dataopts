# AGENTS.md

## Repo state

Early-stage scaffold of a 10-phase DataOps ERP (e-commerce marketplace, India, INR ₹). **Implemented:** Phase 1 business model (`docs/business-model.md`), Phase 2 PostgreSQL DDL (`database/migrations/`), and the Databricks Lakehouse skeleton (`lakehouse/` — Bronze/Silver/Gold contracts, DQ rules R1–R9, Workflows job, Gold SQL). `backend/`, `frontend/`, `ml/`, `rag/`, `bi/` are empty placeholders (.gitkeep only) — do not assume they run or contain code. `scripts/seed/` ingestion lives on a separate branch until merged.

## Tooling

- Python 3.12, managed with **uv** (`uv sync`, `uv run ...`). Project deps are intentionally stdlib-only; cluster deps (pyspark, delta, mlflow) arrive with the backfill/training increment.
- Lakehouse logic is verified without a cluster: `python -m unittest discover -s lakehouse/tests` and `python lakehouse/local_run.py`.
- Databricks Free Edition workspace (URL in `docs/databricks-free-edition.md`); Terraform skeleton in `infra/terraform/` (`terraform init -backend=false && terraform validate`).
- Retired (see `docs/decisions.md`): dbt, Airflow, Airbyte, Metabase-as-core, pgvector-as-sidecar. Do not reintroduce them without an ADR.

## Workflow / branching

- **Trunk-Based Development**: short-lived branches (e.g. `feat/<phase>-<slug>`) merged to `main` only via PR; `main` is protected and always deployable. Full contract: **`docs/branching-strategy.md`**.
- **CI/CD:** `.github/workflows/ci.yml` (PR + push to `main`) and `.github/workflows/release.yml` (tag `v*`). CI runs on GitHub-hosted runners — lakehouse tests need no cluster or DB (stdlib unittest); only `database-sanity` uses a Postgres service container.

## Domain contract

- **`docs/business-model.md` is the single source of truth** for Phases 2–9 (schemas, KPIs, money flow, row counts). If data and doc disagree, the doc is wrong — fix it there first, then propagate.
- Currency is **INR (₹)** throughout; 6 core tables: `customers`, `sellers`, `products`, `inventory`, `orders`, `order_item.opencode/skills/s`.
- Key invariants to preserve:
  - `final_price = unit_price × quantity × (1 − discount_pct/100)` (enforced by CHECK). **Tolerance is ±₹5.00, not ₹0.01** — the source CSV round-trips up to ~₹3.99 from higher precision; see `docs/business-model.md` §6 and `lakehouse/src/quality/rules.py` R4.
  - `orders.delivery_status` lifecycle: `IN TRANSIT → {DELIVERED, DELAYED, RETURNED}`; terminal states immutable.
  - No COGS in source; margin uses estimated `unit_cost = 0.65 × unit_price` — always label margin figures "estimated".
- Reference row counts: 1,000,000 orders; 603,815 customers; 9,000 sellers; 89,999 products.

## Raw data

- `data/amazon-e-commerce/amazon_ecommerce_1M.csv` (133 MB) is **git-ignored — never commit it**.
- Phase 3 ingestion depends on it; must be idempotent (full refresh at 1M rows) and pass the acceptance checks in §6 of the business model doc.
