# Smart-ERP · Ops Dashboard (frontend)

Vite + React 19 + TypeScript + Tailwind v4 + shadcn/ui + TanStack Query over the
FastAPI backend. What it is and why: [`docs/frontend.md`](../docs/frontend.md).

## Prerequisites

- Node 22+
- The backend running (it serves the API this app calls)

## Run it (dev)

**1. Database** — PostgreSQL with migrations applied, plus at least one
customer / seller / product with stock. Full seed or instant demo rows:

```bash
./database/apply.sh
psql -v ON_ERROR_STOP=1 \
 -c "INSERT INTO public.customers (customer_id, home_city, first_purchase_date) VALUES ('U_DEMO','Delhi','2024-03-31') ON CONFLICT DO NOTHING;" \
 -c "INSERT INTO public.sellers (seller_id, current_rating) VALUES ('S_DEMO',4.5) ON CONFLICT DO NOTHING;" \
 -c "INSERT INTO public.products (product_id, category, subcategory, brand, current_price, product_rating, review_count) VALUES ('P_DEMO','Electronics','Mobile','DemoBrand',1000.00,4.0,10) ON CONFLICT DO NOTHING;" \
 -c "INSERT INTO public.inventory (product_id, snapshot_date, stock) VALUES ('P_DEMO', CURRENT_DATE, 50) ON CONFLICT (product_id, snapshot_date) DO UPDATE SET stock = 50;"
```

**2. Backend** (repo root, terminal 1):

```bash
uv sync
PGHOST=localhost PGUSER=magrey PGPASSWORD=pg PGDATABASE=smart \
  uv run uvicorn backend.app.main:app --port 8000
```

Sanity: `curl localhost:8000/health` → `{"status":"ok","db":"up"}`.

**3. Frontend** (terminal 2):

```bash
cd frontend
npm ci
npm run dev -- --port 5173
```

**4. Open it** — http://localhost:5173

## Smoke flow

1. Dashboard shows backend/DB health + orders table (empty on a fresh DB).
2. **New order** → `U_DEMO` / `Delhi`, line `P_DEMO` / `S_DEMO` / qty 1 / ₹1000 /
   10% → create → total **₹900.00** (always server-computed, never trusted
   from the client).
3. Open the order → **DELIVERED** → any further transition returns 409
   (terminal states are immutable — business-model §3).

## Configuration

| Var | Default | Meaning |
|---|---|---|
| `VITE_API_URL` | `/api` (Vite proxy → `localhost:8000`) | Backend base URL; set to the API origin for separate deploys |
| `FRONTEND_ORIGINS` (backend) | `http://localhost:5173` | Allowed CORS origins when not using the proxy |

## Checks

```bash
npx tsc -b      # typecheck (also runs in CI)
npm run build   # production build to dist/
```
