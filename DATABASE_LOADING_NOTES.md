# Database Loading Notes

## Known Issues and Expected Behaviors

### Cross-References with Subset Corpora

#### Issue
When loading a **subset corpus** (small or medium), cross-reference loading will show FK constraint errors:

```
FK constraint error in batch: insert or update on table "section_refs"
violates foreign key constraint "section_refs_jurisdiction_to_id_fkey"
DETAIL: Key (jurisdiction, to_id)=(dc, dc-38-2651) is not present in table "sections".
```

#### Why This Happens
DC Code sections reference other sections throughout the entire code. When you load only a subset:
- Small corpus: ~100 sections from Titles 1-2
- Medium corpus: ~600 sections from Titles 1-10

But those sections contain references to sections in Titles 3-50 that aren't in your subset.

#### Example
Section `dc-1-101` might reference `dc-38-2651` (Title 38), but if you only loaded Titles 1-2, section `dc-38-2651` doesn't exist in your database, causing the FK constraint violation.

#### Solutions

**For Testing/Development:**
1. **Accept the behavior** - Your subset data is still valid, just incomplete cross-refs
2. **Disable FK checks temporarily** (not recommended):
   ```sql
   ALTER TABLE section_refs DROP CONSTRAINT section_refs_jurisdiction_to_id_fkey;
   ```

**For Production:**
1. **Load the full corpus** - Use `--corpus=large` to load all DC Code
2. **Keep only self-contained references** - Filter out external refs during pipeline

#### Impact on Your Data
- ✅ Sections: Fully loaded
- ✅ Structure: Fully loaded
- ✅ Similarities: Fully loaded (only compares sections in corpus)
- ✅ Reporting: Fully loaded
- ✅ Classifications: Fully loaded
- ⚠️ Cross-refs: Only loaded for refs where both sections exist
- ✅ Obligations: Fully loaded
- ✅ Anachronisms: Fully loaded

**Your application will work fine** with incomplete cross-refs - it just means some reference links won't be in the database.

---

## Loader Requirements

All loaders expect the following environment variables:

### Required
- `DATABASE_URL`: PostgreSQL connection string
  ```bash
  export DATABASE_URL="postgresql://user:pass@host:port/dbname"
  ```

### Optional
- `LOADER_BATCH_SIZE`: Batch size for inserts (default: 500)
  ```bash
  export LOADER_BATCH_SIZE=1000
  ```

---

## Loader Status

| Loader | Status | Input File Pattern |
|--------|--------|-------------------|
| Sections | ✅ Working | `sections_{corpus}.ndjson` |
| Structure | ✅ Working | `structure_{corpus}.ndjson` |
| Cross-refs | ✅ Working | `refs_{corpus}.ndjson` |
| Obligations (Enhanced) | ✅ Working | `obligations_enhanced_{corpus}.ndjson` |
| Obligations (Regex) | ✅ Working | `deadlines_{corpus}.ndjson`, `amounts_{corpus}.ndjson` |
| Similarities | ✅ Working | `similarities_{corpus}.ndjson` |
| Reporting | ✅ Working | `reporting_{corpus}.ndjson` |
| Classifications | ✅ Working | `similarity_classifications_{corpus}.ndjson` |
| Anachronisms | ✅ Working | `anachronisms_{corpus}.ndjson` |

---

## Recent Fixes

### 2025-11-19: Anachronisms Schema Mismatch
- **Issue**: Table schema didn't match pipeline data format
  - Table had: `description`, `suggestion`
  - Pipeline produces: `modern_equivalent`, `recommendation`, `explanation`
  - Highlights table had: `matched_phrase` but loader used: `phrase`
  - `executemany()` doesn't support RETURNING clause
- **Fix**:
  - Updated `add_anachronisms_tables.py` to create correct schema
  - Updated `load_anachronisms.py` to use `matched_phrase` column name
  - Replaced `executemany()` with loop using `execute()` for RETURNING support
  - Created `drop_anachronisms_tables.py` to drop old tables
- **Status**: ✅ Fixed and verified working
- **Note**: BaseLoader shows "Inserted: 0" but this is misleading - the custom multi-table loader has its own counters and data loads correctly

### 2025-11-19: Anachronisms Loader Fix
- **Issue**: Missing `database_url` parameter caused `TypeError`
- **Fix**: Added environment variable reading for `DATABASE_URL`
- **Status**: ✅ Fixed

### 2025-11-19: Enhanced Obligations Loader
- **Issue**: Shell script showed "not yet implemented" message
- **Fix**: Wired up existing `load_obligations_enhanced.py` loader
- **Status**: ✅ Fixed

---

## Troubleshooting

### "DATABASE_URL environment variable not set"
**Solution**: Export the variable before running loaders:
```bash
source .env  # If you have DATABASE_URL in .env
# OR
export DATABASE_URL="postgresql://..."
./scripts/load-database.sh --corpus=small
```

### "Input file not found"
**Solution**: Run the pipeline first to generate data files:
```bash
./scripts/run-pipeline.sh --corpus=small
```

### FK Constraint Errors on Cross-refs
**Solution**: This is expected with subset corpora. See "Cross-References with Subset Corpora" above.

### "Telling position disabled by next() call" (Structure)
**Solution**: This is a minor warning and doesn't affect data loading. All structure nodes are still inserted correctly.

---

## Loading Order

The loaders automatically handle dependencies, but the recommended order is:

1. **Sections** (required first - other tables reference this)
2. **Structure** (independent)
3. **Cross-refs** (references sections)
4. **Obligations** (references sections)
5. **Similarities** (references sections)
6. **Reporting** (updates sections)
7. **Classifications** (references similarities)
8. **Anachronisms** (references sections)

The `load-database.sh` script loads in this order automatically.
