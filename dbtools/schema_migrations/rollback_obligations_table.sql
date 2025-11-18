-- Rollback: Remove obligations table
-- Purpose: Revert the add_obligations_table migration
-- Created: 2025-11-18

BEGIN;

-- Drop indexes first
DROP INDEX IF EXISTS idx_obligations_value;
DROP INDEX IF EXISTS idx_obligations_category;
DROP INDEX IF EXISTS idx_obligations_section;
DROP INDEX IF EXISTS idx_obligations_jurisdiction;

-- Drop the table
DROP TABLE IF EXISTS obligations;

COMMIT;
