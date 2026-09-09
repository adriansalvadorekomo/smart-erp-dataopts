"""Unit tests for Silver transforms + Bronze helpers + Gold KPI math."""

import unittest

from lakehouse.src.bronze.ingest import bronze_schema_ok, watermark_filter, with_audit_columns
from lakehouse.src.gold.models import (
    aov,
    discount_band,
    is_stock_critical,
    pareto_share,
    rate,
    total_revenue,
)
from lakehouse.src.silver.transform import (
    estimated_margin,
    final_price_ok,
    normalize_delivery_status,
    trim_record,
)


class TestBronze(unittest.TestCase):
    def test_audit_columns_stamped(self):
        rec = with_audit_columns({"user_id": "U1"}, source="postgres")
        self.assertEqual(rec["_source"], "postgres")
        self.assertIn("_ingest_ts", rec)
        self.assertEqual(rec["user_id"], "U1")  # original preserved

    def test_schema_ok(self):
        from lakehouse.tests.fixtures import BRONZE_COLUMNS

        ok, missing = bronze_schema_ok(list(BRONZE_COLUMNS))
        self.assertTrue(ok)
        self.assertEqual(missing, [])
        ok, missing = bronze_schema_ok(["user_id"])
        self.assertFalse(ok)
        self.assertIn("product_id", missing)

    def test_watermark(self):
        self.assertTrue(watermark_filter(None, "2024-04-01"))  # first load: everything
        self.assertTrue(watermark_filter("2025-01-01", "2025-06-15"))
        self.assertFalse(watermark_filter("2025-01-01", "2024-12-31"))
        self.assertFalse(watermark_filter("2025-01-01", "2025-01-01"))  # idempotent re-run


class TestSilver(unittest.TestCase):
    def test_normalize_delivery_status(self):
        self.assertEqual(normalize_delivery_status("In Transit"), "IN TRANSIT")
        self.assertEqual(normalize_delivery_status(" delivered "), "DELIVERED")
        with self.assertRaises(ValueError):
            normalize_delivery_status("LOST")

    def test_final_price_ok(self):
        self.assertTrue(final_price_ok(1000.00, 1, 10.0, 900.00))
        self.assertFalse(final_price_ok(1000.00, 1, 10.0, 1.00))

    def test_estimated_margin_labelled_by_caller(self):
        self.assertAlmostEqual(estimated_margin(1000.00, 1, 900.00), 250.00)

    def test_trim_record(self):
        self.assertEqual(trim_record({"a": "  x ", "n": 1}), {"a": "x", "n": 1})


class TestConfig(unittest.TestCase):
    def test_table_unity_catalog(self):
        from lakehouse.src.common.config import LakehouseConfig

        cfg = LakehouseConfig(catalog="smart_erp", use_uc=True)
        self.assertEqual(cfg.table("silver", "orders"), "smart_erp.silver.orders")

    def test_table_hive_fallback_community_edition(self):
        from lakehouse.src.common.config import LakehouseConfig

        cfg = LakehouseConfig(catalog="smart_erp", use_uc=False)
        self.assertEqual(cfg.table("silver", "orders"), "silver.orders")
        self.assertEqual(cfg.table("gold", "fact_sales"), "gold.fact_sales")

    def test_table_unknown_layer(self):
        from lakehouse.src.common.config import LakehouseConfig

        with self.assertRaises(ValueError):
            LakehouseConfig().table("platinum", "orders")


class TestGold(unittest.TestCase):
    def test_total_revenue_and_aov(self):
        self.assertEqual(total_revenue([900.00, 100.00]), 1000.00)
        self.assertEqual(aov(9_938_876_985.0, 1_000_000), 9938.88)
        with self.assertRaises(ValueError):
            aov(1.0, 0)

    def test_rate(self):
        self.assertEqual(rate(115990, 1_000_000), 0.116)  # K3 baseline
        with self.assertRaises(ValueError):
            rate(1, 0)

    def test_pareto_share(self):
        revs = [100.0, 30.0, 10.0, 5.0, 5.0]  # top 20% (1 cust) = 100/150
        self.assertAlmostEqual(pareto_share(revs), round(100 / 150, 4))

    def test_discount_band(self):
        self.assertEqual(discount_band(5), "0-10")
        self.assertEqual(discount_band(29), "10-30")
        self.assertEqual(discount_band(45), "30-50")
        self.assertEqual(discount_band(70), "50-70")
        with self.assertRaises(ValueError):
            discount_band(71)

    def test_stock_critical(self):
        self.assertTrue(is_stock_critical(19))
        self.assertFalse(is_stock_critical(20))


if __name__ == "__main__":
    unittest.main()
