#!/usr/bin/env bash
# Apply Phase 2 migrations in order against the Smart-ERP PostgreSQL database.
# Connection defaults mirror ~/.dbt/profiles.yml (smart_erp_dbt / dev).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIGRATIONS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/migrations"

# Defaults from local dbt profile (override via env)
export PGHOST="${PGHOST:-uptown}"
export PGPORT="${PGPORT:-5432}"
export PGUSER="${PGUSER:-magrey}"
export PGDATABASE="${PGDATABASE:-smart}"
# PGPASSWORD: set in env or rely on .pgpass / peer auth

if [[ -z "${PGPASSWORD:-}" && -f "${HOME}/.dbt/profiles.yml" ]]; then
  # Best-effort extract of pass for profile smart_erp_dbt (dev). Optional.
  _pass="$(
    python3 - <<'PY' 2>/dev/null || true
import re, pathlib
text = pathlib.Path.home().joinpath(".dbt/profiles.yml").read_text()
# naive: first pass: under smart_erp_dbt
m = re.search(r"smart_erp_dbt:.*?pass:\s*['\"]?([^'\"\n]+)", text, re.S)
if m:
    print(m.group(1).strip(" '\""))
PY
  )"
  if [[ -n "${_pass}" ]]; then
    export PGPASSWORD="${_pass}"
  fi
fi

echo "→ Connecting to ${PGUSER}@${PGHOST}:${PGPORT}/${PGDATABASE}"
if ! psql -v ON_ERROR_STOP=1 -c "SELECT version();" >/dev/null; then
  echo "ERROR: cannot connect to PostgreSQL." >&2
  echo "  Start the server, or set PGHOST/PGPORT/PGUSER/PGDATABASE/PGPASSWORD." >&2
  exit 1
fi

shopt -s nullglob
files=("${MIGRATIONS_DIR}"/*.sql)
if [[ ${#files[@]} -eq 0 ]]; then
  echo "ERROR: no migrations in ${MIGRATIONS_DIR}" >&2
  exit 1
fi

for f in "${files[@]}"; do
  echo "→ Applying $(basename "$f")"
  psql -v ON_ERROR_STOP=1 -f "$f"
done

echo "→ Verifying core tables"
psql -v ON_ERROR_STOP=1 <<'SQL'
SELECT n.nspname AS schema, c.relname AS table
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname IN ('public', 'raw', 'staging')
  AND c.relname IN (
    'customers', 'sellers', 'products', 'inventory', 'orders', 'order_items',
    'purchases'
  )
ORDER BY 1, 2;
SQL

echo "✓ Phase 2 migrations applied."
