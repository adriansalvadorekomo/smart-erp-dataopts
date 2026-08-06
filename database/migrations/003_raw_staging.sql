-- Phase 2 foundation for Phase 3 ingestion contract (docs/business-model.md §6)
-- raw.purchases mirrors CSV columns 1:1 as TEXT — no types, no transforms.
-- staging.* holds typed, trimmed intermediates before normalize into public.*.
--
-- CSV header:
--   user_id,product_id,category,subcategory,brand,price,discount,final_price,
--   rating,review_count,stock,seller_id,seller_rating,purchase_date,
--   shipping_time_days,location,device,payment_method,is_returned,delivery_status

DROP TABLE IF EXISTS raw.purchases CASCADE;

CREATE TABLE raw.purchases (
  user_id            TEXT,
  product_id         TEXT,
  category           TEXT,
  subcategory        TEXT,
  brand              TEXT,
  price              TEXT,
  discount           TEXT,
  final_price        TEXT,
  rating             TEXT,
  review_count       TEXT,
  stock              TEXT,
  seller_id          TEXT,
  seller_rating      TEXT,
  purchase_date      TEXT,
  shipping_time_days TEXT,
  location           TEXT,
  device             TEXT,
  payment_method     TEXT,
  is_returned        TEXT,   -- dropped in normalize (redundant with delivery_status)
  delivery_status    TEXT
);

COMMENT ON TABLE raw.purchases IS
  'CSV landing (all TEXT). Loaded via COPY. Truncated on every full-refresh seed.';

-- Staging: one typed working table for the full event stream before entity split.
DROP TABLE IF EXISTS staging.purchases CASCADE;

CREATE TABLE staging.purchases (
  user_id            TEXT           NOT NULL,
  product_id         TEXT           NOT NULL,
  category           TEXT           NOT NULL,
  subcategory        TEXT           NOT NULL,
  brand              TEXT           NOT NULL,
  price              NUMERIC(10, 2) NOT NULL,
  discount           NUMERIC(4, 2)  NOT NULL,   -- source discount = discount_pct
  final_price        NUMERIC(10, 2) NOT NULL,
  rating             NUMERIC(2, 1)  NOT NULL,
  review_count       INTEGER        NOT NULL,
  stock              INTEGER        NOT NULL,
  seller_id          TEXT           NOT NULL,
  seller_rating      NUMERIC(2, 1)  NOT NULL,
  purchase_date      DATE           NOT NULL,
  shipping_time_days SMALLINT       NOT NULL,
  location           TEXT           NOT NULL,
  device             TEXT           NOT NULL,
  payment_method     TEXT           NOT NULL,
  delivery_status    TEXT           NOT NULL    -- still source Title Case until normalize
  -- is_returned intentionally omitted (business-model §2.8)
);

CREATE INDEX idx_stg_purchases_user    ON staging.purchases (user_id);
CREATE INDEX idx_stg_purchases_product ON staging.purchases (product_id);
CREATE INDEX idx_stg_purchases_seller  ON staging.purchases (seller_id);
CREATE INDEX idx_stg_purchases_date    ON staging.purchases (purchase_date);

COMMENT ON TABLE staging.purchases IS
  'Typed event stream. Normalize → customers/sellers/products/inventory/orders/order_items.';
