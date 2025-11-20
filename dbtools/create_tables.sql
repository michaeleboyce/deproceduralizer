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
  reporting_text     text,
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

-- Multi-jurisdiction schema for section tables
-- Universal sections table (replaces dc_sections for multi-jurisdiction support)
CREATE TABLE IF NOT EXISTS sections (
  jurisdiction   text NOT NULL,
  id             text NOT NULL,
  citation       text NOT NULL,
  heading        text NOT NULL,
  text_plain     text NOT NULL,
  text_html      text NOT NULL,
  ancestors      jsonb NOT NULL DEFAULT '[]'::jsonb,
  title_label    text NOT NULL,
  chapter_label  text NOT NULL,

  -- Full-text search column
  text_fts       tsvector GENERATED ALWAYS AS (
                    to_tsvector('english', text_plain)
                  ) STORED,

  -- Optional analysis fields
  has_reporting      boolean DEFAULT false,
  reporting_summary  text,
  reporting_text     text,
  reporting_tags     jsonb DEFAULT '[]'::jsonb,

  -- Metadata
  created_at     timestamp with time zone DEFAULT now(),
  updated_at     timestamp with time zone DEFAULT now(),

  PRIMARY KEY (jurisdiction, id)
);

-- Indexes for sections
CREATE INDEX IF NOT EXISTS sections_text_fts_idx
  ON sections USING GIN (text_fts);

CREATE INDEX IF NOT EXISTS sections_jurisdiction_idx
  ON sections (jurisdiction);

CREATE INDEX IF NOT EXISTS sections_title_idx
  ON sections (jurisdiction, title_label);

CREATE INDEX IF NOT EXISTS sections_chapter_idx
  ON sections (jurisdiction, chapter_label);

CREATE INDEX IF NOT EXISTS sections_has_reporting_idx
  ON sections (jurisdiction, has_reporting)
  WHERE has_reporting = true;

-- Multi-jurisdiction structure table
CREATE TABLE IF NOT EXISTS structure (
  jurisdiction   text NOT NULL,
  id             text NOT NULL,
  parent_id      text,
  level          text NOT NULL,
  label          text NOT NULL,
  heading        text NOT NULL,
  ordinal        integer NOT NULL,
  created_at     timestamp with time zone DEFAULT now(),
  PRIMARY KEY (jurisdiction, id)
);

-- Indexes for structure
CREATE INDEX IF NOT EXISTS structure_jurisdiction_idx
  ON structure (jurisdiction);

CREATE INDEX IF NOT EXISTS structure_parent_idx
  ON structure (jurisdiction, parent_id);

CREATE INDEX IF NOT EXISTS structure_level_idx
  ON structure (jurisdiction, level);

