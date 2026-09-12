"""Retrain revenue forecasts and replace public.revenue_forecasts.

Scheduled (cron/systemd/Phase-10 wiring); run manually any time:

    uv run python -m backend.app.jobs.refresh_forecast [--horizon 30]

Connection via the standard PG* env vars. Exit non-zero on failure.
"""
from __future__ import annotations

import argparse
import sys

from backend.app.core.db import get_session_factory
from backend.app.services.forecast import HORIZON, refresh


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--horizon", type=int, default=HORIZON)
    args = ap.parse_args()
    session = get_session_factory()()
    try:
        result = refresh(session, horizon=args.horizon)
    finally:
        session.close()
    print(f"forecast refresh: asof={result['asof']} horizon={result['horizon']} rows={result['rows']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
