-- Migration: Rename matched_phrase to phrase in section_anachronism_highlights
-- Date: 2025-01-20
-- Description: Standardizes column naming to match section_pahlka_highlights pattern

ALTER TABLE section_anachronism_highlights
RENAME COLUMN matched_phrase TO phrase;
