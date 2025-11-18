-- Multi-Jurisdiction Schema Migration
-- Transforms DC-specific schema into jurisdiction-agnostic schema
-- Supports: DC, California, New York, and other legal codes
--
-- IMPORTANT: Create database snapshot before running this migration!
-- Rollback script: rollback_multi_jurisdiction.sql
--
-- Migration Steps:
-- 1. Create jurisdictions metadata table
-- 2. Rename dc_* tables (remove prefix)
-- 3. Add jurisdiction column to all tables
-- 4. Convert PKs to composite (jurisdiction, id)
-- 5. Update all FKs to include jurisdiction
-- 6. Create structure table for hierarchical law
-- 7. Create indexes
-- 8. Populate jurisdiction column with 'dc' for existing data

BEGIN;

-- ============================================================================
-- STEP 1: Create jurisdictions metadata table
-- ============================================================================

CREATE TABLE IF NOT EXISTS jurisdictions (
  id VARCHAR(10) PRIMARY KEY,           -- 'dc', 'ca', 'ny', etc.
  name TEXT NOT NULL,                   -- 'District of Columbia Code'
  abbreviation VARCHAR(10) NOT NULL,    -- 'DC'
  type TEXT NOT NULL,                   -- 'district', 'state', 'county', 'city'
  parser_version TEXT NOT NULL,         -- '0.2.0'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- STEP 2: Rename tables (remove dc_ prefix)
-- ============================================================================

-- Core tables
ALTER TABLE IF EXISTS dc_sections RENAME TO sections_temp;
ALTER TABLE IF EXISTS dc_section_refs RENAME TO section_refs_temp;
ALTER TABLE IF EXISTS dc_section_deadlines RENAME TO section_deadlines_temp;
ALTER TABLE IF EXISTS dc_section_amounts RENAME TO section_amounts_temp;
ALTER TABLE IF EXISTS dc_section_similarities RENAME TO section_similarities_temp;
ALTER TABLE IF EXISTS dc_section_similarity_classifications RENAME TO section_similarity_classifications_temp;
ALTER TABLE IF EXISTS dc_section_highlights RENAME TO section_highlights_temp;

-- Tag tables
ALTER TABLE IF EXISTS dc_global_tags RENAME TO global_tags_temp;
ALTER TABLE IF EXISTS dc_section_tags RENAME TO section_tags_temp;

-- ============================================================================
-- STEP 3: Add jurisdiction column to all tables (populate with 'dc')
-- ============================================================================

-- sections table
ALTER TABLE sections_temp ADD COLUMN jurisdiction VARCHAR(10) DEFAULT 'dc' NOT NULL;

-- section_refs table
ALTER TABLE section_refs_temp ADD COLUMN jurisdiction VARCHAR(10) DEFAULT 'dc' NOT NULL;

-- section_deadlines table
ALTER TABLE section_deadlines_temp ADD COLUMN jurisdiction VARCHAR(10) DEFAULT 'dc' NOT NULL;

-- section_amounts table
ALTER TABLE section_amounts_temp ADD COLUMN jurisdiction VARCHAR(10) DEFAULT 'dc' NOT NULL;

-- section_similarities table
ALTER TABLE section_similarities_temp ADD COLUMN jurisdiction VARCHAR(10) DEFAULT 'dc' NOT NULL;

-- section_similarity_classifications table
ALTER TABLE section_similarity_classifications_temp ADD COLUMN jurisdiction VARCHAR(10) DEFAULT 'dc' NOT NULL;

-- section_highlights table
ALTER TABLE section_highlights_temp ADD COLUMN jurisdiction VARCHAR(10) DEFAULT 'dc' NOT NULL;

-- section_tags table (maps sections to tags)
ALTER TABLE section_tags_temp ADD COLUMN jurisdiction VARCHAR(10) DEFAULT 'dc' NOT NULL;

-- Note: global_tags remains jurisdiction-agnostic (tags shared across all jurisdictions)

-- ============================================================================
-- STEP 4: Drop old constraints and indexes (to be recreated with new structure)
-- ============================================================================

-- Drop FK constraints on sections_temp
ALTER TABLE section_refs_temp DROP CONSTRAINT IF EXISTS dc_section_refs_from_id_fkey;
ALTER TABLE section_refs_temp DROP CONSTRAINT IF EXISTS dc_section_refs_to_id_fkey;
ALTER TABLE section_deadlines_temp DROP CONSTRAINT IF EXISTS dc_section_deadlines_section_id_fkey;
ALTER TABLE section_amounts_temp DROP CONSTRAINT IF EXISTS dc_section_amounts_section_id_fkey;
ALTER TABLE section_similarities_temp DROP CONSTRAINT IF EXISTS dc_section_similarities_section_a_fkey;
ALTER TABLE section_similarities_temp DROP CONSTRAINT IF EXISTS dc_section_similarities_section_b_fkey;
ALTER TABLE section_highlights_temp DROP CONSTRAINT IF EXISTS dc_section_highlights_section_id_fkey;
ALTER TABLE section_tags_temp DROP CONSTRAINT IF EXISTS dc_section_tags_section_id_fkey;
ALTER TABLE section_tags_temp DROP CONSTRAINT IF EXISTS dc_section_tags_tag_fkey;

-- Drop FK constraint on similarity_classifications (references similarities)
ALTER TABLE section_similarity_classifications_temp DROP CONSTRAINT IF EXISTS dc_section_similarity_classifications_section_a_section_b_fkey;

-- Drop old primary keys
ALTER TABLE sections_temp DROP CONSTRAINT IF EXISTS dc_sections_pkey;
ALTER TABLE section_refs_temp DROP CONSTRAINT IF EXISTS dc_section_refs_pkey;
ALTER TABLE section_similarities_temp DROP CONSTRAINT IF EXISTS dc_section_similarities_pkey;
ALTER TABLE section_similarity_classifications_temp DROP CONSTRAINT IF EXISTS dc_section_similarity_classifications_pkey;
ALTER TABLE section_tags_temp DROP CONSTRAINT IF EXISTS dc_section_tags_pkey;

-- ============================================================================
-- STEP 5: Create new tables with proper jurisdiction-aware schema
-- ============================================================================

-- sections table with composite PK
CREATE TABLE sections (
  jurisdiction VARCHAR(10) NOT NULL,
  id TEXT NOT NULL,
  citation TEXT NOT NULL,
  heading TEXT NOT NULL,
  text_plain TEXT NOT NULL,
  text_html TEXT NOT NULL,
  ancestors JSONB NOT NULL DEFAULT '[]'::jsonb,
  title_label TEXT NOT NULL,
  chapter_label TEXT NOT NULL,
  text_fts TSVECTOR GENERATED ALWAYS AS (
    to_tsvector('english', text_plain)
  ) STORED,
  has_reporting BOOLEAN DEFAULT false,
  reporting_summary TEXT,
  reporting_tags JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (jurisdiction, id),
  FOREIGN KEY (jurisdiction) REFERENCES jurisdictions(id) ON DELETE CASCADE
);

-- section_refs table with composite PK and FKs
CREATE TABLE section_refs (
  jurisdiction VARCHAR(10) NOT NULL,
  from_id TEXT NOT NULL,
  to_id TEXT NOT NULL,
  raw_cite TEXT NOT NULL,
  PRIMARY KEY (jurisdiction, from_id, to_id, raw_cite),
  FOREIGN KEY (jurisdiction, from_id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE,
  FOREIGN KEY (jurisdiction, to_id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE
);

-- section_deadlines table
CREATE TABLE section_deadlines (
  id BIGSERIAL,
  jurisdiction VARCHAR(10) NOT NULL,
  section_id TEXT NOT NULL,
  phrase TEXT NOT NULL,
  days INTEGER NOT NULL,
  kind TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (jurisdiction, id),
  FOREIGN KEY (jurisdiction, section_id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE
);

-- section_amounts table
CREATE TABLE section_amounts (
  id BIGSERIAL,
  jurisdiction VARCHAR(10) NOT NULL,
  section_id TEXT NOT NULL,
  phrase TEXT NOT NULL,
  amount_cents BIGINT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (jurisdiction, id),
  FOREIGN KEY (jurisdiction, section_id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE
);

-- section_similarities table
CREATE TABLE section_similarities (
  jurisdiction VARCHAR(10) NOT NULL,
  section_a TEXT NOT NULL,
  section_b TEXT NOT NULL,
  similarity REAL NOT NULL,
  PRIMARY KEY (jurisdiction, section_a, section_b),
  FOREIGN KEY (jurisdiction, section_a) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE,
  FOREIGN KEY (jurisdiction, section_b) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE,
  CHECK (section_a < section_b)
);

-- section_similarity_classifications table
CREATE TABLE section_similarity_classifications (
  jurisdiction VARCHAR(10) NOT NULL,
  section_a TEXT NOT NULL,
  section_b TEXT NOT NULL,
  classification TEXT NOT NULL CHECK (classification IN ('duplicate', 'superseded', 'related', 'conflicting')),
  explanation TEXT NOT NULL,
  model_used TEXT NOT NULL,
  analyzed_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (jurisdiction, section_a, section_b),
  FOREIGN KEY (jurisdiction, section_a, section_b)
    REFERENCES section_similarities(jurisdiction, section_a, section_b)
    ON DELETE CASCADE
);

-- section_highlights table
CREATE TABLE section_highlights (
  id BIGSERIAL,
  jurisdiction VARCHAR(10) NOT NULL,
  section_id TEXT NOT NULL,
  phrase TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (jurisdiction, id),
  FOREIGN KEY (jurisdiction, section_id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE
);

-- global_tags table (remains jurisdiction-agnostic)
CREATE TABLE global_tags (
  tag TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- section_tags table (links sections to tags)
CREATE TABLE section_tags (
  jurisdiction VARCHAR(10) NOT NULL,
  section_id TEXT NOT NULL,
  tag TEXT NOT NULL,
  PRIMARY KEY (jurisdiction, section_id, tag),
  FOREIGN KEY (jurisdiction, section_id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE,
  FOREIGN KEY (tag) REFERENCES global_tags(tag) ON DELETE CASCADE
);

-- ============================================================================
-- STEP 6: Insert DC jurisdiction (must be done before copying data due to FK constraint)
-- ============================================================================

INSERT INTO jurisdictions (id, name, abbreviation, type, parser_version)
VALUES ('dc', 'District of Columbia Code', 'DC', 'district', '0.2.0');

-- ============================================================================
-- STEP 7: Copy data from temp tables to new tables
-- ============================================================================

-- Copy sections (explicitly list columns to handle jurisdiction)
INSERT INTO sections (jurisdiction, id, citation, heading, text_plain, text_html, ancestors, title_label, chapter_label, has_reporting, reporting_summary, reporting_tags, created_at, updated_at)
SELECT jurisdiction, id, citation, heading, text_plain, text_html, ancestors, title_label, chapter_label, has_reporting, reporting_summary, reporting_tags, created_at, updated_at
FROM sections_temp;

-- Copy section_refs
INSERT INTO section_refs (jurisdiction, from_id, to_id, raw_cite)
SELECT jurisdiction, from_id, to_id, raw_cite
FROM section_refs_temp;

-- Copy section_deadlines
INSERT INTO section_deadlines (id, jurisdiction, section_id, phrase, days, kind, created_at)
SELECT id, jurisdiction, section_id, phrase, days, kind, created_at
FROM section_deadlines_temp;

-- Copy section_amounts
INSERT INTO section_amounts (id, jurisdiction, section_id, phrase, amount_cents, created_at)
SELECT id, jurisdiction, section_id, phrase, amount_cents, created_at
FROM section_amounts_temp;

-- Copy section_similarities
INSERT INTO section_similarities (jurisdiction, section_a, section_b, similarity)
SELECT jurisdiction, section_a, section_b, similarity
FROM section_similarities_temp;

-- Fix classification values that don't match CHECK constraint
-- Map 'unrelated' -> 'related' and fix typo 'superseted' -> 'superseded'
UPDATE section_similarity_classifications_temp
SET classification = 'related'
WHERE classification = 'unrelated';

UPDATE section_similarity_classifications_temp
SET classification = 'superseded'
WHERE classification = 'superseted';

-- Copy section_similarity_classifications (now with valid values only)
INSERT INTO section_similarity_classifications (jurisdiction, section_a, section_b, classification, explanation, model_used, analyzed_at, created_at)
SELECT jurisdiction, section_a, section_b, classification, explanation, model_used, analyzed_at, created_at
FROM section_similarity_classifications_temp;

-- Copy section_highlights
INSERT INTO section_highlights (id, jurisdiction, section_id, phrase, created_at)
SELECT id, jurisdiction, section_id, phrase, created_at
FROM section_highlights_temp;

-- Copy global_tags
INSERT INTO global_tags (tag, created_at)
SELECT tag, created_at
FROM global_tags_temp;

-- Copy section_tags
INSERT INTO section_tags (jurisdiction, section_id, tag)
SELECT jurisdiction, section_id, tag
FROM section_tags_temp;

-- ============================================================================
-- STEP 8: Drop temp tables
-- ============================================================================

DROP TABLE IF EXISTS sections_temp CASCADE;
DROP TABLE IF EXISTS section_refs_temp CASCADE;
DROP TABLE IF EXISTS section_deadlines_temp CASCADE;
DROP TABLE IF EXISTS section_amounts_temp CASCADE;
DROP TABLE IF EXISTS section_similarities_temp CASCADE;
DROP TABLE IF EXISTS section_similarity_classifications_temp CASCADE;
DROP TABLE IF EXISTS section_highlights_temp CASCADE;
DROP TABLE IF EXISTS global_tags_temp CASCADE;
DROP TABLE IF EXISTS section_tags_temp CASCADE;

-- ============================================================================
-- STEP 9: Create indexes
-- ============================================================================

-- Indexes on sections
CREATE INDEX idx_sections_jurisdiction ON sections(jurisdiction);
CREATE INDEX idx_sections_text_fts ON sections USING GIN(text_fts);
CREATE INDEX idx_sections_title ON sections(jurisdiction, title_label);
CREATE INDEX idx_sections_chapter ON sections(jurisdiction, chapter_label);
CREATE INDEX idx_sections_has_reporting ON sections(jurisdiction, has_reporting) WHERE has_reporting = true;

-- Indexes on section_refs
CREATE INDEX idx_section_refs_from ON section_refs(jurisdiction, from_id);
CREATE INDEX idx_section_refs_to ON section_refs(jurisdiction, to_id);

-- Indexes on section_deadlines
CREATE INDEX idx_section_deadlines_section ON section_deadlines(jurisdiction, section_id);
CREATE INDEX idx_section_deadlines_days ON section_deadlines(days);

-- Indexes on section_amounts
CREATE INDEX idx_section_amounts_section ON section_amounts(jurisdiction, section_id);
CREATE INDEX idx_section_amounts_amount ON section_amounts(amount_cents);

-- Indexes on section_similarities
CREATE INDEX idx_section_similarities_a ON section_similarities(jurisdiction, section_a, similarity DESC);
CREATE INDEX idx_section_similarities_b ON section_similarities(jurisdiction, section_b, similarity DESC);

-- Indexes on section_similarity_classifications
CREATE INDEX idx_section_similarity_classifications_classification
  ON section_similarity_classifications(jurisdiction, classification);
CREATE INDEX idx_section_similarity_classifications_model
  ON section_similarity_classifications(model_used);

-- Indexes on section_highlights
CREATE INDEX idx_section_highlights_section ON section_highlights(jurisdiction, section_id);

-- Indexes on section_tags
CREATE INDEX idx_section_tags_section ON section_tags(jurisdiction, section_id);
CREATE INDEX idx_section_tags_tag ON section_tags(tag);

-- ============================================================================
-- STEP 10: Create structure table for hierarchical law representation
-- ============================================================================

CREATE TABLE structure (
  jurisdiction VARCHAR(10) NOT NULL,
  id TEXT NOT NULL,
  parent_id TEXT,
  level TEXT NOT NULL,         -- 'title', 'subtitle', 'chapter', 'subchapter', 'section'
  label TEXT NOT NULL,          -- 'Title 1', 'Chapter 3', etc.
  heading TEXT,
  ordinal INTEGER,              -- For sorting
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (jurisdiction, id),
  FOREIGN KEY (jurisdiction) REFERENCES jurisdictions(id) ON DELETE CASCADE,
  FOREIGN KEY (jurisdiction, parent_id) REFERENCES structure(jurisdiction, id) ON DELETE CASCADE
);

-- Indexes on structure
CREATE INDEX idx_structure_jurisdiction ON structure(jurisdiction);
CREATE INDEX idx_structure_parent ON structure(jurisdiction, parent_id);
CREATE INDEX idx_structure_level ON structure(jurisdiction, level);
CREATE INDEX idx_structure_ordinal ON structure(jurisdiction, ordinal);

-- ============================================================================
-- STEP 11: Recreate update trigger on sections table
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER update_sections_updated_at
  BEFORE UPDATE ON sections
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- STEP 12: Verification queries
-- ============================================================================

-- List all tables (should show new names without dc_ prefix)
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_name NOT LIKE '%_temp%'
ORDER BY table_name;

-- Count records in new sections table
SELECT
  'sections' as table_name,
  jurisdiction,
  COUNT(*) as record_count
FROM sections
GROUP BY jurisdiction;

-- Verify indexes created
SELECT
  tablename,
  indexname
FROM pg_indexes
WHERE schemaname = 'public' AND tablename IN (
  'sections', 'section_refs', 'section_deadlines', 'section_amounts',
  'section_similarities', 'section_similarity_classifications',
  'section_highlights', 'section_tags', 'structure', 'jurisdictions'
)
ORDER BY tablename, indexname;

COMMIT;

-- ============================================================================
-- Migration Complete!
-- ============================================================================
-- Next steps:
-- 1. Run this script: psql $DATABASE_URL -f add_multi_jurisdiction.sql
-- 2. Insert DC jurisdiction: INSERT INTO jurisdictions VALUES ('dc', 'District of Columbia Code', 'DC', 'district', '0.2.0');
-- 3. Update web app schema.ts (apps/web/db/schema.ts)
-- 4. Update all queries to include WHERE jurisdiction = 'dc'
-- ============================================================================
