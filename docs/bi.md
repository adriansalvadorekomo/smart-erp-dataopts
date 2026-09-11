# BI — Dashboards over Gold (Phase 7)

> **Status:** ✅ Live (Lakeview dashboards deployed; tile queries validated).
> Definitions: [`bi/revenue_overview/`](../bi/revenue_overview/) ·
> [`bi/fulfillment_funnel/`](../bi/fulfillment_funnel/) ·
> [`bi/dashboards/`](../bi/dashboards/) (`Smart-ERP Revenue`, `Smart-ERP Fulfillment`).

## Principle

Dashboards read **Gold only** (never Bronze/Silver/OLTP), through versioned
definitions in `bi/`. A tile is a `(dataset, widget)` pair; the SQL lives in
git, the layout lives in versioned `.lvdash.json` next to it. Catalog is
concrete (`workspace` — Free Edition single-catalog).

## What's live (workspace)

| Dashboard | Tiles | Source |
|---|---|---|
| Smart-ERP Revenue | Headline KPIs · monthly trend · by city · by category | `bi/dashboards/smart-erp-revenue.lvdash.json` |
| Smart-ERP Fulfillment | Rates (return/delayed/in-transit) · status funnel | `bi/dashboards/smart-erp-fulfillment.lvdash.json` |

Each backing query was executed green on the warehouse against full Gold
(revenue ties to baseline; 11.60% return, ≈50.0% delayed).

## Deploy / refresh

Dashboards import from the versioned JSON (workspace import of
`bi/dashboards/*.lvdash.json` registers a real dashboard object — verified
`object_type: DASHBOARD` via API). Re-import after editing a definition.
Tiles re-query on open; Gold itself rebuilds with the `smart-erp-medallion`
job — no dashboard-side scheduling needed. To switch a table tile to a chart,
open the widget in the UI and change its visualization (one click, no scope
or redeploy needed).

## Blocker notes (why not fully scripted)

Programmatic *visualization*/*dashboard* APIs need broader token scopes than
this repo's PAT carries (`all-apis`, `dashboards`), so chart-type upgrades and
layout edits stay manual UI steps. Queries, datasets and dashboard shells —
the versioned parts — are all deployed. Do not widen token scopes in CI:
workspace assembly stays manual, like the Workflows deploy.

## Principle

Dashboards read **Gold only** (never Bronze/Silver/OLTP), through versioned
queries in `bi/`. A tile is a `(query, visualization)` pair; the SQL lives in
git, the layout lives in the workspace. Catalog is bound per dashboard via the
`catalog` query parameter (`workspace` on Free Edition).

## Backing queries (in the workspace)

All six exist under SQL → Queries with the `[smart-erp]` prefix, pointed at
the Serverless Starter Warehouse (created for ad-hoc use alongside the
dashboards):

| # | Query | Dashboard | Suggested tile |
|---|---|---|---|
| 1 | `[smart-erp] Revenue KPIs` | Revenue | 3 Counters: revenue, orders, aov |
| 2 | `[smart-erp] Monthly trend` | Revenue | Line chart: x = order_month, y = revenue (+ orders) |
| 3 | `[smart-erp] Revenue by city` | Revenue | Bar: x = ship_to_city, y = revenue |
| 4 | `[smart-erp] Revenue by category` | Revenue | Bar or donut: x = category, y = revenue |
| 5 | `[smart-erp] Funnel counts` | Fulfillment | Bar: y = delivery_status, x = orders (+ revenue) |
| 6 | `[smart-erp] Return and delayed rates` | Fulfillment | 3 Counters: return_rate, delayed_rate, in_transit |

> Manual-assembly section removed: dashboards now deploy from
> `bi/dashboards/*.lvdash.json` (see Deploy above).

## Blocker (why assembly isn't scripted yet)

Programmatic visualization/dashboard creation needs broader token scopes than
this repo's PAT carries (`all-apis` for visualizations; the dashboard-create
RPC rejects API calls on this workspace). With an `all-apis` token — or 5
manual minutes above — the dashboards exist; the queries (the versioned part)
are already live. Do not widen token scopes in CI: dashboard assembly stays a
manual workspace step, like the Workflows deploy.
