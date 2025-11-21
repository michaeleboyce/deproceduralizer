-- Migration: Add anachronism_indicator to bookmark types
-- Date: 2025-01-20
-- Description: Extends the bookmarks table to support individual anachronism indicator bookmarking

-- Drop the existing constraint
ALTER TABLE bookmarks DROP CONSTRAINT IF EXISTS bookmarks_item_type_check;

-- Add the new constraint with anachronism_indicator included
ALTER TABLE bookmarks ADD CONSTRAINT bookmarks_item_type_check
  CHECK (item_type IN (
    'section',
    'conflict',
    'duplicate',
    'reporting',
    'anachronism',
    'implementation',
    'implementation_indicator',
    'anachronism_indicator'
  ));
