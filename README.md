<h1 align="center">Smart-ERP · DataOps</h1>

<p align="center">
  <b>DataOps-driven ERP for e-commerce</b> — 10-phase build from business model to AI-powered chat assistant.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/dbt-1.11-FF694B?style=flat&logo=dbt&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB" />
  <img src="https://img.shields.io/badge/Airflow-017CEE?style=flat&logo=apacheairflow&logoColor=white" />
  <img src="https://img.shields.io/badge/MLflow-0194E2?style=flat&logo=mlflow&logoColor=white" />
  <img src="https://github.com/adriansalvadorekomo/smart-erp-dataopts/actions/workflows/ci.yml/badge.svg" />
</p>

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SMART ERP SYSTEM                        │
│                                                           │
│  [1] Business Model ──→ [2] DB ──→ [3] Seed Data          │
│                                    │                       │
│                                    ▼                       │
│                         [4] Backend (FastAPI)             │
│                                    │                       │
│                                    ▼                       │
│                         [5] Web App (React)               │
│                                    │                       │
│              ┌─────────────────────┘                       │
│              ▼                                             │
│       [6] Pipeline: PostgreSQL → Airbyte → dbt → Airflow   │
│              │                                             │
│              ├──→ [7] BI (Metabase / Power BI)            │
│              ├──→ [8] ML (sales pred., churn classif.)    │
│              └──→ [9] AI / RAG (chat over data)           │
│                                                           │
│       [10] Deploy + Demo ◀────────────────────────────── │
└─────────────────────────────────────────────────────────┘
```

*Every phase depends on the one before it. DataOps guarantees each layer feeds the next without friction.*

---

## Phases

| Phase | Component | Status |
|-------|-----------|--------|
| 1 | **Business Model** — multi-seller marketplace (India, INR), KPIs, money flow — [docs/business-model.md](docs/business-model.md) | 🟢 Done |
| 2 | **Database** — PostgreSQL with 6 core tables + `raw`/`staging` — [database/](database/) | 🟢 Done |
| 3 | **Seed Data** — Ingest 1M-row Amazon-style dataset (CSV → `raw` schema → normalized tables, with acceptance checks) | 🟡 Next |
| 4 | **Backend** — FastAPI + SQLAlchemy with atomic transactions, audit logging, Pydantic validation | 🟡 Planned |
| 5 | **Web App** — React (Vite) + TanStack Query + shadcn/ui | 🟡 Planned |
| 6 | **Data Pipeline** — PostgreSQL → Airbyte → dbt (staging/intermediate/marts) → Airflow orchestration | 🟢 Scaffolded |
| 7 | **BI** — Metabase / Power BI dashboards (revenue, top clients, stock critical, order funnel) | 🟡 Planned |
| 8 | **ML** — Sales prediction (XGBoost) + customer churn (RandomForest), tracked with MLflow | 🟡 Planned |
| 9 | **AI / RAG** — Natural language chat over ERP data using embeddings + LLM | 🟡 Planned |
| 10 | **Deploy + Demo** — Railway (backend), Vercel (frontend), Supabase (DB), Astronomer (Airflow) | 🟡 Planned |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Database** | PostgreSQL |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy, Pydantic |
| **Frontend** | React (Vite), TanStack Query, shadcn/ui |
| **ETL / ELT** | Airbyte, dbt-core, dbt-postgres |
| **Orchestration** | Apache Airflow |
| **BI** | Metabase, Power BI |
| **ML / MLOps** | scikit-learn, XGBoost, MLflow |
| **AI / RAG** | LangChain / sentence-transformers, pgvector, GPT-4o / Claude |
| **Infrastructure** | Docker, Docker Compose |
| **Package Manager** | uv |

---

## Project Structure

```
smart-erp/
├── docs/                # [1] Business model — KPIs, money flow, domain definitions
├── database/            # [2] PostgreSQL schema + versioned migrations (apply.sh)
├── scripts/seed/        # [3] Dataset ingestion (CSV → raw → normalized, validated)
├── backend/app/         # [4] FastAPI — api/ core/ models/ schemas/ services/
├── frontend/            # [5] React (Vite) + TanStack Query + shadcn/ui
├── data/
│   ├── dbt/             # [6] dbt project — models/{staging,intermediate,marts}
│   ├── airbyte/         # [6] Airbyte connection configs
│   └── airflow/dags/    # [6] Airflow orchestration DAGs
├── bi/                  # [7] Metabase / Power BI dashboards
├── ml/                  # [8] Sales prediction + churn (MLflow-tracked)
├── rag/                 # [9] Embeddings + LLM chat over ERP data
└── infra/               # [10] Dockerfiles + deploy configs
```

## Docs

- **Business model & data contract** — [`docs/business-model.md`](docs/business-model.md) (single source of truth for Phases 2–9)
- **Branching & CI/CD** — [`docs/branching-strategy.md`](docs/branching-strategy.md) (Trunk-Based Development, GitHub Actions pipeline)
- **Database** — [`database/README.md`](database/README.md) (migrations, invariants, apply)

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/adriansalvadorekomo/smart-erp-dataopts.git
cd smart-erp-dataopts

# Set up environment
uv venv
source .venv/bin/activate
uv sync

# Run dbt (development)
cd data/dbt
dbt debug
dbt run
```

> **Note:** This project is in early development. Each phase is being built incrementally following the methodology outlined in the [project documentation](https://github.com/adriansalvadorekomo/smart-erp-dataopts).

---

## DataOps Principles

Every phase follows these three rules:

- **Automate** the repetitive (pipelines, tests, deploys)
- **Version** everything (code, schemas, models, data)
- **Observe** always (logs, metrics, alerts from day one)

> *"Building this system is like opening a restaurant. First you decide the menu. Then you buy ingredients. Then you cook. Nobody opens a restaurant by hiring the AI sommelier first."*

---

## Why This Matters

This project demonstrates a complete **Data Engineering & BI workflow**:

- **Star-schema dimensional modeling** in PostgreSQL
- **Version-controlled data transformations** with dbt
- **Pipeline orchestration** with Apache Airflow
- **ML model lifecycle** tracking with MLflow
- **Self-service analytics** via BI dashboards
- **Natural language interfaces** through RAG

---

## Related

| Resource | Link |
|----------|------|
| 📄 CV (Multi-Language) | [Download PDFs](https://github.com/adriansalvadorekomo/adriansalvadorekomo/tree/main/cv) |
| 🏗 Event Analytics Platform | [EventZilla BI](https://github.com/adriansalvadorekomo/Esprit-PABI-4ERPBI6-2526-EventZella) |
| 📊 HR Workforce Analytics | [Profile Repo](https://github.com/adriansalvadorekomo/adriansalvadorekomo) |

---

<p align="center">
  <sub>Built with DataOps · Questions drive the warehouse, not source schemas</sub>
</p>
