-- Add similarity classifications table
-- This table stores LLM-based classifications of why similar sections are related

CREATE TABLE IF NOT EXISTS dc_section_similarity_classifications (
  section_a text NOT NULL,
  section_b text NOT NULL,
  classification text NOT NULL CHECK (classification IN ('duplicate', 'superseded', 'related', 'conflicting')),
  explanation text NOT NULL,
  model_used text NOT NULL,
  analyzed_at timestamp with time zone NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  PRIMARY KEY (section_a, section_b),
  FOREIGN KEY (section_a, section_b)
    REFERENCES dc_section_similarities(section_a, section_b)
    ON DELETE CASCADE
);

-- Index on classification for filtering
CREATE INDEX IF NOT EXISTS dc_section_similarity_classifications_classification_idx
  ON dc_section_similarity_classifications(classification);

-- Index on model_used for analytics
CREATE INDEX IF NOT EXISTS dc_section_similarity_classifications_model_idx
  ON dc_section_similarity_classifications(model_used);

-- Verification query
SELECT
  'dc_section_similarity_classifications table created' as status,
  COUNT(*) as initial_count
FROM dc_section_similarity_classifications;
