-- Migration: Add obligations table for enhanced obligation tracking
-- Purpose: Replace separate deadlines/amounts tables with unified obligations table
-- Created: 2025-11-18

BEGIN;

-- Create obligations table
CREATE TABLE obligations (
  id BIGSERIAL,
  jurisdiction VARCHAR(10) NOT NULL,
  section_id TEXT NOT NULL,
  category TEXT NOT NULL,  -- deadline, amount, reporting, constraint, penalty, allocation, other
  phrase TEXT NOT NULL,     -- the extracted text phrase
  value NUMERIC,            -- extracted numeric value (nullable for non-numeric obligations)
  unit TEXT,                -- unit of measurement (days, dollars, years, etc.)
  confidence REAL,          -- confidence score from LLM extraction (0.0-1.0)
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  PRIMARY KEY (jurisdiction, id),
  FOREIGN KEY (jurisdiction, section_id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE
);

-- Create indexes for efficient querying
CREATE INDEX idx_obligations_jurisdiction ON obligations(jurisdiction);
CREATE INDEX idx_obligations_section ON obligations(jurisdiction, section_id);
CREATE INDEX idx_obligations_category ON obligations(jurisdiction, category);
CREATE INDEX idx_obligations_value ON obligations(value) WHERE value IS NOT NULL;

-- Add comment for documentation
COMMENT ON TABLE obligations IS 'Enhanced obligations extracted from legal code sections using LLM analysis';
COMMENT ON COLUMN obligations.category IS 'Type of obligation: deadline, amount, reporting, constraint, penalty, allocation, other';
COMMENT ON COLUMN obligations.phrase IS 'Original text phrase containing the obligation';
COMMENT ON COLUMN obligations.value IS 'Numeric value extracted from phrase (if applicable)';
COMMENT ON COLUMN obligations.unit IS 'Unit of measurement for the value (days, dollars, years, etc.)';
COMMENT ON COLUMN obligations.confidence IS 'LLM confidence score for the extraction (0.0-1.0)';

COMMIT;
