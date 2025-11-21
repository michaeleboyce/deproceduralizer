-- Migration: Add Implementation Indicator Bookmark Type
-- Date: 2025-11-20
-- Description: Adds 'implementation_indicator' as a valid bookmark item type for individual Pahlka implementation indicators

--===============================================================================
-- UPDATE BOOKMARKS TABLE CONSTRAINT
--===============================================================================

-- Drop existing constraint
ALTER TABLE bookmarks DROP CONSTRAINT IF EXISTS bookmarks_item_type_check;

-- Add updated constraint with new type
ALTER TABLE bookmarks ADD CONSTRAINT bookmarks_item_type_check
  CHECK (item_type IN (
    'section',
    'conflict',
    'duplicate',
    'reporting',
    'anachronism',
    'implementation',
    'implementation_indicator'
  ));

--===============================================================================
-- COMMENTS
--===============================================================================

COMMENT ON CONSTRAINT bookmarks_item_type_check ON bookmarks IS
  'Valid bookmark types: section, conflict, duplicate, reporting, anachronism, implementation (section-level), implementation_indicator (individual indicator)';
