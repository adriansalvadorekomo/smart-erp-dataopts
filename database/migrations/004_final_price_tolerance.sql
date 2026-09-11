-- Phase 3 — Widen final_price CHECK to the contract tolerance.
-- Source of truth: docs/business-model.md §6 (tolerance ±₹5.00).
--
-- Why: the source CSV round-trips final_price from higher precision.
-- Measured on the full 1M rows: max deviation ≈ ₹3.99, 920,997 rows exceed
-- ±₹0.01, zero rows exceed ±₹5.00. The ±₹0.01 CHECK from 002_core_tables.sql
-- would reject ~92% of real source rows, so it is superseded here.
-- Lakehouse parity: lakehouse/src/silver/transform.py FINAL_PRICE_TOLERANCE.
--
-- Idempotent: DROP IF EXISTS + ADD (safe to re-run).

ALTER TABLE public.order_items
  DROP CONSTRAINT IF EXISTS chk_order_items_final_price;

ALTER TABLE public.order_items
  ADD CONSTRAINT chk_order_items_final_price CHECK (
    abs(
      final_price
      - round(unit_price * quantity * (1 - discount_pct / 100), 2)
    ) <= 5.00
  );

COMMENT ON CONSTRAINT chk_order_items_final_price ON public.order_items IS
  'final_price = unit_price × qty × (1 − discount_pct/100), CHECK ±₹5.00 (business-model §6).';
