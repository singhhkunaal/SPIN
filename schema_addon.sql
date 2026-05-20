-- ============================================================================
-- One-time schema upgrade for dashboard integration
-- ----------------------------------------------------------------------------
-- Run this once in Supabase → SQL Editor → New query → paste → Run.
-- Safe to re-run: "IF NOT EXISTS" makes it idempotent.
-- ============================================================================

ALTER TABLE savings_benchmarks_memory
    ADD COLUMN IF NOT EXISTS strategy_json TEXT;

-- Verify (should now list strategy_json as a column):
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'savings_benchmarks_memory';
