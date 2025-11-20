-- Migration: Add Pahlka Implementation Analysis Tables
-- Date: 2025-01-19
-- Description: Creates tables for Jennifer Pahlka "Recoding America" framework analysis

--===============================================================================
-- PAHLKA IMPLEMENTATION ANALYSIS TABLES
--===============================================================================

-- Main Pahlka implementation analysis results
CREATE TABLE IF NOT EXISTS section_pahlka_implementations (
  jurisdiction text NOT NULL,
  section_id text NOT NULL,
  has_implementation_issues boolean NOT NULL DEFAULT false,
  overall_complexity text CHECK (overall_complexity IN ('HIGH', 'MEDIUM', 'LOW')),
  summary text,
  requires_technical_review boolean NOT NULL DEFAULT false,
  model_used text,
  analyzed_at timestamp with time zone NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  PRIMARY KEY (jurisdiction, section_id),
  FOREIGN KEY (jurisdiction, section_id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE
);

-- Individual Pahlka implementation indicators
CREATE TABLE IF NOT EXISTS pahlka_implementation_indicators (
  id bigserial PRIMARY KEY,
  jurisdiction text NOT NULL,
  section_id text NOT NULL,
  category text NOT NULL CHECK (category IN (
    'complexity_policy_debt',
    'options_become_requirements',
    'policy_implementation_separation',
    'overwrought_legalese',
    'cascade_of_rigidity',
    'mandated_steps_not_outcomes',
    'administrative_burdens',
    'no_feedback_loops',
    'process_worship_oversight',
    'zero_risk_language',
    'frozen_technology',
    'implementation_opportunity'
  )),
  complexity text NOT NULL CHECK (complexity IN ('HIGH', 'MEDIUM', 'LOW')),
  implementation_approach text NOT NULL,
  effort_estimate text,
  explanation text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  FOREIGN KEY (jurisdiction, section_id) REFERENCES section_pahlka_implementations(jurisdiction, section_id) ON DELETE CASCADE
);

-- Matched phrases for Pahlka implementation issues (for UI highlighting)
CREATE TABLE IF NOT EXISTS section_pahlka_highlights (
  id bigserial PRIMARY KEY,
  indicator_id bigint NOT NULL REFERENCES pahlka_implementation_indicators(id) ON DELETE CASCADE,
  phrase text NOT NULL,
  created_at timestamp with time zone DEFAULT now()
);

-- Indexes for Pahlka implementation tables
CREATE INDEX IF NOT EXISTS pahlka_implementations_complexity_idx
  ON section_pahlka_implementations (jurisdiction, overall_complexity)
  WHERE has_implementation_issues = true;

CREATE INDEX IF NOT EXISTS pahlka_implementations_technical_review_idx
  ON section_pahlka_implementations (jurisdiction, requires_technical_review)
  WHERE requires_technical_review = true;

CREATE INDEX IF NOT EXISTS pahlka_indicators_section_idx
  ON pahlka_implementation_indicators (jurisdiction, section_id);

CREATE INDEX IF NOT EXISTS pahlka_indicators_category_idx
  ON pahlka_implementation_indicators (category);

CREATE INDEX IF NOT EXISTS pahlka_indicators_complexity_idx
  ON pahlka_implementation_indicators (complexity);

CREATE INDEX IF NOT EXISTS pahlka_highlights_indicator_idx
  ON section_pahlka_highlights (indicator_id);

--===============================================================================
-- COMMENTS
--===============================================================================

COMMENT ON TABLE section_pahlka_implementations IS
  'Main table for Pahlka implementation analysis results per section';

COMMENT ON TABLE pahlka_implementation_indicators IS
  'Individual implementation issues/patterns found using Pahlka framework';

COMMENT ON TABLE section_pahlka_highlights IS
  'Matched phrases from section text for UI highlighting';

COMMENT ON COLUMN section_pahlka_implementations.has_implementation_issues IS
  'True if section has any implementation complexity or burden issues';

COMMENT ON COLUMN section_pahlka_implementations.overall_complexity IS
  'Highest complexity level among all indicators (null if no issues)';

COMMENT ON COLUMN section_pahlka_implementations.requires_technical_review IS
  'True if section needs technical/architecture review for implementation';

COMMENT ON COLUMN pahlka_implementation_indicators.category IS
  'Category of implementation issue following Pahlka framework from Recoding America';

COMMENT ON COLUMN pahlka_implementation_indicators.implementation_approach IS
  'Suggested approach for implementing section or addressing the issue';

COMMENT ON COLUMN pahlka_implementation_indicators.effort_estimate IS
  'Estimated implementation difficulty or timeline';
