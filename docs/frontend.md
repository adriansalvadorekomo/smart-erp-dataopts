# Frontend — Data Product (Phase 5)

> **Status:** ✅ Question-driven console (overview, sales, sellers, operations,
> pipeline, orders). Run guide: [`frontend/README.md`](../frontend/README.md).

## What it is

The consumption and decision layer of the data platform — it turns committed
data into answers, not record browsers. Every section is organized around a
business question (who drives revenue, who slips, what needs action, is data
flowing), and every number comes from a business-oriented API endpoint
(`backend/app/services/stats.py`), never from client-side crunching.

Layer discipline (brief: metrics live in the analytical layer):

```
OLTP / Gold models → FastAPI stats endpoints → TanStack Query → pages
```

The browser never holds Databricks credentials: lakehouse state on the
Pipeline page is either computed live over OLTP (DQ mirror) or a labeled,
dated validation snapshot — never faked live data.

## Pages (each answers a question)

| Route | Question | Backend calls |
|---|---|---|
| `/` Overview | How is the business doing right now? | `/stats/overview`, `/revenue-trend`, `/pareto`, `/stats/city-performance`, `/stats/seller-performance` (attention strip) |
| `/sales` | What drives revenue, and what is changing? | `/stats/category-trend`, `/stats/city-performance`, `/stats/discount-bands`, `/stats/seller-performance` |
| `/sellers` | Who performs — and who needs attention? | `/stats/seller-performance` (flags: low rating, delays, returns) |
| `/operations` | What needs action? | `/stats/city-performance`, `/stats/stock-critical`, `/stats/dq-checks` |
| `/pipeline` | Is data flowing? | `/stats/overview`, `/stats/dq-checks` (+ dated backfill snapshot) |
| `/orders`, `/orders/:id` | Operate: inspect / transition a single order | `GET /orders`, `GET /orders/{id}`, `PATCH /orders/{id}/status` |
| `/new` | Operate: book an order (server prices it) | `POST /orders` |

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

- Databricks-native BI dashboards (Phase 7) — this console mirrors Gold KPIs
  from OLTP; the workspace dashboards query Gold directly.
- ML targets (K11 churn, K12 return propensity, Phase 8) — endpoints and pages
  plug into the existing stats → Query → page pattern when models land.
- AuthN/Z — with the backend auth increment.
