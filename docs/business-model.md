# Phase 1 — Business Model

> **Status:** ✅ Validated against source data (`data/amazon-e-commerce/amazon_ecommerce_1M.csv`, 1,000,000 rows)
> **Author:** Data Engineering
> **Purpose:** Single source of truth for Phases 2–9. Every schema, seed script, KPI dashboard, and ML feature derives from this document.

---

## 1. Business Definition

**Smart-ERP operates a multi-seller e-commerce marketplace in India (currency: INR, ₹).**

- **603,815 customers** purchase from **9,000 independent sellers**
- Catalog of **89,999 products** across **5 categories / 16 subcategories / 12 brands**
- The platform processes **payments** (UPI, credit card, debit card, cash on delivery) and coordinates **fulfillment** (1–6 day shipping)
- Activity is concentrated in **5 metro cities**: Delhi, Bangalore, Mumbai, Chennai, Hyderabad
- Dataset window: **2024-03-31 → 2026-03-31** (24 months), with revenue growing ~30× over the period (₹13.9M → ₹423.7M monthly) — a high-growth marketplace

**Validated scale figures:**

| Metric | Value |
|---|---|
| Total revenue (24 mo) | ₹9,938,876,985 (≈ ₹9.94B) |
| Orders | 1,000,000 |
| Average order value (AOV) | ₹9,938.88 |
| Overall return rate | 11.60% |
| Customer concentration | Top 20% of customers = **62.9%** of revenue (real Pareto curve, not the textbook 80/20) |
| Stock-critical products (latest stock < 20) | 3,561 (4.0% of catalog) |

---

## 2. Domain Model (→ Phase 2 Schema)

Six core tables. Naming convention: `snake_case`, surrogate identity columns for `orders`/`order_items`, natural keys preserved from source (`U*`, `S*`, `P*`) as business keys.

### 2.1 `customers`
| Column | Type | Notes |
|---|---|---|
| customer_id | TEXT PK | Source `user_id` (e.g. `U356787`) |
| home_city | TEXT | **Most frequent** location across the customer's orders (235,114 customers purchased from multiple cities) |
| first_purchase_date | DATE | Derived: MIN(order_date) |
| created_at / updated_at | TIMESTAMPTZ | Audit columns (platform standard) |

Grain: 1 row per customer · **603,815 rows**

### 2.2 `sellers`
| Column | Type | Notes |
|---|---|---|
| seller_id | TEXT PK | Source `seller_id` (e.g. `S2679`) |
| current_rating | NUMERIC(2,1) | **Latest** seller_rating snapshot (0.0–5.0) |
| created_at / updated_at | TIMESTAMPTZ | Audit |

Grain: 1 row per seller · **9,000 rows**
*Rationale for first-class table:* seller rating varies over time (snapshot at each sale), enabling seller-quality analytics and the Phase 7 "top sellers" dashboard. Folding into `products` would lose this.

### 2.3 `products`
| Column | Type | Notes |
|---|---|---|
| product_id | TEXT PK | Source `product_id` (e.g. `P39256`) |
| category | TEXT | 5 values: Electronics, Home, Sports, Beauty, Clothing |
| subcategory | TEXT | 16 values (Mobile, Decor, Fitness, Makeup, …) |
| brand | TEXT | 12 values (Samsung, Nike, H&M, Boat, …) |
| current_price | NUMERIC(10,2) | **Latest** observed price (₹200.03 – ₹79,999.70) |
| product_rating | NUMERIC(2,1) | Latest rating snapshot (0.0–5.0) |
| review_count | INT | Latest snapshot |
| created_at / updated_at | TIMESTAMPTZ | Audit |

Grain: 1 row per product · **89,999 rows**
*Note:* price is a **per-event snapshot** in the source (89,981/89,999 products show price variation) — historical prices live in `order_items.unit_price`, current value in `products.current_price`.

### 2.4 `inventory`
| Column | Type | Notes |
|---|---|---|
| inventory_id | BIGINT PK (identity) | Surrogate |
| product_id | TEXT FK → products | |
| snapshot_date | DATE | Date the stock level was observed |
| stock | INT | 0–500 |
| UNIQUE (product_id, snapshot_date) | | Idempotent re-ingestion |

Grain: 1 row per product per observed date · derived from per-event stock snapshots (89,981/89,999 products vary).
*Purpose:* feeds the **stock-critical** KPI (latest stock < 20) and gives Phase 4 a real table to decrement atomically on new orders.

