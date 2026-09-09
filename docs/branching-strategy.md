# Branching Strategy & CI/CD

> **Status:** ✅ Active (Trunk-Based Development)
> **Owner:** DevOps / Platform
> **Applies to:** `adriansalvadorekomo/smart-erp-dataopts`
> **Purpose:** Define how code reaches production safely and repeatably across all 10 phases of the monorepo, and how CI/CD enforces it.

---

## 1. Model: Trunk-Based Development

Smart-ERP is a **monorepo** with many components (`database/`, `backend/`, `frontend/`, `data/`, `ml/`, `rag/`, `bi/`, `infra/`) that all ship together. We use **Trunk-Based Development (TBD)**:

- **`main` is the single, always-deployable trunk.** Never work directly on it.
- Developers create **short-lived feature branches** off `main` and merge them back via **Pull Request**.
- Merging to `main` requires **CI to pass** and **one review**.
- `main` is **protected**: no direct pushes, no force pushes.
- Every merge to `main` produces a **release candidate** tagged with a version.

Nothing is long-lived: branches exist for **hours to a couple of days**, not weeks. This keeps integration friction low and aligns with the incremental phase-by-phase build.

### Why not GitFlow?

GitFlow's `develop` ⇄ `main` split and multi-hop `release`/`hotfix` branches add ceremony that slows delivery. For a small-teamed, continuously-deployable DataOps platform, GitFlow mainly adds merge overhead and stale integrations. TBD gives us the same four guarantees we need with less machinery:

| Need | How TBD covers it |
|---|---|
| Working `main` at all times | CI gate + protected `main` |
| Safe experimentation | short-lived PR branches |
| Fixed releases / hotfixes | `v*` tagged RC snapshots; hotfixes are short PRs straight to `main` |
| Parallel work without conflicts | frequent, small merges |

---

## 2. Branch naming conventions

| Purpose | Branch name | Source | Merges → |
|---|---|---|---|
| Feature (default) | `feat/<phase>-<slug>` (e.g. `feat/3-ingestion`) | `main` | `main` via PR |
| Fix / patch | `fix/<slug>` | `main` | `main` via PR |
| Chore / docs / CI | `chore/<slug>` | `main` | `main` via PR |
| Refactor | `refactor/<slug>` | `main` | `main` via PR |
| Hotfix (prod regression) | `hotfix/<slug>` | `main` (or `v<version>`) | `main` via PR |
| Release snapshot | `v<major>.<minor>.<patch>` | `main` (tag) | n/a (tag) |

**Rules:**
- Use `kebab-case`, lowercase, a slash-separated type prefix.
- Branch life: **as short as the work**; target < 2 days.
- **Never** commit directly to `main`, `dev`, or any environment branch.

---

## 3. The release flow

```
feature branch ──PR──► main ──tag──► v<semver>
     │                     │                │
  CI on PR & push ·      merge =      CI on tag builds, runs
  lakehouse tests         new RC      migrations, publishes
     │                     │                │
 PR requires:         main passes       tag is deployable
  green CI + review    all checks        artifact
```

1. **Develop on a short-lived branch** with automated formatting/tests locally.
2. **Open a PR.** CI runs the full validation matrix on the branch (see §5).
3. **PR is approved** and CI is green → **squash-merge** to `main`.
4. **CI re-runs on `main`** as a final gate.
5. **Release:** a maintainer tags `main` with `v<semver>` → CI builds the deployable artifact. Future phases (deploy) hook here.

> **Phase-10 note:** when deployable infra lands, a `releases/` environment will pull by tag. Until then, tags are bookkeeping for deployable `main` snapshots.

---

## 4. CI/CD architecture

Two **GitHub Actions** workflows enforce and automate the strategy:

| Workflow | Trigger | Purpose |
|---|---|---|
| `.github/workflows/ci.yml` | PRs to `main` + push to `main` + cron | Validate every commit: uv lock, lint, lakehouse tests, Gold SQL sanity, terraform validate, DB migration smoke |
| `.github/workflows/release.yml` | tag `v*` | Build & publish the deployable artifact from a `main` snapshot |

