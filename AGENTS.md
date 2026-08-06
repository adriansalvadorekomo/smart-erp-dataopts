# AGENTS.md

## Repo state

Early-stage scaffold of a 10-phase DataOps ERP (e-commerce marketplace, India, INR ₹). **Implemented:** Phase 1 business model (`docs/business-model.md`), Phase 2 PostgreSQL DDL (`database/migrations/`), and dbt project scaffold (`data/dbt/`). `backend/`, `frontend/`, `ml/`, `rag/`, `bi/`, `infra/`, `scripts/` are empty placeholders (.gitkeep only) — do not assume they run or contain code.

## Tooling

- Python 3.12, managed with **uv** (`uv sync`, `uv run ...`). Only dependencies: `dbt-core`, `dbt-postgres`.
- The dbt project lives at **`data/dbt/`**, not the repo root — run `dbt` commands from that directory (`cd data/dbt && dbt run`).
- dbt profile `smart_erp_dbt` lives in **`~/.dbt/profiles.yml`** (outside the repo, machine-local, points at a local PostgreSQL). Do not add a repo-local `profiles.yml`.
- No CI, tests, or linter are configured yet.

## Domain contract

- **`docs/business-model.md` is the single source of truth** for Phases 2–9 (schemas, KPIs, money flow, row counts). If data and doc disagree, the doc is wrong — fix it there first, then propagate.
- Currency is **INR (₹)** throughout; 6 core tables: `customers`, `sellers`, `products`, `inventory`, `orders`, `order_item.opencode/skills/s`.
- Key invariants to preserve:
  - `final_price = unit_price × quantity × (1 − discount_pct/100)` (enforced by CHECK).
  - `orders.delivery_status` lifecycle: `IN TRANSIT → {DELIVERED, DELAYED, RETURNED}`; terminal states immutable.
  - No COGS in source; margin uses estimated `unit_cost = 0.65 × unit_price` — always label margin figures "estimated".
- Reference row counts: 1,000,000 orders; 603,815 customers; 9,000 sellers; 89,999 products.

## Raw data

- `data/amazon-e-commerce/amazon_ecommerce_1M.csv` (133 MB) is **git-ignored — never commit it**.
- Phase 3 ingestion depends on it; must be idempotent (full refresh at 1M rows) and pass the acceptance checks in §6 of the business model doc.