### 2.5 `orders`
| Column | Type | Notes |
|---|---|---|
| order_id | BIGINT PK (identity) | Surrogate (source has no order id — each source row = one order) |
| customer_id | TEXT FK → customers | |
| order_date | DATE | 2024-03-31 → 2026-03-31 |
| ship_to_city | TEXT | Per-order (customer may move) |
| payment_method | TEXT | UPI · Credit Card · Debit Card · Cash on Delivery (~25% each) |
| device | TEXT | Mobile App · Web · Tablet (~33% each) |
| delivery_status | TEXT | **Single source of truth** for fulfillment state (see §3) |
| shipping_time_days | SMALLINT | 1–6 |
| created_at / updated_at | TIMESTAMPTZ | Audit |

Grain: 1 row per order · **1,000,000 rows**

### 2.6 `order_items`
| Column | Type | Notes |
|---|---|---|
| order_item_id | BIGINT PK (identity) | Surrogate |
| order_id | BIGINT FK → orders | |
| product_id | TEXT FK → products | |
| seller_id | TEXT FK → sellers | Seller **of this item** (marketplace) |
| quantity | SMALLINT | = 1 in seed data; schema supports multi-qty (Phase 4) |
| unit_price | NUMERIC(10,2) | Price snapshot **at time of sale** |
| discount_pct | NUMERIC(4,2) | 0–70% |
| final_price | NUMERIC(10,2) | `unit_price × quantity × (1 − discount_pct/100)` — invariant enforced by CHECK |
| seller_rating_at_sale | NUMERIC(2,1) | Snapshot — preserves seller quality history |

Grain: 1 row per order line · 1:1 with `orders` in seed data (99.9% of user-date baskets contain a single item); schema intentionally supports multi-item orders created via the Phase 4 API.

### 2.7 Relationships

```
customers 1 ──── ∞ orders 1 ──── ∞ order_items ∞ ──── 1 products
                                                          │
sellers 1 ──── ∞ order_items                              │
                 products 1 ──── ∞ inventory (snapshots) ──┘
```

### 2.8 Explicitly rejected source columns
| Source column | Decision | Reason |
|---|---|---|
| `is_returned` | **Dropped** | Perfectly correlated with `delivery_status = 'Returned'` (115,990 = 115,990). Two columns saying the same thing → future inconsistencies. |
| `location` on customer | Moved to `orders.ship_to_city` | 39% of customers use multiple locations; it is a per-order attribute |
| `rating`, `review_count` (product) | Latest → `products`; history not kept | Acceptable loss; review text doesn't exist in source |
| `seller_rating` | Latest → `sellers`; per-sale → `order_items.seller_rating_at_sale` | Both current state and history preserved |

---

## 3. Order Lifecycle

Source of truth: `orders.delivery_status`.

```
                 ┌────────────┐
   created ────► │ IN TRANSIT │ (29.4%)
                 └─────┬──────┘
                       │
          ┌────────────┼─────────────┐
          ▼            ▼             ▼
     ┌─────────┐  ┌─────────┐  ┌──────────┐
     │DELIVERED│  │ DELAYED │  │ RETURNED │ (terminal)
     │ (29.5%) │  │ (29.5%) │  │ (11.6%)  │
     └─────────┘  └─────────┘  └──────────┘
```

- Percentages are share of all 1M orders.
- `DELAYED` is a terminal delivery outcome in this dataset (shipped late, not returned).
- **Phase 4 contract:** the API may only transition `IN TRANSIT → {DELIVERED, DELAYED, RETURNED}`; terminal states are immutable. All transitions are atomic transactions with audit logging.
- **Phase 7 funnel:** In Transit → Delivered/Delayed/Returned conversion.

---

## 4. Money Flow

```
unit_price (at sale)
   × quantity
   × (1 − discount_pct / 100)
   ─────────────────────────
   = final_price            ← what the customer paid
```

- **Gross revenue** = Σ `final_price` (validated: ₹9.94B / 24 mo)
- **Discounts** are seller-funded promotions: avg 29%, max 70%
- **Payments** settle per order via one method: UPI 25.0% · Credit Card 25.0% · COD 25.0% · Debit Card 24.9%
- **Returns** refund `final_price` in full (no partial refunds in source data)

> ⚠️ **Modeling assumption (flagged, revisit in Phase 7):** the source data contains **no COGS**. For margin KPIs we define `unit_cost = 0.65 × unit_price` (65% — typical marketplace blended category margin). All margin figures must be labeled *estimated*. If real cost data ever arrives, it lands in `products.unit_cost` and supersedes this constant.

