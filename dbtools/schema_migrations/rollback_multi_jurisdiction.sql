-- Rollback Script for Multi-Jurisdiction Migration
-- Reverts add_multi_jurisdiction.sql changes
--
-- WARNING: This will restore the DC-specific schema (dc_* tables)
-- Only use this if migration failed or needs to be rolled back
--
-- Alternative: Restore from database snapshot/backup

BEGIN;

-- ============================================================================
-- STEP 1: Drop new tables with jurisdiction support
-- ============================================================================

DROP TABLE IF EXISTS section_tags CASCADE;
DROP TABLE IF EXISTS section_highlights CASCADE;
DROP TABLE IF EXISTS section_similarity_classifications CASCADE;
DROP TABLE IF EXISTS section_similarities CASCADE;
DROP TABLE IF EXISTS section_amounts CASCADE;
DROP TABLE IF EXISTS section_deadlines CASCADE;
DROP TABLE IF EXISTS section_refs CASCADE;
DROP TABLE IF EXISTS sections CASCADE;
DROP TABLE IF EXISTS structure CASCADE;
DROP TABLE IF EXISTS global_tags CASCADE;
DROP TABLE IF EXISTS jurisdictions CASCADE;

-- ============================================================================
-- STEP 2: Recreate original DC-specific schema
-- ============================================================================

-- Core sections table (original schema)
CREATE TABLE dc_sections (
  id             TEXT PRIMARY KEY,
  citation       TEXT NOT NULL,
  heading        TEXT NOT NULL,
  text_plain     TEXT NOT NULL,
  text_html      TEXT NOT NULL,
  ancestors      JSONB NOT NULL DEFAULT '[]'::jsonb,
  title_label    TEXT NOT NULL,
  chapter_label  TEXT NOT NULL,
  text_fts       TSVECTOR GENERATED ALWAYS AS (
                    to_tsvector('english', text_plain)
                  ) STORED,
  has_reporting      BOOLEAN DEFAULT false,
  reporting_summary  TEXT,
  reporting_tags     JSONB DEFAULT '[]'::jsonb,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for dc_sections
CREATE INDEX dc_sections_text_fts_idx ON dc_sections USING GIN (text_fts);
CREATE INDEX dc_sections_title_idx ON dc_sections (title_label);
CREATE INDEX dc_sections_chapter_idx ON dc_sections (chapter_label);
CREATE INDEX dc_sections_has_reporting_idx ON dc_sections (has_reporting) WHERE has_reporting = true;

-- Cross-references
CREATE TABLE dc_section_refs (
  from_id  TEXT NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  to_id    TEXT NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  raw_cite TEXT NOT NULL,
  PRIMARY KEY (from_id, to_id, raw_cite)
);

CREATE INDEX dc_section_refs_from_idx ON dc_section_refs (from_id);
CREATE INDEX dc_section_refs_to_idx ON dc_section_refs (to_id);

-- Deadlines
CREATE TABLE dc_section_deadlines (
  id         BIGSERIAL PRIMARY KEY,
  section_id TEXT NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  phrase     TEXT NOT NULL,
  days       INTEGER NOT NULL,
  kind       TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX dc_section_deadlines_section_idx ON dc_section_deadlines (section_id);
CREATE INDEX dc_section_deadlines_days_idx ON dc_section_deadlines (days);

-- Amounts
CREATE TABLE dc_section_amounts (
  id           BIGSERIAL PRIMARY KEY,
  section_id   TEXT NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  phrase       TEXT NOT NULL,
  amount_cents BIGINT NOT NULL,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX dc_section_amounts_section_idx ON dc_section_amounts (section_id);
CREATE INDEX dc_section_amounts_amount_idx ON dc_section_amounts (amount_cents);

-- Global tags
CREATE TABLE dc_global_tags (
  tag        TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Section tags
CREATE TABLE dc_section_tags (
  section_id TEXT NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  tag        TEXT NOT NULL REFERENCES dc_global_tags(tag) ON DELETE CASCADE,
  PRIMARY KEY (section_id, tag)
);

CREATE INDEX dc_section_tags_section_idx ON dc_section_tags (section_id);
CREATE INDEX dc_section_tags_tag_idx ON dc_section_tags (tag);

-- Similarities
CREATE TABLE dc_section_similarities (
  section_a  TEXT NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  section_b  TEXT NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  similarity REAL NOT NULL,
  PRIMARY KEY (section_a, section_b),
  CHECK (section_a < section_b)
);

CREATE INDEX dc_section_similarities_a_idx ON dc_section_similarities (section_a, similarity DESC);
CREATE INDEX dc_section_similarities_b_idx ON dc_section_similarities (section_b, similarity DESC);

-- Similarity classifications
CREATE TABLE dc_section_similarity_classifications (
  section_a TEXT NOT NULL,
  section_b TEXT NOT NULL,
  classification TEXT NOT NULL CHECK (classification IN ('duplicate', 'superseded', 'related', 'conflicting')),
  explanation TEXT NOT NULL,
  model_used TEXT NOT NULL,
  analyzed_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (section_a, section_b),
  FOREIGN KEY (section_a, section_b)
    REFERENCES dc_section_similarities(section_a, section_b)
    ON DELETE CASCADE
);

CREATE INDEX dc_section_similarity_classifications_classification_idx
  ON dc_section_similarity_classifications(classification);
CREATE INDEX dc_section_similarity_classifications_model_idx
  ON dc_section_similarity_classifications(model_used);

-- Highlights
CREATE TABLE dc_section_highlights (
  id         BIGSERIAL PRIMARY KEY,
  section_id TEXT NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  phrase     TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX dc_section_highlights_section_idx ON dc_section_highlights (section_id);

-- Update trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER update_dc_sections_updated_at
  BEFORE UPDATE ON dc_sections
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- STEP 3: Verification
-- ============================================================================

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE 'dc_%'
ORDER BY table_name;

COMMIT;

-- ============================================================================
-- Rollback Complete
-- ============================================================================
-- NOTE: This rollback creates empty tables with original schema.
-- You'll need to restore data from backup or re-run the pipeline.
-- ============================================================================