**Branch protection** (enable in GitHub repo settings / `main`):
- Require PRs before merging.
- Require **1** approving review.
- Require CI (`ci.yml`) to pass.
- Allow **no force pushes**; **no direct pushes** to `main`.
- Require **linear history** (squash merges only).

---

## 5. The CI validation matrix (`ci.yml`)

Runs on every PR and every push to `main`. Failure blocks the merge.

| Job | What it does | Fails PR on |
|---|---|---|
| `lockfile` | `uv lock --check` (lockfile matches `pyproject.toml`) | dependency drift |
| `lint` | Python lint/format gate (stage clean) | offending code |
| `lakehouse-test` | stdlib unittest over lakehouse pure logic + `local_run.py` + Workflows JSON validation (no cluster, no DB) | failing contracts |
| `sql-parse` | Gold SQL sanity (silver-sourced, margin labelled estimated) | leaking OLTP/raw reads |
| `terraform-validate` | `terraform init -backend=false && terraform validate` in `infra/terraform` | invalid workspace assets |
| `database-sanity` | apply `database/apply.sh` against Postgres, assert core tables exist | broken migrations |
| `seed-acceptance-note` | doc-consistency guard until `scripts/seed/` merges (full 1M-row acceptance runs on its own branch) | contract drift |

> Machine-local credentials (Databricks token, PG passwords) are **never** in the repo and CI never deploys to the workspace — Free Edition deploy stays a manual `workflow_dispatch`. See `docs/databricks-free-edition.md`.

### Environment targets

- **dev / PR:** every PR runs the full matrix (lakehouse tests need no DB; only `database-sanity` uses a throwaway Postgres container). Nothing is deployed.
- **staging:** next `main` merge is promoted; the Workflows job runs fully with all data.
- **prod:** a released `v*` tag is `what to be deployed` after staging sign-off.

> Environment *deploy* wiring arrives in Phase 10 (infra). Get the validation gate right now; deploys drop in at the tag hook.

---

## 6. Hotfix flow

A prod regression (bad migration, P0 bug) follows the same trunk shape, just faster:

1. Branch `hotfix/<slug>` off the **released tag** (not latest `main`).
2. Minimal fix + a regression test.
3. PR → CI green → merge to `main`.
4. Tag `v<patch>` and re-release.

This avoids dragging unrelated in-flight work from `main` into a hotfix.

---

## 7. Phase–strategy mapping

| Phase | Where branches touch | CI relevance |
|---|---|---|
| 1 Business model | `docs/` | — (doc) |
| 2 Database | `database/migrations/` | `database-sanity` |
| 3 Seed / ingestion | `scripts/seed/`, `data/` | `seed-acceptance` (own branch until merged) |
| 4 Backend | `backend/` | lint, tests |
| 5 Frontend | `frontend/` | build, lint |
| 6 Data platform | `lakehouse/` (bronze/silver/gold/quality/workflows/sql) | `lakehouse-test`, `sql-parse` |
| 7 BI | `bi/` (Databricks SQL core) | — |
| 8 ML | `ml/` | model CI, unittest |
| 9 AI | `rag/` (governed Gold) | unittest |
| 10 Deploy | `infra/`, `release.yml` | `terraform-validate`, tag → prod |

---

## 8. Daily workflow (cheat sheet)

```bash
git checkout main && git pull                    # start clean
git switch -c feat/3-ingestion                   # short-lived branch
# ... work ...
uv lock                                          # keep deps in sync
git add -A && git commit -m "feat(3): ingest CSV → staging"
git push -u origin feat/3-ingestion              # open PR
# CI runs the matrix; reviewer approves → squash-merge to main
git checkout main && git pull                    # TBD: always rebase off latest main
```

## 9. Out of scope / future

- Automatic deploy to staging/prod (Phase 10 `infra/`).
- `release.yml` publishing artifacts (wired once an artifact exists).
- Secret handling for DB credentials (use GitHub Environments / OIDC), to be scoped at Phase 10.
- Conventional-commit auto-versioning (Semantic Versioning) — adopt when releases actually deploy.

---

> **This document is the contract.** If CI behavior and this doc disagree, fix the doc first, then the pipeline.