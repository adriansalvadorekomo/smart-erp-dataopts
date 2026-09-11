# Phase 3 — Seed / Ingestion

Loads the raw e-commerce dataset into PostgreSQL and validates it. Written for
developers who are new to the project — you can follow this end-to-end and the
numbers at the end are the same every time.

## What this phase does

The dataset is a single 133 MB CSV (`data/amazon-e-commerce/amazon_ecommerce_1M.csv`,
git-ignored — never commit it) with **1,000,000 purchase rows**. One raw row
describes one purchase: who bought it, from which seller, on which date, at
what price, and the delivery state.

A single CSV row does **not** slot directly into one database table, because the
six core tables (see `docs/business-model.md` §2) are at different "grains"
(levels of detail):

| Table | Grain | rows for 1M CSV |
|---|---|---|
| `customers` | one per buyer | 603,815 |
| `sellers` | one per seller | 9,000 |
| `products` | one per product | 89,999 |
| `inventory` | one stock snapshot per product per day | varies |
| `orders` | one per purchase | 1,000,000 |
| `order_items` | one per line item | 1,000,000 |

So the ingest **splits** the flat CSV stream across these tables. This is the
"normalize" step.

## The 3-stage pipeline

```
  ┌──────────┐   COPY    ┌────────────────┐  insert  ┌──────────────────┐
  │ raw CSV  │ ────────► │ raw.purchases  │ ───────► │ staging.purchases │
  └──────────┘   1:1     └────────────────┘   typed  └──────────────────┘
                                                        │  SQL (normalize)
                                                        ▼
                             ┌──────────────────────────────────────────┐
                             │ customers · sellers · products · inventory │
                             │ orders · order_items                      │
                             └──────────────────────────────────────────┘
```

1. **`raw.purchases`** — a byte-for-byte copy of the CSV. Every column is `TEXT`
   and we do **no transforms**. It exists so we can always re-read exactly what
   the source said. Replayable and auditable.
2. **`staging.purchases`** — the same rows but **typed** (numbers become numbers,
   dates become dates), trimmed of whitespace, and enum values normalized
   (`"In Transit"` → `"IN TRANSIT"` to match the `CHECK` constraints in the DDL).
3. **The six core tables** — populated from `staging` by SQL that groups rows to
   the right grain (mode city per customer, latest price per product, etc.).

## The two scripts

There are two files. Run them in this order. Both are **stdlib-only** (no
`pip install` needed) and talk to Postgres through the `psql` CLI, which must
be on your `PATH`. Connection settings come from the standard libpq env vars,
same as `database/apply.sh`:

| Script | What it does | Effect |
|---|---|---|
| `ingest.py` | Loads CSV → `raw` → `staging` → six tables | idempotent full refresh |
| `acceptance.py` | Runs the §6 contract checks and exits non-zero on any failure | read-only |

| Env var | Default | Meaning |
|---|---|---|
| `PGHOST` | `uptown` | DB host (`localhost` for the compose stack) |
| `PGPORT` | `5432` | DB port |
| `PGUSER` | `magrey` | DB role |
| `PGPASSWORD` | — | DB password (also read from `~/.pgpass`) |
| `PGDATABASE` | `smart` | Database name |

## How to run it

Start Postgres (local dev stack) and apply the migrations first:

```bash
docker compose -f infra/docker-compose.yml up -d   # local Postgres
./database/apply.sh                                 # creates raw / staging / public tables
```

Then ingest — all commands below run from the **repo root**:

```bash
# Default connection (reads PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE)
python3 scripts/seed/ingest.py

# Against the local compose stack (user magrey / db smart)
PGHOST=localhost PGUSER=magrey PGPASSWORD=pg PGDATABASE=smart python3 scripts/seed/ingest.py

# A different CSV path (default: data/amazon-e-commerce/amazon_ecommerce_1M.csv)
python3 scripts/seed/ingest.py --csv /path/to/file.csv
```

A successful run prints:

```
raw: 1000000
staging: 1000000
Normalization complete.
```

Then verify the data is correct (same env vars — no extra flags needed):

```bash
python3 scripts/seed/acceptance.py
```

A successful run prints the measured values and `ACCEPTANCE PASSED`.

## What "idempotent" means (important)

If you run `ingest.py` a **second time**, the database ends up exactly the same.
We guarantee this by, at the start of the normalize step:

1. **Deleting rows children-first** (`order_items` → `orders` → `inventory` →
   `products` → `sellers` → `customers`). If we deleted a parent first, Postgres
   would reject the statement because child rows still reference it (foreign key
   violation).
2. **Restarting the identity sequences** back to 1, so generated IDs are identical
   on every run rather than growing forever.
3. Rebuilding `orders`/`order_items` pairing from a deterministic per-row surrogate
   (`row_idx`) instead of relying on insert order — so a run is fully reproducible.

## The invariant that displaced the old tolerance

The business model says `final_price ≈ unit_price × qty × (1 − discount_pct/100)`.
The first ingest attempt failed on this constraint (`CheckViolation`) because the
**source** CSV stores `final_price` rounded from higher precision, so it never
round-trips to a `± ₹0.01` tolerance. We measured the real error across all
1,000,000 rows:

| percentile | abs error |
|---|---|
| 50 % | ₹0.12 |
| 90 % | ₹0.85 |
| 99 % | ₹2.83 |
| 99.99 % | ₹3.88 |
| max | ₹3.99 |

Because the doc says "if data and doc disagree, fix the doc", the tolerance is
**`± ₹5.00`** — it passes 100% of rows while still catching genuine
calculation bugs. The change lives in:
- `docs/business-model.md` §6 (fixed first — the contract),
- `database/migrations/004_final_price_tolerance.sql` (widens the `CHECK`;
  `002` is versioned history and stays untouched),
- `database/README.md`,
- `scripts/seed/acceptance.py` and the lakehouse DQ rule R4
  (`lakehouse/src/quality/rules.py`, `FINAL_PRICE_TOLERANCE`).

`final_price` (what the customer paid) stays authoritative; we keep the stored
value and only validate it against the formula.

## Before you commit / open a PR

- Confirm the CSV exists and is git-ignored: `data/amazon-e-commerce/amazon_ecommerce_1M.csv`
- Run both scripts and confirm `ACCEPTANCE PASSED`.
- Re-run `ingest.py` once more and re-run `acceptance.py` to confirm idempotency.

## Troubleshooting

- **`relation "raw.purchases" does not exist`** — migrations were not applied;
  run `./database/apply.sh`.
- **`psql: command not found`** — install the PostgreSQL client
  (`postgresql-client` / `libpq`) so `psql` is on `PATH`.
- **CheckViolation on `final_price`** — the database predates migration `004`;
  re-run `./database/apply.sh` to widen the `CHECK`.
- **`role "..." does not exist` / connection refused** — the `PG*` env vars don't
  match the cluster; point them at the compose stack (see above) or set `PGPASSWORD`.
- **Slow**: a full 1M-row refresh takes on the order of a minute. That is expected.
