# Corpus Loading Behavior

## Can I load a different corpus size without cleaning?

**YES!** After the fixes on 2025-11-19, it is safe to load different corpus sizes without cleaning.

## What happens when loading medium corpus after small?

### Data Overwrites (UPSERT behavior)

All loaders use `ON CONFLICT DO UPDATE`, which means:

1. **Sections** (Title 1-2 overlap between small and medium):
   - Existing records → **UPDATED** with fresh data
   - New records (Title 3-10) → **INSERTED**

2. **Structure** (hierarchy nodes):
   - Existing nodes → **UPDATED**
   - New nodes → **INSERTED**

3. **Cross-references**:
   - Existing refs → **UPDATED**
   - New refs → **INSERTED**

4. **Obligations**:
   - Existing obligations → **UPDATED**
   - New obligations → **INSERTED**

5. **Similarities** (section pairs):
   - Existing pairs (e.g., Title 1 ↔ Title 2) → **UPDATED** with recalculated scores
   - New pairs (e.g., Title 1 ↔ Title 3) → **INSERTED**

6. **Reporting Requirements**:
   - Existing records → **UPDATED**
   - New records → **INSERTED**

7. **Classifications**:
   - Existing classifications → **UPDATED**
   - New classifications → **INSERTED**

8. **Anachronisms** (multi-table):
   - Main records → **UPDATED** via `ON CONFLICT DO UPDATE`
   - Indicators → **DELETED then INSERTED** (prevents orphans)
   - Highlights → **DELETED via CASCADE then INSERTED**

### State Files (Resume Points)

Each loader now uses **corpus-specific state files**:

```
Small corpus:  data/outputs/sections_small.state
Medium corpus: data/outputs/sections_medium.state
Large corpus:  data/outputs/sections_large.state
```

This means:
- ✅ State files don't collide between corpus sizes
- ✅ Each corpus tracks its own progress independently
- ✅ Safe to switch between corpus sizes without cleaning

### What Gets Preserved vs Replaced

| Data Type | Overlapping Records | New Records | Deleted Records |
|-----------|---------------------|-------------|-----------------|
| Sections | UPDATED | ADDED | None |
| Structure | UPDATED | ADDED | None |
| Cross-refs | UPDATED | ADDED | None |
| Obligations | UPDATED | ADDED | None |
| Similarities | UPDATED (scores may change) | ADDED (new pairs) | None |
| Reporting | UPDATED | ADDED | None |
| Classifications | UPDATED | ADDED | None |
| Anachronisms | UPDATED | ADDED | Old indicators cleaned up |

### Example Scenario

You have loaded **small corpus** (Titles 1-2, ~100 sections):
- 100 sections
- 50 cross-refs
- 20 similarities (section pairs)

Now you load **medium corpus** (Titles 1-10, ~600 sections) **without cleaning**:

**Result:**
- 600 sections (100 updated, 500 new)
- Cross-refs updated/added (may have FK errors for refs to Titles 11-50)
- Similarities: Original 20 pairs updated if scores changed, plus ~hundreds of new pairs (Title 1-10 combinations)
- All other tables: Updated + new records

**Data Integrity:**
- ✅ No duplicate records (enforced by primary keys + ON CONFLICT)
- ✅ No stale state file issues (corpus-specific state files)
- ✅ No orphaned child records (cascade deletes)
- ⚠️ May have incomplete cross-refs pointing outside corpus (expected behavior)

## When Should You Clean?

You generally **don't need to clean** when switching corpus sizes. However, you may want to clean if:

1. **Starting fresh**: You want to ensure 100% clean slate
2. **Debugging**: Troubleshooting data issues
3. **Disk space**: State files and checkpoints are accumulating
4. **Major schema changes**: After modifying table structures

## How to Clean

```bash
# Clean all checkpoints and state files
./scripts/load-database.sh --corpus=medium  # Will prompt for clean/resume

# Or manually:
rm -rf data/outputs/*.state
rm -rf data/interim/*.state
rm -rf data/interim/*.ckpt
```

## Summary

**After 2025-11-19 fixes:**
- ✅ Safe to load different corpus sizes without cleaning
- ✅ Data will be properly updated/inserted (no duplicates)
- ✅ State files won't interfere (corpus-specific paths)
- ✅ No data corruption or orphaned records
- ⚠️ Cross-refs may have FK errors with subset corpora (expected behavior documented in DATABASE_LOADING_NOTES.md)
