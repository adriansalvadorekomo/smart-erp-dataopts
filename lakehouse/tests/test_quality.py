"""Unit tests for DQ rules + runner (R1–R9). Run: python -m unittest discover -s lakehouse/tests."""

import unittest

from lakehouse.src.quality import rules, runner
from lakehouse.tests.fixtures import BRONZE_COLUMNS, GOOD_ITEM, GOOD_ORDER


class TestRules(unittest.TestCase):
    def test_r1_null_key_detected(self):
        rows = [{"order_id": None, "customer_id": "U1"}]
        self.assertEqual(len(rules.check_no_null_keys(rows, ["order_id"], "orders")), 1)
        self.assertEqual(rules.check_no_null_keys([{"order_id": 1}], ["order_id"], "orders"), [])

    def test_r2_duplicate_business_key(self):
        rows = [{"customer_id": "U1"}, {"customer_id": "U1"}]
        self.assertEqual(len(rules.check_unique(rows, "customer_id", "customers")), 1)

    def test_r3_orphan_fk(self):
        rows = [{"order_id": 1, "product_id": "PX"}]
        self.assertEqual(len(rules.check_fk(rows, "product_id", {"P1"}, "order_items")), 1)
        self.assertEqual(rules.check_fk(rows, "product_id", {"P1", "PX"}, "order_items"), [])

    def test_r4_final_price(self):
        self.assertEqual(rules.check_final_price([dict(GOOD_ITEM)]), [])
        bad = dict(GOOD_ITEM, final_price=1.00)
        self.assertEqual(len(rules.check_final_price([bad])), 1)

    def test_r5_enums(self):
        self.assertEqual(rules.check_enums([dict(GOOD_ORDER)]), [])
        bad = dict(GOOD_ORDER, delivery_status="LOST")
        self.assertTrue(rules.check_enums([bad]))

    def test_r6_ranges(self):
        self.assertEqual(rules.check_ranges([dict(GOOD_ITEM)]), [])
        bad = dict(GOOD_ITEM, quantity=0, discount_pct=99)
        self.assertEqual(len(rules.check_ranges([bad])), 2)
        self.assertTrue(rules.check_ranges([dict(GOOD_ITEM)], [{"stock": 501}]))

    def test_r7_date_window(self):
        self.assertEqual(rules.check_date_window(["2025-06-15"]), [])
        self.assertTrue(rules.check_date_window(["2023-01-01"]))
        self.assertTrue(rules.check_date_window(["not-a-date"]))

    def test_r8_revenue_checksum(self):
        self.assertEqual(rules.check_revenue(9_938_876_985.0), [])
        self.assertTrue(rules.check_revenue(1.0))

    def test_r9_schema(self):
        self.assertEqual(rules.check_schema(BRONZE_COLUMNS, BRONZE_COLUMNS, "bronze.raw_purchases"), [])
        self.assertTrue(rules.check_schema(["user_id"], BRONZE_COLUMNS, "bronze.raw_purchases"))


class TestRunner(unittest.TestCase):
    def test_fail_fast_raises(self):
        results = [runner.RuleResult(name="R1", violations=["boom"])]
        with self.assertRaises(runner.DataQualityError):
            runner.fail_fast(results)

    def test_fail_fast_passes(self):
        results = [runner.RuleResult(name="R1", violations=[])]
        runner.fail_fast(results)  # must not raise

    def test_run_rule_logs_and_returns(self):
        res = runner.run_rule("R1", rules.check_no_null_keys, [{"a": 1}], ["a"], "t")
        self.assertTrue(res.passed)


if __name__ == "__main__":
    unittest.main()
