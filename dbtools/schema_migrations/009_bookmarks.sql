-- Migration: Add Bookmarks Table
-- Date: 2025-11-20
-- Description: Creates shared bookmarks table for sections, conflicts, and analysis items

--===============================================================================
-- BOOKMARKS TABLE
--===============================================================================

-- Shared bookmarks table (no user authentication required)
-- Everyone can see and manage all bookmarks
CREATE TABLE IF NOT EXISTS bookmarks (
  id bigserial PRIMARY KEY,
  jurisdiction varchar(10) NOT NULL DEFAULT 'dc',

  -- Item reference
  item_type text NOT NULL CHECK (item_type IN (
    'section',
    'conflict',
    'duplicate',
    'reporting',
    'anachronism',
    'implementation'
  )),
  item_id text NOT NULL,

  -- Optional note
  note text,

  -- Metadata
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,

  -- Ensure no duplicate bookmarks
  UNIQUE (jurisdiction, item_type, item_id)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_bookmarks_jurisdiction
  ON bookmarks(jurisdiction);

CREATE INDEX IF NOT EXISTS idx_bookmarks_item_type
  ON bookmarks(item_type);

CREATE INDEX IF NOT EXISTS idx_bookmarks_created_at
  ON bookmarks(created_at DESC);

--===============================================================================
-- COMMENTS
--===============================================================================

COMMENT ON TABLE bookmarks IS
  'Shared bookmarks for sections, conflicts, and analysis items. No user auth - everyone sees same bookmarks.';

COMMENT ON COLUMN bookmarks.item_type IS
  'Type of bookmarked item: section, conflict, duplicate, reporting, anachronism, implementation';

COMMENT ON COLUMN bookmarks.item_id IS
  'Section ID or composite ID (e.g., sectionA:sectionB for conflicts/duplicates)';

COMMENT ON COLUMN bookmarks.note IS
  'Optional note about why this item was bookmarked';
