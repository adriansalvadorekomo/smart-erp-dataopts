# Frontend — Ops Dashboard (Phase 5)

> **Status:** ✅ Increment 1 live (orders over the Phase 4 API). Run guide:
> [`frontend/README.md`](../frontend/README.md).

## What it is

A thin operations console over the FastAPI backend — no business logic lives
here. Prices, lifecycle transitions, stock decrements and audit rows are all
enforced server-side (`backend/app/services/orders.py`); the UI only renders
state and forwards intent. If the UI and the contract ever disagree, the
backend wins.

## Pages

| Route | Page | Backend calls |
|---|---|---|
| `/` | Overview — Gold KPI grid (revenue, AOV, return/delayed rates, stock-critical, Pareto), 90-day revenue chart, category + discount mix, top sellers, status split | `GET /stats/overview`, `/revenue-trend`, `/revenue-by-category`, `/discount-bands`, `/top-sellers`, `/pareto` |
| `/pipeline` | Medallion flow — OLTP → Bronze → Silver → DQ gate → Gold stages, live DQ R1–R7 table, fulfillment split | `GET /stats/overview`, `/stats/dq-checks` |
| `/orders` | Orders — status-filtered table, latest first | `GET /orders?delivery_status=` |
| `/orders/:id` | Order detail — lines, totals, terminal-transition buttons (immutable notice on terminal states) | `GET /orders/{id}`, `PATCH /orders/{id}/status` |
| `/new` | Create order — multi-line form | `POST /orders` |

## Data flow

```
Browser ──same-origin /api──► Vite dev proxy ──► uvicorn :8000 ──► PostgreSQL
        (VITE_API_URL override for separate deploys; backend CORS then applies)
```

- Dev: Vite proxies `/api` → `http://localhost:8000` (see
  `frontend/vite.config.ts`), so no CORS configuration is needed locally.
- Separate deploys: set `VITE_API_URL` to the API origin and allow the
  frontend origin via the backend's `FRONTEND_ORIGINS` env var.
- Fetching/caching: TanStack Query (`src/lib/api.ts` is the only module that
  touches the network; every component goes through it).

## Stack

Vite + React 19 + TypeScript (strict, `tsc -b` gates CI) + Tailwind v4 +
shadcn/ui primitives (`src/components/ui/`) + TanStack Query + react-router +
lucide icons. Path alias `@/*` → `src/*` (wired in both `vite.config.ts` and
`tsconfig.app.json`).

## Out of scope (later)

- KPIs over Gold (revenue trends, stock-critical, funnels) → Phase 7 BI; the
  dashboard deliberately shows only OLTP state today.
- AuthN/Z → with the backend auth increment.
- Backend coverage beyond orders (customers/sellers/products/inventory views) →
  as those routers land.
