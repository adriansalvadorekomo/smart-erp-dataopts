# Database — Phase 2

PostgreSQL schema for Smart-ERP. **Contract:** [`docs/business-model.md`](../docs/business-model.md) §2–§3, §6.

## Layout

| Schema | Role |
|--------|------|
| `raw` | CSV landing (`raw.purchases`, all TEXT) — Phase 3 |
| `staging` | Typed intermediate (`staging.purchases`) — Phase 3 |
| `public` | Six core OLTP tables (this phase) |

```
customers 1 ──── ∞ orders 1 ──── ∞ order_items ∞ ──── 1 products
                                                        │
sellers 1 ──── ∞ order_items                            │
               products 1 ──── ∞ inventory (snapshots) ─┘
```

## Migrations

| File | Purpose |
|------|---------|
| `migrations/001_schemas.sql` | `raw` + `staging` schemas |
| `migrations/002_core_tables.sql` | 6 core tables, FKs, CHECKs, indexes, `updated_at` triggers |
| `migrations/003_raw_staging.sql` | `raw.purchases` + `staging.purchases` for ingestion |
| `migrations/004_final_price_tolerance.sql` | Widen `final_price` CHECK to ±₹5.00 (business-model §6; source rounds from higher precision) |

Applied in filename order. `002` drops/recreates core tables (early-scaffold full refresh).

### Invariants enforced in DDL

- `order_items.final_price ≈ unit_price × quantity × (1 − discount_pct/100)` (± ₹5.00 — source rounds from higher precision, max ≈₹3.99)
- `orders.delivery_status ∈ {IN TRANSIT, DELIVERED, DELAYED, RETURNED}`
- `payment_method` / `device` / product `category` restricted to validated source sets
- `inventory (product_id, snapshot_date)` UNIQUE (idempotent re-load)
- Ratings 0.0–5.0; `shipping_time_days` 1–6; `discount_pct` 0–70

> Source CSV uses Title Case delivery statuses (`In Transit`, …). Phase 3 normalizes to the uppercase contract values above.

## Apply

Requires a running PostgreSQL and connection settings (same as dbt: `~/.dbt/profiles.yml` → profile `smart_erp_dbt` / `dev`).

```bash
# From repo root — uses env vars or defaults matching the local dbt profile
./database/apply.sh

# Or explicit:
PGHOST=uptown PGPORT=5432 PGUSER=magrey PGDATABASE=smart PGPASSWORD=… ./database/apply.sh
```

Verify:

```bash
psql -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -c "\dt public.*" -c "\dt raw.*" -c "\dt staging.*"
```

## Out of scope (later phases)

- Phase 3 seed / COPY / normalize / acceptance checks → `scripts/seed/`
- Phase 4 API transition rules (terminal `delivery_status` immutable) → app layer + optional trigger
- Alembic / SQLAlchemy models → arrive with the FastAPI backend
- dbt models use profile schema `test` (analytics), not these OLTP tables directly until sources are wired
