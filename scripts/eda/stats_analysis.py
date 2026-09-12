#!/usr/bin/env python3
"""Phase 8 — Statistical analysis over the source CSV (numpy/scipy).

Three layers, targets first:
  §1 UNIVARIATE — distributions (numeric moments/quartiles, categorical shape).
  §2 BIVARIATE + INFERENTIAL vs targets — RETURNED (binary) and
     delivery_status (4-class): chi-square + Cramer's V, mean gaps + Cohen's d,
     Mann-Whitney U, Wilson 95% CIs. Focused z-tests for the two EDA cliffs
     (ship day 6, rating < 3.0).
  §3 PCA — standardized numeric space: eigenvalues, explained variance,
     PC1/PC2 loadings (what actually varies together), class separation check.

Usage:
    uv run python scripts/eda/stats_analysis.py [--csv PATH] [--n N]
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CSV = REPO / "data/amazon-e-commerce/amazon_ecommerce_1M.csv"
NUM = ["price", "discount", "final_price", "rating", "review_count", "stock",
       "seller_rating", "shipping_time_days"]
CAT = ["category", "subcategory", "brand", "location", "device",
       "payment_method", "shipping_time_days"]
ALPHA = 0.05


def cramers_v(chi2: float, n: int, r: int, k: int) -> float:
    return math.sqrt(chi2 / (n * min(r - 1, k - 1))) if min(r, k) > 1 else 0.0


def wilson(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - m) / d, (c + m) / d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default=str(DEFAULT_CSV))
    ap.add_argument("--n", type=int, default=0, help="row cap (0 = all)")
    args = ap.parse_args()

    df = pd.read_csv(args.csv, nrows=args.n or None)
    n = len(df)
    df["is_returned"] = (df["delivery_status"] == "Returned").astype(int)
    y = df["is_returned"].to_numpy()
    base = y.mean()
    print(f"rows: {n:,}  base return rate: {base*100:.3f}%")

    print("== §1 UNIVARIATE (numeric) ==")
    desc = df[NUM].describe(percentiles=[0.25, 0.5, 0.75]).T
    desc["skew"] = df[NUM].skew(numeric_only=True)
    with pd.option_context("display.float_format", "{:,.2f}".format, "display.width", 200):
        print(desc[["count", "mean", "std", "min", "25%", "50%", "75%", "max", "skew"]].to_string())

    print("== §2 BIVARIATE vs RETURNED (categorical: chi2 + Cramer's V) ==")
    for c in CAT:
        ct = pd.crosstab(df[c], df["is_returned"])
        chi2, p, dof, _ = stats.chi2_contingency(ct.values)
        print(f"  {c}: chi2={chi2:,.0f} dof={dof} p={'<1e-300' if p == 0 else f'{p:.2g}'} "
              f"Cramer's V={cramers_v(chi2, n, *ct.shape):.4f} "
              f"{'(independent)' if cramers_v(chi2, n, *ct.shape) < 0.02 else ''}")

    print("== §2 BIVARIATE vs RETURNED (numeric: mean gap, Cohen's d, Mann-Whitney) ==")
    for c in NUM:
        a = df.loc[y == 1, c].to_numpy(dtype=float)
        b = df.loc[y == 0, c].to_numpy(dtype=float)
        d = (a.mean() - b.mean()) / math.sqrt((a.var() + b.var()) / 2)
        u, pu = stats.mannwhitneyu(a, b, alternative="two-sided")
        print(f"  {c}: mean(ret)={a.mean():,.2f} mean(keep)={b.mean():,.2f} "
              f"d={d:+.4f} MWU p={'<1e-300' if pu == 0 else f'{pu:.2g}'}")

    print("== §2 FOCUSED: the two cliffs (two-proportion z + Wilson CI) ==")
    for name, mask in {
        "ship==6d vs rest": (df["shipping_time_days"] == 6, df["shipping_time_days"] != 6),
        "rating<3 vs >=3": (df["rating"] < 3.0, df["rating"] >= 3.0),
    }.items():
        p1, n1 = y[mask[0]].mean(), mask[0].sum()
        p2, n2 = y[mask[1]].mean(), mask[1].sum()
        se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
        z = (p1 - p2) / se
        pval = 2 * (1 - stats.norm.cdf(abs(z)))
        ci1, ci2 = wilson(p1, n1), wilson(p2, n2)
        print(f"  {name}: {p1*100:.2f}% [{ci1[0]*100:.2f},{ci1[1]*100:.2f}] (n={n1:,}) vs "
              f"{p2*100:.2f}% [{ci2[0]*100:.2f},{ci2[1]*100:.2f}] (n={n2:,}) "
              f"z={z:.1f} p={'<1e-300' if pval == 0 else f'{pval:.2g}'}")

    print("== §2 delivery_status × ship/device (chi2, 4-class target) ==")
    for c in ("shipping_time_days", "device", "payment_method"):
        ct = pd.crosstab(df[c], df["delivery_status"])
        chi2, p, dof, _ = stats.chi2_contingency(ct.values)
        print(f"  {c}: chi2={chi2:,.0f} p={'<1e-300' if p == 0 else f'{p:.2g}'} "
              f"V={cramers_v(chi2, n, *ct.shape):.4f}")

    print("== §3 PCA (standardized numeric space) ==")
    X = (df[NUM].to_numpy(dtype=float) - df[NUM].mean().to_numpy()) / df[NUM].std().to_numpy()
    vals, vecs = np.linalg.eigh(np.cov(X, rowvar=False))
    order = np.argsort(vals)[::-1]
    vals, vecs = vals[order], vecs[:, order]
    tot = vals.sum()
    for i in range(len(NUM)):
        print(f"  PC{i+1}: explained {vals[i]/tot*100:5.2f}% (cumulative {vals[:i+1].sum()/tot*100:5.2f}%)")
    load = pd.DataFrame(vecs[:, :2], index=NUM, columns=["PC1", "PC2"]).round(3)
    print("  loadings (PC1/PC2):")
    print(load.to_string())
    z = X @ vecs[:, :2]
    c_ret, c_keep = z[y == 1].mean(axis=0), z[y == 0].mean(axis=0)
    dist = float(np.linalg.norm(c_ret - c_keep))
    print(f"  class-centroid distance in PC1–PC2: {dist:.4f} std units "
          f"({'no separation' if dist < 0.1 else 'separated'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
