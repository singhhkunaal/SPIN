-- ============================================================================
-- Treya Spend Diagnostic — Supabase Schema
-- Paste this entire file into the Supabase SQL Editor and click "Run".
-- ============================================================================

-- Vendor dedupe enrichment cache
-- Caches results of enrich_dedupe_batch (standard name, parent, etc).
CREATE TABLE IF NOT EXISTS vendor_dedupe_memory (
    vendor_key         TEXT PRIMARY KEY,
    standard_name      TEXT,
    parent             TEXT,
    notes              TEXT,
    confidence_score   TEXT,
    updated_at         TIMESTAMPTZ DEFAULT now()
);

-- Vendor-to-category mapping cache
-- Caches results of enrich_map_batch (area + category mapping).
CREATE TABLE IF NOT EXISTS vendor_map_memory (
    vendor_key         TEXT PRIMARY KEY,
    area_mapping       TEXT,
    category_mapping   TEXT,
    notes              TEXT,
    confidence_score   TEXT,
    updated_at         TIMESTAMPTZ DEFAULT now()
);

-- Company research cache (key = "company|pe_firm")
CREATE TABLE IF NOT EXISTS company_research_memory (
    research_key   TEXT PRIMARY KEY,
    research_text  TEXT,
    updated_at     TIMESTAMPTZ DEFAULT now()
);

-- Savings benchmarks cache (key = category name)
CREATE TABLE IF NOT EXISTS savings_benchmarks_memory (
    category           TEXT PRIMARY KEY,
    addressability     NUMERIC,
    savings_low_pct    NUMERIC,
    savings_high_pct   NUMERIC,
    notes              TEXT,
    updated_at         TIMESTAMPTZ DEFAULT now()
);

-- Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_touch_vendor_dedupe ON vendor_dedupe_memory;
CREATE TRIGGER trg_touch_vendor_dedupe
    BEFORE UPDATE ON vendor_dedupe_memory
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trg_touch_vendor_map ON vendor_map_memory;
CREATE TRIGGER trg_touch_vendor_map
    BEFORE UPDATE ON vendor_map_memory
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trg_touch_research ON company_research_memory;
CREATE TRIGGER trg_touch_research
    BEFORE UPDATE ON company_research_memory
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

DROP TRIGGER IF EXISTS trg_touch_benchmarks ON savings_benchmarks_memory;
CREATE TRIGGER trg_touch_benchmarks
    BEFORE UPDATE ON savings_benchmarks_memory
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- Optional: enable row-level security and lock everything down so only the
-- service-role key (used by your Streamlit app) can read/write.
-- The anon key (used in browsers) gets no access at all.
ALTER TABLE vendor_dedupe_memory       ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendor_map_memory          ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_research_memory    ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings_benchmarks_memory  ENABLE ROW LEVEL SECURITY;
