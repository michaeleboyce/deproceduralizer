-- Migration: Create indicator_feedback table for human review of AI findings
-- Purpose: Track reviewer feedback on anachronisms, implementation issues, and conflicts
-- Used for: prompt improvement, training data, display filtering, accuracy metrics

CREATE TABLE IF NOT EXISTS indicator_feedback (
  id BIGSERIAL PRIMARY KEY,

  -- What's being reviewed
  item_type VARCHAR(50) NOT NULL CHECK (item_type IN (
    'anachronism_indicator',
    'implementation_indicator',
    'similarity_classification'
  )),
  item_id BIGINT NOT NULL,
  jurisdiction VARCHAR(10) NOT NULL DEFAULT 'dc',

  -- Reviewer information
  reviewer_id VARCHAR(100) NOT NULL,  -- Email or unique identifier
  reviewer_name VARCHAR(255),         -- Display name

  -- Feedback rating (categorical with required comment)
  rating VARCHAR(50) NOT NULL CHECK (rating IN (
    'correct',              -- Finding is accurate and helpful
    'false_positive',       -- Finding is incorrect/not applicable
    'wrong_category',       -- Finding is valid but miscategorized
    'wrong_severity',       -- Severity/complexity level is wrong
    'missing_context',      -- Needs more context or explanation
    'needs_refinement'      -- Generally correct but needs improvement
  )),

  -- Required explanation (distinguishes from bookmarks)
  comment TEXT NOT NULL CHECK (LENGTH(TRIM(comment)) > 0),

  -- Optional corrections (populated when rating indicates error)
  suggested_category VARCHAR(100),    -- If wrong_category
  suggested_severity VARCHAR(20),     -- If wrong_severity (for anachronisms)
  suggested_complexity VARCHAR(20),   -- If wrong_severity (for implementations)

  -- Metadata
  reviewed_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

  -- One review per reviewer per item (can update existing review)
  CONSTRAINT unique_reviewer_per_item UNIQUE(item_type, item_id, reviewer_id)
);

-- Indexes for common query patterns
CREATE INDEX idx_indicator_feedback_item ON indicator_feedback(item_type, item_id);
CREATE INDEX idx_indicator_feedback_reviewer ON indicator_feedback(reviewer_id);
CREATE INDEX idx_indicator_feedback_rating ON indicator_feedback(rating);
CREATE INDEX idx_indicator_feedback_jurisdiction ON indicator_feedback(jurisdiction);
CREATE INDEX idx_indicator_feedback_reviewed_at ON indicator_feedback(reviewed_at DESC);

-- Index for finding unreviewed items (useful for queue)
CREATE INDEX idx_indicator_feedback_lookup ON indicator_feedback(item_type, item_id, jurisdiction);

-- Trigger to update updated_at on modifications
CREATE OR REPLACE FUNCTION update_indicator_feedback_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_indicator_feedback_updated_at
  BEFORE UPDATE ON indicator_feedback
  FOR EACH ROW
  EXECUTE FUNCTION update_indicator_feedback_updated_at();

-- Comments for documentation
COMMENT ON TABLE indicator_feedback IS 'Human reviewer feedback on AI-generated findings for model improvement and quality control';
COMMENT ON COLUMN indicator_feedback.item_type IS 'Type of finding being reviewed: anachronism_indicator, implementation_indicator, or similarity_classification';
COMMENT ON COLUMN indicator_feedback.rating IS 'Categorical rating: correct, false_positive, wrong_category, wrong_severity, missing_context, needs_refinement';
COMMENT ON COLUMN indicator_feedback.comment IS 'Required explanation of the rating (cannot be empty)';
COMMENT ON COLUMN indicator_feedback.suggested_category IS 'Correct category if rating is wrong_category';
COMMENT ON COLUMN indicator_feedback.suggested_severity IS 'Correct severity if rating is wrong_severity (anachronisms: CRITICAL, HIGH, MEDIUM, LOW)';
COMMENT ON COLUMN indicator_feedback.suggested_complexity IS 'Correct complexity if rating is wrong_severity (implementations: HIGH, MEDIUM, LOW)';
