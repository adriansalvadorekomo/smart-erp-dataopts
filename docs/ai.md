# AI — Grounded Insights (Phase 9)

> **Status:** ✅ Documents attach + retrieve live; doc-grounded FM answers live;
> Genie client live, Space setup is the one remaining manual step (below).

## Architecture (veracity per question)

```
Business documents ──► parse/chunk/embed ──► Postgres (+ UC Volume bytes)
                                                        │ cosine top-k
Gold marts ──► Genie Space ──► per-question SQL ────────┼──► cited answers
OLTP/stats ──► deterministic intents ───────────────────┘
```

Three answerers, one contract (`{answer, intent, sources}`):

| Ask tab | Engine | Grounding | Needs |
|---|---|---|---|
| Data | intent → stats services (no LLM) | OLTP + forecasts, computed live | nothing |
| Documents | retrieve top-k chunks → FM synthesis, strict context-only prompt | attached docs (cited per chunk) | `DATABRICKS_HOST/TOKEN` (FM API) |
| Genie | Genie writes Gold SQL per question, backend relays SQL + rows | governed Gold (cited SQL) | `GENIE_SPACE_ID` |

Rules both LLM paths obey: empty grounding → explicit unknown (never
generation); every factual claim cites its source; no auto-actions.

## Genie Space setup (one-time, ~5 min UI)

API space creation needs an undocumented `serialized_space` schema — not worth
reverse-engineering against a UI that does it in clicks:

1. Databricks → **Genie** → New space → name `Smart-ERP Gold`.
2. Add data: `workspace.gold.fact_sales`, `sales_daily`, `customer_360`,
   `inventory_kpis` (+ `dim_*` as they land).
3. Add 2–3 sample questions (e.g. "total revenue by month", "return rate by
   category") so business users see the pattern.
4. Copy the space ID from the URL (`.../genie/<space-id>`) → backend env
   **`GENIE_SPACE_ID`**.
5. Verify: `POST /ai/ask-genie {"question": "total revenue?"}` returns Genie's
   own SQL plus result rows (verified live: `SUM(revenue)` over
   `workspace.gold.sales_daily` → ₹9,938,876,984.90 = baseline).

Relay flow (`services/genie.py`, conversation API): `start-conversation` →
poll message to `COMPLETED` → attachments (SQL + inline rows, else fetch via
`query-result`) → answer = Genie text (question echoes filtered) or a row
summary. Without the ID the endpoint answers 502 with these instructions.

## Documents pipeline

- Upload (`POST /documents`, pdf/md/txt/csv ≤ 20 MB) → BackgroundTasks:
  volume put → parse → 400-word chunks (80 overlap) → MiniLM embeddings →
  `ready` (or `failed` with the reason on the row — always observable).
- Bytes: `workspace.bronze.documents` UC Volume in prod, local dir for
  dev/test (`DOC_STORE_DIR`). Registry enforces mime/size/UNIQUE path.
- Retrieval (`POST /documents/search`): exact brute-force cosine over
  L2-normalized vectors — right scale to hundreds of docs; Vector Search index
  only if that changes (no pgvector sidecar per decisions).
- Deps: `transformers` + CPU torch (present), `pypdf`. Model downloads once
  (`~/.cache/huggingface`); CI runs the real-embedding smoke test.

## Env

| Var | Used by | Notes |
|---|---|---|
| `DATABRICKS_HOST` / `DATABRICKS_TOKEN` | FM synthesis, volume store, Genie relay | backend secret, never committed; FM needs `model-serving`, Genie `genie` scope |
| `FM_ENDPOINT` | RAG synthesis | default `databricks-gpt-oss-120b` (verified READY) |
| `GENIE_SPACE_ID` | Genie relay | unset → 502 with setup instructions |
| `DOC_STORE_DIR` | local volume fallback | dev/test only |

## Out of scope (later)

- LLM intent routing for the Data tab (contract already stable for it).
- Scheduled re-embedding / doc versioning (re-upload supersedes for now).
- Conversation memory (each ask is stateless; threads arrive with UX demand).