**Category economics (validated):**

| Category | Revenue (24 mo) | Share | Return rate |
|---|---|---|---|
| Electronics | ₹6,579.0M | 66.2% | 11.27% |
| Home | ₹1,530.0M | 15.4% | 11.58% |
| Sports | ₹1,124.8M | 11.3% | 11.65% |
| Beauty | ₹376.0M | 3.8% | 11.76% |
| Clothing | ₹329.1M | 3.3% | 11.74% |

*Insight:* rows are evenly distributed (~200k/category) but revenue is not — Electronics wins on price, not volume. City revenue is uniform (₹1,978M–2,001M each).

---

## 5. KPI Definitions (→ Phase 7 dashboards, Phase 8 targets)

Each KPI: formula + exact source. No KPI without a query path.

| # | KPI | Formula | Source |
|---|---|---|---|
| K1 | **Revenue** | Σ final_price | order_items |
| K2 | **AOV** | Σ final_price / COUNT(DISTINCT order_id) | order_items (₹9,938.88 baseline) |
| K3 | **Return rate** | orders with status RETURNED / all orders | orders (11.60% baseline) |
| K4 | **Delayed-delivery rate** | DELAYED / (DELIVERED + DELAYED) | orders (≈50.0% of completed) |
| K5 | **Revenue by city / category / month** | K1 grouped | orders ⋈ order_items |
| K6 | **Discount effectiveness** | K1 by discount band (0–10/10–30/30–50/50–70%) | order_items |
| K7 | **Top sellers** | K1 × avg seller_rating_at_sale, per seller | order_items |
| K8 | **Stock-critical products** | latest stock < 20 | inventory (3,561 baseline) |
| K9 | **Customer concentration (Pareto)** | cumulative revenue share by customer percentile | orders ⋈ order_items (top 20% → 62.9%) |
| K10 | **Est. gross margin** | Σ (final_price − 0.65 × unit_price × qty) | order_items ⚠️ assumption §4 |
| K11 | **Customer churn risk** *(Phase 8 target)* | no order in trailing 90 days vs. own cadence | orders |
| K12 | **Return propensity** *(Phase 8 target)* | P(return) per customer/category/brand | orders ⋈ order_items (11.6% base rate) |

---

## 6. Phase 3 Ingestion Contract

**Source:** `data/amazon-e-commerce/amazon_ecommerce_1M.csv` (133 MB, 1,000,000 rows + header, RFC-4180 CSV, UTF-8). File is git-ignored; never commit it.

**Pipeline:**

```
CSV ──COPY──► raw.purchases (all TEXT, 1:1 columns)
      ──validate──► staging (typed, trimmed, deduplicated keys)
      ──normalize──► customers · sellers · products · inventory · orders · order_items
```

**Rules:**
1. `raw.purchases` mirrors the CSV exactly — no types, no transforms (replayable, auditable)
2. `orders.order_id` / `order_items.order_item_id` are generated identities; source row order is not meaningful
3. `customers.home_city` = mode of customer's locations; ties broken by most recent order
4. `products.current_price`, `sellers.current_rating` = value at **max(order_date)** per entity
5. `inventory` = distinct (product_id, order_date, stock) — last stock wins on same-day duplicates
6. Load is **idempotent**: re-running truncates raw/staging and rebuilds normalized tables (full refresh — acceptable at 1M rows)

**Acceptance checks (must all pass):**

| Check | Expected |
|---|---|
| raw row count | exactly 1,000,000 |
| orders row count | exactly 1,000,000 |
| customers / sellers / products | 603,815 / 9,000 / 89,999 |
| orphan order_items (no order) | 0 |
| orphan order_items (no product/seller) | 0 |
| NULL in any PK/FK | 0 |
| final_price invariant violations | 0 (tolerance ₹5.00 — source rounded from higher precision; max observed deviation 3.99) |
| Σ final_price | ₹9,938,876,985 ± ₹1,000 |

---

## 7. DataOps Alignment

- **Automate:** §6 is a script, not a manual import; acceptance checks run as assertions
- **Version:** this document + DDL migrations + dbt models all in git; the dataset never is
- **Observe:** ingestion logs row counts per stage; dbt tests enforce §6 checks on every run

> *This document is the contract. If data and doc disagree, the doc is wrong — fix it here first, then propagate.*
