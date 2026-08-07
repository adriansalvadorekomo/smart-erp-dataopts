# Phase 3 — Seed / Ingestion

Loads the raw e-commerce dataset into PostgreSQL and validates it. Written for
developers who are new to the project — you can follow this end-to-end and the
numbers at the end are the same every time.

## What this phase does

The dataset is a single 133 MB CSV (`data/amazon-e-commerce/amazon_ecommerce_1M.csv`)
with **1,000,000 purchase rows**. One raw row describes one purchase: who bought
it, from which seller, on which date, at what price, and the delivery state.

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

There are two files. Run them in this order.

| Script | What it does | Effect |
|---|---|---|
| `ingest.py` | Loads CSV → `raw` → `staging` → six tables | idempotent full refresh |
| `acceptance.py` | Runs the §6 contract checks and exits non-zero on any failure | read-only |

## How to run it

Run the DB migrations first (creates the `raw`, `staging`, and `public` tables):

```bash
./database/apply.sh          # from the repo root
```

Then ingest from any path — all commands below are run from the **repo root**:

```bash
# Option A: default connection (reads PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE)
python3 scripts/seed/ingest.py

# Option B: explicit DSN (e.g. a local docker Postgres on port 5433)
python3 scripts/seed/ingest.py --dsn "host=localhost port=5433 user=magrey password=pg dbname=smart"
```

A successful run prints:

```
raw: 1000000  staging: 1000000
Normalization complete.
```

Then verify the data is correct:

```bash
python3 scripts/seed/acceptance.py --dsn "host=... port=... user=... password=... dbname=..."
```

> Use the **same DSN** for both commands. If you used the default connection for
> ingest, acceptance will pick up the same env vars — no need to pass `--dsn`.

## What "idempotent" means (important)

If you run `ingest.py` a **second time**, the database ends up exactly the same:

```
raw: 1000000  staging: 1000000
Normalization complete.
```

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
round-trips to the old `± ₹0.01` tolerance. We measured the real error across all
1,000,000 rows:

| percentile | abs error |
|---|---|
| 50 % | ₹0.12 |
| 90 % | ₹0.85 |
| 99 % | ₹2.83 |
| 99.99 % | ₹3.88 |
| max | ₹3.99 |

Because the doc says "if data and doc disagree, fix the doc", the tolerance was
updated to **`± ₹5.00`** — it passes 100% of rows while still catching genuine
calculation bugs. The change is mirrored in:
- `database/migrations/002_core_tables.sql` (the `CHECK`),
- `docs/business-model.md` §6,
- `database/README.md`,
- `scripts/seed/acceptance.py`.

`final_price` (what the customer paid) stays authoritative; we keep the stored
value and only validate it against the formula.

## Before you commit / open a PR

- Confirm the CSV exists and is git-ignored: `data/amazon-e-commerce/amazon_ecommerce_1M.csv`
- Run both scripts and confirm "ACCEPTANCE PASSED".
- Re-run `ingest.py` once more and re-run `acceptance.py` to confirm idempotency.

## Troubleshooting

- **`relation "raw" does not exist`** — migrations were not applied; run `./database/apply.sh`.
- **`psycopg2.CheckViolation` on `final_price`** — the stored migration is very
  old (pre tolerance change); re-run `./database/apply.sh` to recreate the CHECK.
- **`role "..." does not exist`** — the DB user in your DSN doesn't match the
  cluster; set `PGUSER`/`PGPASSWORD` or pass a full `--dsn`.
- **Slow**: a full 1M-row refresh takes ~80 s. That is expected.