-- Multi-jurisdiction cross-references
CREATE TABLE IF NOT EXISTS section_refs (
  jurisdiction text NOT NULL,
  from_id      text NOT NULL,
  to_id        text NOT NULL,
  raw_cite     text NOT NULL,
  PRIMARY KEY (jurisdiction, from_id, to_id, raw_cite),
  FOREIGN KEY (jurisdiction, from_id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE,
  FOREIGN KEY (jurisdiction, to_id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE
);

-- Indexes for section_refs
CREATE INDEX IF NOT EXISTS section_refs_from_idx
  ON section_refs (jurisdiction, from_id);

CREATE INDEX IF NOT EXISTS section_refs_to_idx
  ON section_refs (jurisdiction, to_id);

-- Multi-jurisdiction similarities
CREATE TABLE IF NOT EXISTS section_similarities (
  jurisdiction text NOT NULL,
  section_a    text NOT NULL,
  section_b    text NOT NULL,
  similarity   real NOT NULL,
  PRIMARY KEY (jurisdiction, section_a, section_b),
  CHECK (section_a < section_b),
  FOREIGN KEY (jurisdiction, section_a) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE,
  FOREIGN KEY (jurisdiction, section_b) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE
);

-- Indexes for section_similarities
CREATE INDEX IF NOT EXISTS section_similarities_a_idx
  ON section_similarities (jurisdiction, section_a, similarity DESC);

CREATE INDEX IF NOT EXISTS section_similarities_b_idx
  ON section_similarities (jurisdiction, section_b, similarity DESC);

-- Multi-jurisdiction similarity classifications (with cross-encoder triage)
CREATE TABLE IF NOT EXISTS section_similarity_classifications (
  jurisdiction   text NOT NULL,
  section_a      text NOT NULL,
  section_b      text NOT NULL,
  classification text NOT NULL CHECK (classification IN ('duplicate', 'superseded', 'related', 'conflicting', 'unrelated')),
  explanation    text NOT NULL,
  model_used     text NOT NULL,
  analyzed_at    timestamp with time zone NOT NULL,

  -- Cross-encoder triage metadata (for Model Cascading optimization)
  cross_encoder_label text CHECK (cross_encoder_label IN ('entailment', 'contradiction', 'neutral') OR cross_encoder_label IS NULL),
  cross_encoder_score real CHECK (cross_encoder_score >= 0.0 OR cross_encoder_score IS NULL),  -- Allows unnormalized logits (can be > 1.0)

  potential_anachronism boolean DEFAULT false,
  created_at     timestamp with time zone DEFAULT now(),
  PRIMARY KEY (jurisdiction, section_a, section_b),
  CHECK (section_a < section_b),
  FOREIGN KEY (jurisdiction, section_a) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE,
  FOREIGN KEY (jurisdiction, section_b) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE
);

-- Indexes for section_similarity_classifications
CREATE INDEX IF NOT EXISTS section_similarity_classifications_a_idx
  ON section_similarity_classifications (jurisdiction, section_a);

CREATE INDEX IF NOT EXISTS section_similarity_classifications_b_idx
  ON section_similarity_classifications (jurisdiction, section_b);

CREATE INDEX IF NOT EXISTS section_similarity_classifications_class_idx
  ON section_similarity_classifications (jurisdiction, classification);

-- Index for auditing cross-encoder triage performance
CREATE INDEX IF NOT EXISTS section_similarity_classifications_ce_label_idx
  ON section_similarity_classifications (cross_encoder_label)
  WHERE cross_encoder_label IS NOT NULL;

-- Multi-jurisdiction reporting requirements
CREATE TABLE IF NOT EXISTS section_reporting (
  jurisdiction text NOT NULL,
  id           text NOT NULL,
  has_reporting boolean NOT NULL,
  reporting_summary text,
  analyzed_at  timestamp with time zone NOT NULL,
  model_used   text,
  created_at   timestamp with time zone DEFAULT now(),
  PRIMARY KEY (jurisdiction, id),
  FOREIGN KEY (jurisdiction, id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE
);

-- Indexes for section_reporting
CREATE INDEX IF NOT EXISTS section_reporting_has_reporting_idx
  ON section_reporting (jurisdiction, has_reporting)
  WHERE has_reporting = true;

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

--===============================================================================
-- ANACHRONISM DETECTION TABLES
--===============================================================================

-- Main anachronism analysis results
CREATE TABLE IF NOT EXISTS section_anachronisms (
  jurisdiction text NOT NULL,
  section_id text NOT NULL,
  has_anachronism boolean NOT NULL DEFAULT false,
  overall_severity text CHECK (overall_severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
  summary text,
  requires_immediate_review boolean NOT NULL DEFAULT false,
  model_used text,
  analyzed_at timestamp with time zone NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  PRIMARY KEY (jurisdiction, section_id),
  FOREIGN KEY (jurisdiction, section_id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE
);

-- Individual anachronism indicators
CREATE TABLE IF NOT EXISTS anachronism_indicators (
  id bigserial PRIMARY KEY,
  jurisdiction text NOT NULL,
  section_id text NOT NULL,
  category text NOT NULL CHECK (category IN (
    'jim_crow',
    'obsolete_technology',
    'defunct_agency',
    'gendered_titles',
    'archaic_measurements',
    'outdated_professions',
    'obsolete_legal_terms',
    'outdated_medical_terms',
    'obsolete_transportation',
    'obsolete_military',
    'prohibition_era',
    'outdated_education',
    'obsolete_religious',
    'age_based',
    'environmental_agricultural',
    'commercial_business',
    'outdated_social_structures',
    'obsolete_economic'
  )),
  severity text NOT NULL CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
  modern_equivalent text,
  recommendation text NOT NULL CHECK (recommendation IN ('REPEAL', 'UPDATE', 'REVIEW', 'PRESERVE')),
  explanation text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  FOREIGN KEY (jurisdiction, section_id) REFERENCES section_anachronisms(jurisdiction, section_id) ON DELETE CASCADE
);

-- Matched phrases for anachronisms (for UI highlighting)
CREATE TABLE IF NOT EXISTS section_anachronism_highlights (
  id bigserial PRIMARY KEY,
  indicator_id bigint NOT NULL REFERENCES anachronism_indicators(id) ON DELETE CASCADE,
  phrase text NOT NULL,
  created_at timestamp with time zone DEFAULT now()
);

-- Indexes for anachronism tables
CREATE INDEX IF NOT EXISTS section_anachronisms_severity_idx
  ON section_anachronisms (jurisdiction, overall_severity)
  WHERE has_anachronism = true;

CREATE INDEX IF NOT EXISTS section_anachronisms_immediate_review_idx
  ON section_anachronisms (jurisdiction, requires_immediate_review)
  WHERE requires_immediate_review = true;

CREATE INDEX IF NOT EXISTS anachronism_indicators_section_idx
  ON anachronism_indicators (jurisdiction, section_id);

CREATE INDEX IF NOT EXISTS anachronism_indicators_category_idx
  ON anachronism_indicators (category);

CREATE INDEX IF NOT EXISTS anachronism_indicators_severity_idx
  ON anachronism_indicators (severity);

CREATE INDEX IF NOT EXISTS anachronism_highlights_indicator_idx
  ON section_anachronism_highlights (indicator_id);

--===============================================================================
-- TRIGGER FUNCTIONS
--===============================================================================

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
