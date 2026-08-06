-- Phase 2 — Schema layout
-- raw:      CSV landing (all TEXT, 1:1 with source) — Phase 3
-- staging:  typed / validated intermediate — Phase 3
-- public:   6 core application tables (this phase)
--
-- Idempotent: safe to re-run.

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;

COMMENT ON SCHEMA raw IS
  'Landing zone: CSV mirrored 1:1 as TEXT. Replayable, no transforms.';
COMMENT ON SCHEMA staging IS
  'Typed, trimmed, key-deduplicated intermediate between raw and core tables.';
