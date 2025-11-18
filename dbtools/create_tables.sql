-- Deproceduralizer Database Schema
-- DC Code sections, cross-references, obligations, and analysis results

-- Core sections table
CREATE TABLE IF NOT EXISTS dc_sections (
  id             text PRIMARY KEY,
  citation       text NOT NULL,
  heading        text NOT NULL,
  text_plain     text NOT NULL,
  text_html      text NOT NULL,
  ancestors      jsonb NOT NULL DEFAULT '[]'::jsonb,
  title_label    text NOT NULL,
  chapter_label  text NOT NULL,

  -- Full-text search column (auto-generated from text_plain)
  text_fts       tsvector GENERATED ALWAYS AS (
                    to_tsvector('english', text_plain)
                  ) STORED,

  -- Optional analysis fields (populated by pipeline)
  has_reporting      boolean DEFAULT false,
  reporting_summary  text,
  reporting_tags     jsonb DEFAULT '[]'::jsonb,

  -- Metadata
  created_at     timestamp with time zone DEFAULT now(),
  updated_at     timestamp with time zone DEFAULT now()
);

-- Indexes for dc_sections
CREATE INDEX IF NOT EXISTS dc_sections_text_fts_idx
  ON dc_sections USING GIN (text_fts);

CREATE INDEX IF NOT EXISTS dc_sections_title_idx
  ON dc_sections (title_label);

CREATE INDEX IF NOT EXISTS dc_sections_chapter_idx
  ON dc_sections (chapter_label);

CREATE INDEX IF NOT EXISTS dc_sections_has_reporting_idx
  ON dc_sections (has_reporting)
  WHERE has_reporting = true;

-- Cross-references between sections
CREATE TABLE IF NOT EXISTS dc_section_refs (
  from_id  text NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  to_id    text NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  raw_cite text NOT NULL,
  PRIMARY KEY (from_id, to_id, raw_cite)
);

-- Indexes for cross-references
CREATE INDEX IF NOT EXISTS dc_section_refs_from_idx
  ON dc_section_refs (from_id);

CREATE INDEX IF NOT EXISTS dc_section_refs_to_idx
  ON dc_section_refs (to_id);

-- Deadlines extracted from sections
CREATE TABLE IF NOT EXISTS dc_section_deadlines (
  id         bigserial PRIMARY KEY,
  section_id text NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  phrase     text NOT NULL,
  days       integer NOT NULL,
  kind       text NOT NULL,
  created_at timestamp with time zone DEFAULT now()
);

-- Index for deadlines
CREATE INDEX IF NOT EXISTS dc_section_deadlines_section_idx
  ON dc_section_deadlines (section_id);

CREATE INDEX IF NOT EXISTS dc_section_deadlines_days_idx
  ON dc_section_deadlines (days);

-- Dollar amounts extracted from sections
CREATE TABLE IF NOT EXISTS dc_section_amounts (
  id           bigserial PRIMARY KEY,
  section_id   text NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  phrase       text NOT NULL,
  amount_cents bigint NOT NULL,
  created_at   timestamp with time zone DEFAULT now()
);

-- Index for amounts
CREATE INDEX IF NOT EXISTS dc_section_amounts_section_idx
  ON dc_section_amounts (section_id);

CREATE INDEX IF NOT EXISTS dc_section_amounts_amount_idx
  ON dc_section_amounts (amount_cents);

-- Global tags (for categorization)
CREATE TABLE IF NOT EXISTS dc_global_tags (
  tag        text PRIMARY KEY,
  created_at timestamp with time zone DEFAULT now()
);

-- Section-to-tag mapping
CREATE TABLE IF NOT EXISTS dc_section_tags (
  section_id text NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  tag        text NOT NULL REFERENCES dc_global_tags(tag) ON DELETE CASCADE,
  PRIMARY KEY (section_id, tag)
);

-- Index for section tags
CREATE INDEX IF NOT EXISTS dc_section_tags_section_idx
  ON dc_section_tags (section_id);

CREATE INDEX IF NOT EXISTS dc_section_tags_tag_idx
  ON dc_section_tags (tag);

-- Similar sections (computed via embeddings)
CREATE TABLE IF NOT EXISTS dc_section_similarities (
  section_a  text NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  section_b  text NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  similarity real NOT NULL,
  PRIMARY KEY (section_a, section_b),
  CHECK (section_a < section_b)  -- Ensure alphabetical order to avoid duplicates
);

-- Index for similarities (optimized for "find similar to X" queries)
CREATE INDEX IF NOT EXISTS dc_section_similarities_a_idx
  ON dc_section_similarities (section_a, similarity DESC);

CREATE INDEX IF NOT EXISTS dc_section_similarities_b_idx
  ON dc_section_similarities (section_b, similarity DESC);

-- Highlight phrases for reporting requirements
CREATE TABLE IF NOT EXISTS dc_section_highlights (
  id         bigserial PRIMARY KEY,
  section_id text NOT NULL REFERENCES dc_sections(id) ON DELETE CASCADE,
  phrase     text NOT NULL,
  created_at timestamp with time zone DEFAULT now()
);

-- Index for highlights
CREATE INDEX IF NOT EXISTS dc_section_highlights_section_idx
  ON dc_section_highlights (section_id);

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update timestamp trigger to dc_sections
DROP TRIGGER IF EXISTS update_dc_sections_updated_at ON dc_sections;
CREATE TRIGGER update_dc_sections_updated_at
  BEFORE UPDATE ON dc_sections
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Verification queries (uncomment to run after creating tables)
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
-- SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname;
