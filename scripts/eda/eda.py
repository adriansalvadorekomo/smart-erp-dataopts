#!/usr/bin/env python3
"""Phase 8 — Exploratory Data Analysis over the source CSV (stdlib only).

Answers two questions before any modeling:
  1. Data QUALITY: missing, invalid, duplicated, inconsistent values?
  2. SIGNAL: does the outcome (RETURNED) depend on anything observable,
     or is it generated independently (→ unlearnable)?

Usage:
    python3 scripts/eda/eda.py [--csv PATH]
"""
from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CSV = REPO / "data/amazon-e-commerce/amazon_ecommerce_1M.csv"
COLS = ["user_id", "product_id", "category", "subcategory", "brand", "price",
        "discount", "final_price", "rating", "review_count", "stock",
        "seller_id", "seller_rating", "purchase_date", "shipping_time_days",
        "location", "device", "payment_method", "is_returned", "delivery_status"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", default=str(DEFAULT_CSV))
    args = ap.parse_args()
    path = Path(args.csv)
    if not path.exists():
        print(f"ERROR: CSV not found: {path}")
        return 1

    n = 0
    nulls: Counter = Counter()
    cats: dict[str, Counter] = {c: Counter() for c in
        ("category", "subcategory", "brand", "location", "device",
         "payment_method", "delivery_status", "is_returned", "shipping_time_days")}
    ret_by: dict[str, dict[str, list]] = {c: defaultdict(lambda: [0, 0]) for c in
        ("category", "brand", "location", "device", "payment_method", "shipping_time_days")}
    price_dec, disc_band, rating_band, stock_band = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    per_day: Counter = Counter()
    ret_by_month: dict[str, list] = defaultdict(lambda: [0, 0])
    rev_by_month: dict[str, float] = defaultdict(float)
    devs, discounts, prices, stocks = [], [], [], []
    bad_dates, bad_rating, bad_stock, bad_ship, bad_price = 0, 0, 0, 0, 0
    dup_keys: Counter = Counter()
    users, products, sellers = set(), set(), set()

    with open(path, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        assert rdr.fieldnames == COLS, f"header drift: {rdr.fieldnames}"
        for row in rdr:
            n += 1
            for c in COLS:
                if row[c] is None or row[c].strip() == "":
                    nulls[c] += 1
            users.add(row["user_id"]); products.add(row["product_id"]); sellers.add(row["seller_id"])
            dup_keys[(row["user_id"], row["purchase_date"], row["product_id"])] += 1
            is_ret = 1 if row["delivery_status"] == "Returned" else 0
            for c in cats:
                cats[c][row[c]] += 1
            for c in ret_by:
                cell = ret_by[c][row[c]]
                cell[0] += 1; cell[1] += is_ret
            try:
                price, disc, fp = float(row["price"]), float(row["discount"]), float(row["final_price"])
                devs.append(abs(fp - round(price * (1 - disc / 100), 2)))
                prices.append(price); discounts.append(disc)
                if price <= 0: bad_price += 1
            except ValueError:
                bad_price += 1
            try:
                rating = float(row["rating"]); srating = float(row["seller_rating"])
                if not (0.0 <= rating <= 5.0 and 0.0 <= srating <= 5.0): bad_rating += 1
                rating_band[f"{math.floor(rating)}★"][0] += 1; rating_band[f"{math.floor(rating)}★"][1] += is_ret
            except ValueError:
                bad_rating += 1
            try:
                stock = int(row["stock"]); stocks.append(stock)
                if not (0 <= stock <= 500): bad_stock += 1
                key = "0" if stock == 0 else "<20" if stock < 20 else "20-100" if stock <= 100 else ">100"
                stock_band[key][0] += 1; stock_band[key][1] += is_ret
            except ValueError:
                bad_stock += 1
            d = row["purchase_date"]
            if len(d) != 10 or not ("2024-03-31" <= d <= "2026-03-31"): bad_dates += 1
            per_day[d] += 1
            m = d[:7]
            ret_by_month[m][0] += 1; ret_by_month[m][1] += is_ret; rev_by_month[m] += fp
            try:
                if not (1 <= int(row["shipping_time_days"]) <= 6): bad_ship += 1
            except ValueError:
                bad_ship += 1
            price_dec[f"₹{int(price//5000)*5}k-{int(price//5000)*5+5}k"][0] += 1
            price_dec[f"₹{int(price//5000)*5}k-{int(price//5000)*5+5}k"][1] += is_ret
            disc_band[f"{int(disc//10)*10}-{int(disc//10)*10+10}%"][0] += 1
            disc_band[f"{int(disc//10)*10}-{int(disc//10)*10+10}%"][1] += is_ret

    print(f"== 1. COMPLETENESS ({n:,} rows) ==")
    print(f"  null/empty cells: {dict(nulls) or 'NONE'}")
    print(f"  unique users/products/sellers: {len(users):,} / {len(products):,} / {len(sellers):,}")
    multi = sum(1 for v in dup_keys.values() if v > 1)
    print(f"  duplicate (user,date,product) baskets: {multi:,} (multi-item rate {multi/n*100:.2f}%)")
    print(f"  invalid: dates={bad_dates} ratings={bad_rating} stocks={bad_stock} ship_days={bad_ship} prices={bad_price}")

    print("== 2. LOW-CARDINALITY SHAPE (synthetic-uniformity check) ==")
    for c in ("category", "location", "device", "payment_method", "delivery_status"):
        vals = cats[c]
        total = sum(vals.values())
        shares = [v / total * 100 for v in vals.values()]
        print(f"  {c}: {len(vals)} values, share range {min(shares):.1f}–{max(shares):.1f}% {dict(vals)}")

    print("== 3. RETURN-RATE INDEPENDENCE (overall 11.60%) ==")
    def show(name, table):
        tot_r = sum(v[1] for v in table.values()); tot_n = sum(v[0] for v in table.values())
        rates = [(k, v[1] / v[0]) for k, v in sorted(table.items())]
        lo, hi = min(r for _, r in rates), max(r for _, r in rates)
        # binomial noise scale at smallest cell
        n_min = min(v[0] for v in table.values())
        noise = 2 * math.sqrt(0.116 * 0.884 / n_min)
        flag = "≈ noise" if (hi - lo) < 2 * noise else "REAL SPREAD"
        print(f"  {name}: range {lo*100:.2f}–{hi*100:.2f}% (noise band ±{noise*100:.2f}pp) → {flag}")
    for c in ret_by:
        show(c, ret_by[c])
    show("price decile-ish", price_dec)
    show("rating band", rating_band)
    show("stock band", stock_band)

    print("== 4. TEMPORAL ==")
    months = sorted(rev_by_month)
    print(f"  window: {months[0]} → {months[-1]} ({len(months)} months, {len(per_day)} days)")
    print(f"  monthly revenue first/last: ₹{rev_by_month[months[0]]/1e6:.1f}M → ₹{rev_by_month[months[-1]]/1e6:.1f}M")
    mr = [(m, ret_by_month[m][1] / ret_by_month[m][0]) for m in months]
    print(f"  monthly return rate: min {min(r for _, r in mr)*100:.2f}% / max {max(r for _, r in mr)*100:.2f}% (flat ⇒ no drift)")
    daily = sorted(per_day.values())
    print(f"  orders/day: median {daily[len(daily)//2]:,}")

    print("== 5. MONEY (final_price vs formula) ==")
    devs.sort()
    print(f"  |error|: p50 ₹{devs[len(devs)//2]:.2f} / p99 ₹{devs[int(len(devs)*0.99)]:.2f} / max ₹{devs[-1]:.2f}")
    print(f"  discount: mean {sum(discounts)/len(discounts):.1f}% max {max(discounts):.0f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
