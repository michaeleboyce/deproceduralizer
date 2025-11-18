# Deproceduralizer Development TODO

Track development progress across all three parallel tracks (A: Pipeline, B: Database, C: Web). Update this file as tasks are completed.

**Legend**:
- [ ] Not started
- [~] In progress
- [x] Completed
- **BLOCKS** - This task blocks another task
- **REQUIRES** - This task requires another task to be completed first

---

## 🎯 Strategic Pivot: Deepen Before Widening

**Status**: Active - This is a pivotal moment for the project

### Context

You have a working "vertical slice" (Titles 1-2, ~100 sections) with all features implemented. However, before scaling to the "horizontal" (full corpus of 50 titles), we must address architectural debt and functional fragility. Running the full pipeline now would generate large volumes of low-quality data that is hard to query and hard to update.

### Strategy: Build Multi-Jurisdiction Foundation Now

This project will expand beyond DC to support California, New York, and other legal codes. We will build jurisdiction-agnostic architecture from the start to avoid a painful refactor later.

**Key Principles:**
1. **DRY (Don't Repeat Yourself)**: Eliminate code duplication in loaders and parsers
2. **Structured Data**: Replace brittle regex JSON parsing with validated Pydantic models
3. **Hierarchical Integrity**: Represent law as a tree, not a flat list
4. **Professional UX**: Build a legal intelligence platform, not just a search tool
5. **Multi-Jurisdiction**: Design schema and pipeline for DC, CA, NY, etc. from day one

### Three Strategic Tracks

**Track A: Architecture & Data Engineering**
- Create `BaseLoader` abstract class (DRY principle)
- Implement two-pass XML parsing (structure → content)
- Add multi-jurisdiction support to all tables (jurisdiction column + composite PKs)
- Replace regex JSON parsing with Pydantic + Instructor

**Track B: Advanced Intelligence**
- Replace regex obligations with LLM-based classification
- Optimize similarity search with FAISS IVF indexing (100x speedup)
- Add jurisdiction-aware loaders

**Track C: "BCG-Level" UX Polish**
- In-text citation hyperlinking
- Citation graph visualization
- Legislative conflict dashboard
- Hover cards for previews
- Professional typography and layout

### Execution Plan

- **Milestones 0-5**: ✅ Complete (vertical slice working)
- **Milestones 5.1-5.3**: 🏗️ Refinement phase (NEW - do these next)
- **Milestones 6-8**: ⏸️ PAUSED until refinement complete

After refinement, we will process DC's full corpus (Milestone 6), then easily expand to California, New York, and other jurisdictions without refactoring.

### Milestone Dependency Graph

```
Milestones 0-5: ✅ Complete
    |
    v
Milestone 5.1: Architecture Hardening (DRY, Multi-Jurisdiction, Hierarchy)
    |
    v
Milestone 5.2: Enhanced Intelligence (Pydantic/Instructor, IVF, Enhanced Obligations)
    |    \
    |     \------- (Milestone 5.5 can run in parallel with 5.3)
    |              (Applies 5.2's improvements)
    v
Milestone 5.3: "BCG-Level" UX (shadcn/ui, Citations, Graphs, Dashboards)
    |
    v
Milestone 5.5: Similarity Classification (If not done in parallel)
    |
    v
Milestone 6: Medium Corpus (Titles 1-10, ~500-600 sections)
    |
    v
Milestone 7: Reporting Deep Analysis (Enhanced metadata, frequency, entities)
    |
    v
Milestone 8: Full DC Code Corpus (~50 titles) + Deploy to Production
    |
    v
Milestone 9: (Future) Add California, New York, other jurisdictions
```

**Key Dependencies:**
- **5.1 BLOCKS 5.2**: Pydantic models (5.1) needed before instructor refactor (5.2)
- **5.1 BLOCKS 5.3**: Multi-jurisdiction schema (5.1) needed before UI updates (5.3)
- **5.2 BLOCKS 5.5**: Structured LLM patterns (5.2) should be applied to similarity classification (5.5)
- **5.1 + 5.2 + 5.3 + 5.5 BLOCK 6**: Refinement must be complete before scaling to medium corpus
- **6 BLOCKS 7**: Medium corpus provides realistic data for reporting deep analysis
- **7 BLOCKS 8**: Reporting enhancements should be tested before full corpus

**Parallelization Opportunities:**
- Milestone 5.5 can run in parallel with 5.3 if resources allow (both are Track C heavy)
- Within milestones, Track A/B/C tasks can often run in parallel (see individual BLOCKS/REQUIRES)

---

## 🧱 Milestone 0: Environment Ready

**Goal**: Everything installed; DB + app skeletons exist
**Status**: ✅ Complete

### Track A: Pipeline Foundation

- [x] **A0.1** Create Python venv → `python3 -m venv .venv`
- [x] **A0.2** Create `pipeline/requirements.txt` (BLOCKS: A0.3)
- [x] **A0.3** Install pipeline requirements (REQUIRES: A0.2, BLOCKS: A1.1)
  ```bash
  source .venv/bin/activate
  pip install -r pipeline/requirements.txt
  ```
- [x] **A0.4** Clone DC XML repo (BLOCKS: A1.1)
  ```bash
  git clone https://github.com/DCCouncil/law-xml.git data/raw/dc-law-xml
  ```
- [x] **A0.5** Verify Ollama running (BLOCKS: A4.1, A5.1)
  ```bash
  ollama list  # Should show nomic-embed-text and phi3.5
  ```
- [x] **A0.6** Create `pipeline/common.py` skeleton

**Acceptance**: ✅ **COMPLETE** - Python environment ready, DC XML cloned, Ollama verified

---

### Track B: Database Setup

- [x] **B0.1** Create Neon project
- [x] **B0.2** Add DATABASE_URL to `.env`
- [x] **B0.3** Create `dbtools/create_tables.sql` with full schema (BLOCKS: B0.4)
- [x] **B0.4** Run `create_tables.sql` against Neon (REQUIRES: B0.3, BLOCKS: B1.1, C0.3)
  ```bash
  psql $DATABASE_URL -f dbtools/create_tables.sql
  ```
- [x] **B0.5** Create `dbtools/load_sections.py` skeleton (BLOCKS: B1.1)
- [x] **B0.6** Verify database connection works
  ```bash
  psql $DATABASE_URL -c "SELECT version();"
  ```

**Acceptance**: ✅ Database tables exist, loaders have skeletons

---

### Track C: Web App Foundation

- [x] **C0.1** Initialize Next.js app (BLOCKS: C0.2, C0.3)
  ```bash
  npx create-next-app@latest apps/web --typescript --tailwind --app --no-src-dir --import-alias "@/*" --eslint --no-turbopack
  ```
- [x] **C0.2** Install Drizzle + Neon deps (REQUIRES: C0.1)
  ```bash
  cd apps/web
  npm add drizzle-orm @neondatabase/serverless
  npm add -D drizzle-kit
  ```
- [x] **C0.3** Create `apps/web/db/schema.ts` (REQUIRES: B0.4)
- [x] **C0.4** Create `apps/web/lib/db.ts` connection (REQUIRES: C0.3)
- [x] **C0.5** Copy DATABASE_URL to `apps/web/.env.local`
- [x] **C0.6** Verify `npm run dev` works
  ```bash
  cd apps/web && npm run dev
  # Visit http://localhost:3000
  ```

**Acceptance**: ✅ Next.js app running, Drizzle connected to Neon

---

### Cross-Track Dependencies

- **B0.4** (database created) UNBLOCKS **C0.3** (can write schema.ts)
- **A0.6** (common.py) UNBLOCKS **A1.1** (parse XML script)

---

## 🧪 Milestone 1: Minimal Subset Searchable

**Goal**: Small subset (Titles 1-2) parsed, loaded, and searchable via keyword FTS
**Status**: ✅ Complete

### Track A: Parse Subset

- [x] **A1.1** Write `scripts/make_subset.sh` (REQUIRES: A0.4)
  - Copies 1-2 XML title files from `data/raw/dc-law-xml/` to `data/subsets/`
- [x] **A1.2** Implement `pipeline/10_parse_xml.py` (REQUIRES: A0.3, A0.6, BLOCKS: B1.1)
  - Parse XML sections using ElementTree or lxml
  - Extract id, citation, heading, text_plain, text_html, ancestors, title_label, chapter_label
  - Write to `data/outputs/sections_subset.ndjson`
  - Use tqdm for progress
  - Implement checkpoint/resume with `.state` file
  - Support `--src`, `--out`, `--limit` flags
- [x] **A1.3** Run parser on subset
  ```bash
  python pipeline/10_parse_xml.py --src data/subsets --out data/outputs/sections_subset.ndjson
  ```
- [x] **A1.4** Validate output has >100 sections
  ```bash
  wc -l data/outputs/sections_subset.ndjson
  ```

**Acceptance**: ✅ **COMPLETE** - `sections_subset.ndjson` exists with 100 lines, valid JSON, all fields present

---

### Track B: Load Subset

- [x] **B1.1** Implement `dbtools/load_sections.py` (REQUIRES: A1.2, B0.5)
  - Read NDJSON line-by-line
  - Batch inserts (500 rows per batch)
  - Use `INSERT ... ON CONFLICT (id) DO UPDATE`
  - Maintain `.state` file with last byte offset for resume
  - Progress bar with count of inserted/updated rows
  - Support `--input` flag
- [x] **B1.2** Run loader on subset
  ```bash
  python dbtools/load_sections.py --input data/outputs/sections_subset.ndjson
  ```
- [x] **B1.3** Verify data loaded (REQUIRES: B1.2)
  ```bash
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM dc_sections;"
  # Should be >100
  ```

**Acceptance**: ✅ `SELECT COUNT(*) FROM dc_sections;` returns 100

---

### Track C: Basic Search UI

- [x] **C1.1** Create `apps/web/app/api/search/route.ts` (REQUIRES: B1.3)
  - Accept GET with `?query=term`
  - Use Postgres FTS: `WHERE text_fts @@ plainto_tsquery('english', $query)`
  - Return JSON array of sections (id, citation, heading, snippet)
  - Limit 20 results
- [x] **C1.2** Create `apps/web/app/search/page.tsx`
  - Search input field
  - Call `/api/search` on submit
  - Display results list (citation, heading, text preview)
  - Link to `/section/[id]`
- [x] **C1.3** Test search for "notice" or "board"
  ```bash
  cd apps/web && pnpm dev
  # Visit http://localhost:3000/search
  # Type "notice" and verify results appear
  ```

**Acceptance**: ✅ **COMPLETE** - Visiting `/search`, typing "notice" or "board" returns results from DB

---

### Cross-Track Dependencies

- **A1.2** (parse XML) UNBLOCKS **B1.1** (load sections)
- **B1.2** (data loaded) UNBLOCKS **C1.1** (search API has data to query)

---

## 🔎 Milestone 2: Enhanced Search & Filters

**Goal**: Add title/chapter filters, FTS improvements
**Status**: ✅ Complete

### Track A: No Changes

- [ ] **A2.1** (No new pipeline work needed - still using subset)

---

### Track B: Ensure Indexing

- [x] **B2.1** Verify FTS column exists (should be automatic from schema)
  ```sql
  SELECT column_name FROM information_schema.columns
  WHERE table_name = 'dc_sections' AND column_name = 'text_fts';
  ```
- [x] **B2.2** Verify FTS index exists
  ```sql
  SELECT indexname FROM pg_indexes WHERE tablename = 'dc_sections';
  ```
- [x] **B2.3** Ensure `title_label` and `chapter_label` populated (check load_sections.py)

**Acceptance**: ✅ FTS index exists (dc_sections_text_fts_idx + 4 other indexes), all 100 sections have title/chapter labels populated (2 titles, 1 chapter)

---

### Track C: Enhanced Search

- [x] **C2.1** Update `/api/search` route (REQUIRES: B2.3)
  - Accept `query`, `title`, `chapter` params *(hasReporting/hasDeadline deferred to Milestone 5)*
  - Build dynamic WHERE clause with filters
  - Add pagination support (offset/limit)
- [x] **C2.2** Update `/search` page UI
  - Add dropdown for `title` (populate from DB distinct values)
  - Add dropdown for `chapter` (filtered by selected title)
  - Add pagination controls
  - *(Checkboxes for reporting/deadlines deferred to Milestone 5 when data is available)*
- [x] **C2.3** Test filtering by Title 1
  ```bash
  # Tested via API: Title 1 returns 50 results, Title 2 returns 50 results
  # Combined filters work: query="board" + title="Title 1" returns 29 results
  # Pagination works: Page 1 shows 20 results, Page 2 shows 9 results
  ```

**Acceptance**: ✅ **COMPLETE** - Can filter by title/chapter, pagination works, result counts change correctly

---

## 🧷 Milestone 3: Cross-References & Obligations

**Goal**: Extract and display cross-refs, deadlines, and dollar amounts
**Status**: ✅ Complete

### Track A: Extract Cross-Refs & Obligations

- [x] **A3.1** Implement `pipeline/20_crossrefs.py` (REQUIRES: A1.2, BLOCKS: B3.1)
  - Read `sections_subset.ndjson`
  - Regex to find citations: `§ \d+-\d+`, `section \d+-\d+`, etc.
  - Resolve citations to section IDs
  - Write `refs_subset.ndjson` (from_id, to_id, raw_cite)
  - Support `--in`, `--out` flags
  - tqdm + .state for resume
- [x] **A3.2** Run crossrefs extraction
  ```bash
  python pipeline/20_crossrefs.py --in data/outputs/sections_subset.ndjson --out data/outputs/refs_subset.ndjson
  ```
- [x] **A3.3** Implement `pipeline/30_regex_obligations.py` (REQUIRES: A1.2, BLOCKS: B3.2)
  - Read `sections_subset.ndjson`
  - Regex for deadlines: "within X days", "X-day notice", etc.
  - Regex for amounts: "$X", "$X,XXX", etc.
  - Write `deadlines_subset.ndjson` and `amounts_subset.ndjson`
  - Support `--in`, `--deadlines`, `--amounts` flags
  - tqdm + .state for resume
- [x] **A3.4** Run obligations extraction
  ```bash
  python pipeline/30_regex_obligations.py \
    --in data/outputs/sections_subset.ndjson \
    --deadlines data/outputs/deadlines_subset.ndjson \
    --amounts data/outputs/amounts_subset.ndjson
  ```

**Acceptance**: ✅ **COMPLETE** - 102 cross-refs, 56 deadlines, 33 amounts extracted

---

### Track B: Load Cross-Refs & Obligations

- [x] **B3.1** Implement `dbtools/load_refs.py` (REQUIRES: A3.2)
  - Read `refs_subset.ndjson`
  - Batch insert to `dc_section_refs`
  - ON CONFLICT DO NOTHING (primary key on from_id, to_id, raw_cite)
  - .state for resume
- [x] **B3.2** Implement `dbtools/load_deadlines_amounts.py` (REQUIRES: A3.4)
  - Read both `deadlines_subset.ndjson` and `amounts_subset.ndjson`
  - Insert to `dc_section_deadlines` and `dc_section_amounts`
  - .state for resume
- [x] **B3.3** Run loaders
  ```bash
  python dbtools/load_refs.py --input data/outputs/refs_subset.ndjson
  python dbtools/load_deadlines_amounts.py \
    --deadlines data/outputs/deadlines_subset.ndjson \
    --amounts data/outputs/amounts_subset.ndjson
  ```
- [x] **B3.4** Verify data loaded
  ```bash
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM dc_section_refs;"
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM dc_section_deadlines;"
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM dc_section_amounts;"
  ```

**Acceptance**: ✅ **COMPLETE** - 0 cross-refs (FK constraints - refs outside subset), 56 deadlines, 33 amounts loaded successfully

---

### Track C: Section Detail Page

- [x] **C3.1** Create `apps/web/app/section/[id]/page.tsx` (REQUIRES: B3.4)
  - Fetch section by ID
  - Display: citation, heading, breadcrumbs (title/chapter), text_html
  - Query `dc_section_refs` where `from_id = id` (references)
  - Query `dc_section_refs` where `to_id = id` (referenced by)
  - Query `dc_section_deadlines` where `section_id = id`
  - Query `dc_section_amounts` where `section_id = id`
  - Display in sections: References, Referenced By, Deadlines, Dollar Amounts
- [x] **C3.2** Test section detail page
  - Verified section detail page renders correctly
  - Confirmed deadlines display (56 total across sections)
  - Confirmed dollar amounts display (33 total across sections)
  - Confirmed cross-references structure (0 in subset due to FK constraints)

**Acceptance**: ✅ **COMPLETE** - Section detail page with cross-refs and obligations fully implemented and tested

---

## 🧬 Milestone 4: Similar Sections (Semantic)

**Goal**: Compute embeddings offline, find similar sections, display in UI
**Status**: ✅ Complete

### Track A: Compute Similarities

- [x] **A4.1** Implement `pipeline/40_similarities.py` (REQUIRES: A0.5, A1.2, BLOCKS: B4.1)
  - Read `sections_subset.ndjson`
  - For each section, call Ollama embeddings API:
    ```python
    import requests
    resp = requests.post("http://localhost:11434/api/embeddings",
                        json={"model": "nomic-embed-text", "prompt": text_plain})
    embedding = resp.json()["embedding"]
    ```
  - Normalize vectors (L2 norm)
  - Use FAISS IndexFlatIP to compute top-k neighbors (k=10)
  - Only write pairs with similarity > 0.7
  - Write `similarities_subset.ndjson` (section_a, section_b, similarity)
  - Ensure section_a < section_b (alphabetically) to avoid duplicates
  - tqdm + .ckpt for resume (since embeddings are slow)
  - Support `--in`, `--out`, `--top-k`, `--min-similarity` flags
- [x] **A4.2** Run similarities extraction
  ```bash
  python pipeline/40_similarities.py \
    --in data/outputs/sections_subset.ndjson \
    --out data/outputs/similarities_subset.ndjson \
    --top-k 10 \
    --min-similarity 0.7
  ```
- [x] **A4.3** Verify output shape
  ```bash
  wc -l data/outputs/similarities_subset.ndjson
  # Should have hundreds of pairs
  ```

**Acceptance**: ✅ **COMPLETE** - 254 similarity pairs, scores 0.70-1.00, mean 0.767

---

### Track B: Load Similarities

- [x] **B4.1** Implement `dbtools/load_similarities.py` (REQUIRES: A4.2)
  - Read `similarities_subset.ndjson`
  - Batch insert to `dc_section_similarities`
  - ON CONFLICT (section_a, section_b) DO UPDATE SET similarity = ...
  - .state for resume
- [x] **B4.2** Run loader
  ```bash
  python dbtools/load_similarities.py --input data/outputs/similarities_subset.ndjson
  ```
- [x] **B4.3** Verify data loaded
  ```bash
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM dc_section_similarities;"
  ```

**Acceptance**: ✅ **COMPLETE** - 254 similarity pairs loaded, range 0.70-1.00, mean 0.767, queries working

---

### Track C: Similar Sections UI

- [x] **C4.1** Update `/section/[id]` page (REQUIRES: B4.2)
  - Query similar sections in both directions (section_a and section_b)
  - Join with dc_sections to get citation, heading
  - Display "Similar Sections" list with similarity scores
  - Show top 5 similar sections sorted by similarity
- [x] **C4.2** Add diff modal/view (REQUIRES: C4.1)
  - Installed `diff-match-patch` library and types
  - Created `SectionDiffModal.tsx` component
  - Created `SimilarSectionsList.tsx` client component
  - Created `/api/section/[id]` route to fetch individual sections
  - Implemented side-by-side diff view with color-coded changes
  - Added "Compare" button for each similar section
- [x] **C4.3** Test similarity display
  - Verified similar sections query returns correct data (254 pairs, 0.70-1.00 similarity range)
  - Confirmed UI components integrate properly
  - Tested with sections that have high similarity (e.g., dc-1-1061-08 and dc-1-1061-12 at 100% match)

**Acceptance**: ✅ **COMPLETE** - Similar sections displayed with interactive diff modal view

---

## 🧾 Milestone 5: Reporting Detection (LLM)

**Goal**: Use phi3.5 to detect reporting requirements and highlight them
**Status**: ✅ Complete

### Track A: LLM Reporting Detection

- [x] **A5.1** Implement `pipeline/50_llm_reporting.py` (REQUIRES: A0.5, A1.2, BLOCKS: B5.1)
  - Read `sections_subset.ndjson`
  - For each section, call Ollama generate API with phi3.5:
    ```python
    prompt = f"""
    Analyze this DC Code section for reporting requirements.
    Return JSON ONLY with these fields:
    - has_reporting_requirement: true/false
    - reporting_summary: short 1-2 sentence description or ""
    - tags: array of tags like ["reporting", "mayor", "annual"]
    - highlight_phrases: array of exact phrases from text

    SECTION TEXT:
    {text_plain}
    """
    resp = requests.post("http://localhost:11434/api/generate",
                        json={"model": "phi3.5", "prompt": prompt, "stream": False})
    result = parse_json_from_response(resp.json()["response"])
    ```
  - Write `reporting_subset.ndjson` (id, has_reporting, reporting_summary, tags, highlight_phrases)
  - tqdm + .ckpt for resume
  - Support `--in`, `--out` flags
- [x] **A5.2** Run reporting detection
  - Reporting pipeline executed successfully
  - Generated reporting data for 98 sections
  - 45 sections identified with reporting requirements

**Acceptance**: ✅ **COMPLETE** - Reporting data generated and processed

---

### Track B: Load Reporting Data

- [x] **B5.1** Implement `dbtools/load_reporting.py` (REQUIRES: A5.2)
  - Read `reporting_subset.ndjson`
  - UPDATE `dc_sections` SET has_reporting, reporting_summary, reporting_tags
  - INSERT tags into `dc_global_tags` (ON CONFLICT DO NOTHING)
  - INSERT section-tag pairs into `dc_section_tags`
  - Store `highlight_phrases` in new table `dc_section_highlights(section_id, phrase)` if needed
  - .state for resume
- [x] **B5.2** Add highlights table if needed
  ```sql
  CREATE TABLE IF NOT EXISTS dc_section_highlights (
    id bigserial PRIMARY KEY,
    section_id text REFERENCES dc_sections(id),
    phrase text NOT NULL
  );
  ```
- [x] **B5.3** Run loader
  ```bash
  python dbtools/load_reporting.py --input data/outputs/reporting_subset.ndjson
  ```

**Acceptance**: ✅ **COMPLETE** - 98 sections processed, 45 with reporting requirements, 74 unique tags, 120 section-tag pairs, 84 highlight phrases

---

### Track C: Reporting UI

- [x] **C5.1** Update `/api/search` to support `hasReporting` filter (REQUIRES: B5.3)
  - Added `hasReporting` query parameter to search API
  - Implemented `WHERE has_reporting = true` filter
  - Returns filter status in response
- [x] **C5.2** Update `/search` page
  - Added "Has reporting requirement" checkbox to filters
  - Integrated with URL parameters and search state
  - Added purple badge to active filters display
  - Checkbox resets with "Clear" button
- [x] **C5.3** Update `/section/[id]` page (REQUIRES: B5.3)
  - Created `apps/web/lib/highlight.ts` utility for phrase highlighting
  - Added queries for `dc_section_highlights` and `dc_section_tags`
  - Display reporting badge when `has_reporting = true`
  - Show `reporting_summary` with purple theme
  - Display tags as small badges
  - Highlighted phrases in section text using yellow `<mark>` tags
- [x] **C5.4** Test reporting highlights
  - Verified 45 sections with reporting requirements in database
  - Confirmed highlight phrases (84 total) and tags (74 unique) loaded
  - Tested reporting badge, summary, and tag display
  - Verified phrase highlighting functionality
- [x] **C5.5** Improve overall look/feel/navigation with modern design system
  - Created comprehensive STYLE_GUIDE.md with color palette and design tokens ✅
  - Implemented sophisticated slate/teal color palette (replaced all blue/indigo colors) ✅
  - Added navigation header component with breadcrumbs across all pages ✅
  - Enhanced typography hierarchy with system font stack in globals.css ✅
  - Created tailwind.config.ts with design tokens and theme configuration ✅
  - Updated search page with cleaner filters and consistent colors ✅
  - Updated section detail page with improved hierarchy and sky colors for references ✅
  - Updated reporting page with consistent color palette ✅

**Acceptance**: ✅ **COMPLETE** - Full reporting UI with filters, badges, summaries, tags, and highlighted phrases

---

## 🏗️ Milestone 5.1: Architecture Hardening

**Goal**: DRY principles, multi-jurisdiction support, hierarchical integrity
**Status**: 🟡 In Progress (Track B: ✅ Complete, Track A: ⚪ Not Started, Track C: 🟢 Mostly Complete)

**Rationale**: Before scaling to medium/full corpus, eliminate technical debt. Build jurisdiction-agnostic foundation to support DC, California, New York, and other legal codes without refactoring.

### Track A: Pipeline Refactoring

- [ ] **A5.1.1** Create `pipeline/models.py` with jurisdiction-agnostic Pydantic models (BLOCKS: A5.2.3)
  - Define `Section`, `CrossReference`, `Obligation`, `SimilarityPair`, `ReportingRequirement`
  - Use Field validators and aliases for data contract compatibility
  - Support multi-jurisdiction with `jurisdiction` field
- [ ] **A5.1.2** Create `pipeline/parsers/` module structure (BLOCKS: A5.1.4)
  - Create `parsers/__init__.py`
  - Create `parsers/base.py` with abstract `BaseParser` class
  - Create `parsers/dc.py` extending `BaseParser` for DC Code XML format
  - Add `--jurisdiction` flag to all pipeline scripts
- [ ] **A5.1.3** Implement two-pass XML parsing in `10_parse_xml.py` (REQUIRES: A5.1.2)
  - **Pass 1**: Parse `index.xml` files to extract hierarchical structure
  - **Pass 2**: Parse section XMLs and attach to hierarchy
  - Output includes correct parent/child relationships
- [ ] **A5.1.4** Add `<history>` effective date extraction (REQUIRES: A5.1.3)
  - Parse `<history>` tags in XML for effective dates
  - Add `effective_date` field to sections.ndjson output
  - Update CONTRACTS.md with new field

**Acceptance**: ✅ Jurisdiction-agnostic Pydantic models exist, two-pass parsing works, effective dates extracted

---

### Track B: Multi-Jurisdiction Schema

- [x] **B5.1.1** Create `dbtools/schema_migrations/add_multi_jurisdiction.sql` (BLOCKS: B5.1.5)
  - Create `jurisdictions` table (id, name, abbreviation, type, parser_version)
  - Rename all `dc_*` tables to remove `dc_` prefix:
    - `dc_sections` → `sections`
    - `dc_section_refs` → `section_refs`
    - `dc_section_deadlines` → `section_deadlines`
    - `dc_section_amounts` → `section_amounts`
    - `dc_section_similarities` → `section_similarities`
    - `dc_section_similarity_classifications` → `section_similarity_classifications`
    - `dc_global_tags` → `global_tags`
    - `dc_section_tags` → `section_tags`
    - `dc_section_highlights` → `section_highlights`
    - `dc_reporting_entities` → `reporting_entities`
    - `dc_reporting_related` → `reporting_related`
  - Add `jurisdiction` VARCHAR(10) column to all tables
  - Update primary keys to be composite: (jurisdiction, id)
  - Update all foreign keys to include jurisdiction
  - Create indexes on jurisdiction column
- [x] **B5.1.2** Create `structure` table for hierarchical law representation (REQUIRES: B5.1.1)
  ```sql
  CREATE TABLE structure (
    jurisdiction VARCHAR(10) NOT NULL,
    id TEXT NOT NULL,
    parent_id TEXT,
    level TEXT, -- 'title', 'subtitle', 'chapter', 'subchapter', etc.
    label TEXT,
    heading TEXT,
    ordinal INTEGER,
    PRIMARY KEY (jurisdiction, id),
    FOREIGN KEY (jurisdiction, parent_id) REFERENCES structure(jurisdiction, id)
  );
  ```
- [x] **B5.1.3** Create `dbtools/common/base_loader.py` with abstract `BaseLoader` (BLOCKS: B5.1.4)
  - Abstract class with `abc` module
  - Common logic: progress bars (tqdm), state files, DB connection pooling
  - Abstract methods: `process_batch()`, `validate_record()`
  - Implements checkpoint save/resume automatically
  - Logging utilities
- [x] **B5.1.4** Refactor all loaders to inherit from `BaseLoader` (REQUIRES: B5.1.3)
  - Update `dbtools/load_sections.py`
  - Update `dbtools/load_refs.py`
  - Update `dbtools/load_deadlines_amounts.py`
  - Update `dbtools/load_similarities.py`
  - Update `dbtools/load_similarity_classifications.py`
  - Update `dbtools/load_reporting.py`
  - Remove duplicated code (~200+ lines eliminated)
- [x] **B5.1.5** Run schema migration against Neon DB (REQUIRES: B5.1.1)
  ```bash
  psql $DATABASE_URL -f dbtools/schema_migrations/add_multi_jurisdiction.sql
  ```
- [x] **B5.1.6** Insert 'dc' jurisdiction into `jurisdictions` table
  ```sql
  INSERT INTO jurisdictions (id, name, abbreviation, type, parser_version)
  VALUES ('dc', 'District of Columbia Code', 'DC', 'district', '0.2.0');
  ```
- [x] **B5.1.7** Verify schema migration successful (REQUIRES: B5.1.5, B5.1.6)
  ```bash
  psql $DATABASE_URL -c "\dt"  # Should show renamed tables
  psql $DATABASE_URL -c "SELECT * FROM jurisdictions;"  # Should show DC
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM sections WHERE jurisdiction = 'dc';"  # Should match old count
  ```

**Acceptance**: ✅ Multi-jurisdiction schema live, all tables renamed, DC data migrated, BaseLoader implemented

---

### Track C: UI Updates for Multi-Jurisdiction

- [x] **C5.1.1** Update `apps/web/db/schema.ts` to match new DB schema (REQUIRES: B5.1.5)
  - Renamed all `dc*` table definitions → `sections`, `sectionRefs`, etc.
  - Added `jurisdiction` varchar(10) column to all tables
  - Updated to composite primary keys with jurisdiction
  - Added `jurisdictions` and `structure` table definitions
- [x] **C5.1.2** Update all database queries to include jurisdiction filter
  - Updated 5 API routes: search, reporting, section detail, filters (titles/chapters)
  - Updated section detail page with 10+ queries
  - All queries filter by `jurisdiction = 'dc'` (hardcoded, transparent to users)
  - Updated all JOIN conditions to include jurisdiction matching
- [ ] **C5.1.3** Add jurisdiction selector to navigation (currently DC only)
  - Add dropdown in Navigation component
  - Store selected jurisdiction in URL params or context
  - Filter all queries by selected jurisdiction
- [ ] **C5.1.4** Update `apps/web/lib/db.ts` connection utilities
  - Ensure queries use jurisdiction parameter
  - Add helper functions: `getCurrentJurisdiction()`, `getJurisdictions()`
- [ ] **C5.1.5** Test "Browse by Chapter" navigation with new structure table (REQUIRES: B5.1.2)
  - Query `structure` table for hierarchical navigation
  - Render collapsible tree (Title → Chapter → Section)
  - Verify breadcrumbs work correctly

**Acceptance**: ✅ UI works with multi-jurisdiction schema, jurisdiction selector present (DC only initially), structure-based navigation

---

## 🧠 Milestone 5.2: Enhanced Intelligence

**Goal**: Replace brittle regex parsing with validated structured outputs, optimize similarity search
**Status**: ⚪ Not Started

**Rationale**: Current LLM scripts use 200+ lines of fragile regex-based JSON parsing with manual field validation. Replace with Pydantic + Instructor for automatic validation, retry logic, and type safety. Optimize similarity search for full corpus scale.

### Track A: LLM Hardening with Structured Outputs

- [ ] **A5.2.1** Install `instructor` library (BLOCKS: A5.2.2)
  ```bash
  source .venv/bin/activate
  pip install instructor
  pip freeze > pipeline/requirements.txt
  ```
- [ ] **A5.2.2** Create `pipeline/llm_client.py` unified LLM wrapper (REQUIRES: A5.2.1, BLOCKS: A5.2.3)
  - Wrap Gemini API with instructor
  - Wrap Ollama API with instructor
  - Integrate existing RateLimiter cascade logic (Gemini → Ollama fallback)
  - Support `response_model` parameter for Pydantic validation
  - Return validated model instances (not raw JSON strings)
  - Handle rate limits and model fallback gracefully
  - Logging for which model was used per request
- [ ] **A5.2.3** Refactor `50_llm_reporting.py` to use structured outputs (REQUIRES: A5.1.1, A5.2.2)
  - Import `ReportingRequirement` model from `pipeline/models.py`
  - Replace `parse_llm_json()` function (40+ lines) with instructor calls
  - Remove manual field validation loops (20+ lines)
  - Use llm_client wrapper with `response_model=ReportingRequirement`
  - Keep checkpoint/resume logic intact
  - Maintain CONTRACTS.md output schema compatibility
  - Test on subset data to verify parity with old approach
- [ ] **A5.2.4** Refactor `55_similarity_classification.py` to use structured outputs (REQUIRES: A5.1.1, A5.2.2)
  - Import `SimilarityClassification` model from `pipeline/models.py`
  - Replace duplicate `parse_llm_json()` (40+ lines)
  - Remove duplicate RateLimiter class (consolidate to llm_client.py)
  - Remove manual field validation
  - Maintain output schema compatibility
  - Test on subset similarity pairs
- [ ] **A5.2.5** Update CONTRACTS.md to reference Pydantic models (REQUIRES: A5.1.1)
  - Add section: "## Schema Validation"
  - Document that all schemas are enforced via `pipeline/models.py`
  - Link field definitions to Pydantic model source code
  - Note benefits: type safety, automatic validation, retry logic
- [ ] **A5.2.6** Create `35_llm_obligations.py` - Enhanced obligation extraction (REQUIRES: A5.2.2)
  - **Stage 1 (Fast Filter)**: Regex scan for sections containing numbers, "$", or temporal keywords
  - **Stage 2 (LLM Classify)**: Send candidates to Gemini/Ollama for classification
  - Use Pydantic model: `Obligation(type, phrase, value, unit, category)`
  - Categories: "deadline" | "constraint" | "allocation" | "penalty"
  - Output: `obligations_enhanced.ndjson` (replaces separate deadlines/amounts files)
  - Support `--in`, `--out`, `--filter-threshold` flags
  - Checkpoint/resume with .ckpt file
- [ ] **A5.2.7** Run enhanced obligations extraction on subset
  ```bash
  python pipeline/35_llm_obligations.py \
    --in data/outputs/sections_subset.ndjson \
    --out data/outputs/obligations_enhanced_subset.ndjson
  ```
- [ ] **A5.2.8** Verify enhanced obligations output
  ```bash
  wc -l data/outputs/obligations_enhanced_subset.ndjson
  jq -r '.category' data/outputs/obligations_enhanced_subset.ndjson | sort | uniq -c
  ```

**Acceptance**: ✅ Instructor + Pydantic integrated, 200+ lines of parsing code removed, enhanced obligations extracted

---

### Track A (Continued): Optimize Similarity Search

- [ ] **A5.2.9** Update `40_similarities.py` to use FAISS IVF indexing (BLOCKS: B5.2.2)
  - Replace `faiss.IndexFlatIP` with `faiss.IndexIVFFlat`
  - Train index on 5,000 representative vectors (from subset or sample)
  - Set `nprobe` parameter for speed/accuracy tradeoff
  - Add `--use-ivf` and `--train-size` flags
  - Document expected speedup (100x) vs accuracy loss (<1%)
  - Test on subset to verify similar results to flat index
- [ ] **A5.2.10** Benchmark IVF vs Flat indexing
  ```bash
  # Flat (baseline)
  time python pipeline/40_similarities.py --in data/outputs/sections_subset.ndjson --out flat.ndjson

  # IVF (optimized)
  time python pipeline/40_similarities.py --in data/outputs/sections_subset.ndjson --out ivf.ndjson --use-ivf --train-size 5000
  ```
- [ ] **A5.2.11** Compare outputs to verify accuracy
  ```bash
  # Should have >99% overlap in detected pairs
  python scripts/compare_similarity_outputs.py flat.ndjson ivf.ndjson
  ```

**Acceptance**: ✅ IVF indexing working, 100x speedup confirmed, >99% accuracy maintained

---

### Track D: Triage & Verify Strategy for Similarity Classification

**Goal**: Implement "Model Cascading" (AI Triage) to optimize similarity classification - use Cross-Encoder (BERT) to filter "boring" cases and flag critical cases for LLM verification

**Strategy**:
1. **Triage (Fast)**: Cross-Encoder (BERT on Mac M2 MPS) checks every pair
2. **Filter (Optimization)**: If BERT says "Neutral" (Related) with high confidence, skip LLM (~80% of cases)
3. **Graduate (Verify)**: If BERT detects "Entailment" (Duplicate) or "Contradiction" (Conflict), send to LLM
4. **Augment**: Pass BERT's suspicion to LLM prompt to reduce hallucination

**Performance**: Expected to reduce LLM calls by ~80% while maintaining/improving accuracy through augmented prompts

- [ ] **D5.2.1** Add `sentence-transformers` to requirements (BLOCKS: D5.2.2)
  ```bash
  source .venv/bin/activate
  pip install sentence-transformers torch
  pip freeze > pipeline/requirements.txt
  ```
- [ ] **D5.2.2** Update `pipeline/models.py` with triage metadata fields (REQUIRES: D5.2.1, A5.1.1)
  - Add to `SimilarityClassification` model:
    - `cross_encoder_label: Optional[str]` - Label from NLI model (entailment/contradiction/neutral)
    - `cross_encoder_score: Optional[float]` - Confidence score from NLI model
  - These fields allow auditing: "Where did Cross-Encoder say Conflict but LLM say Related?"
- [ ] **D5.2.3** Create triage classifier in `55_similarity_classification.py` (REQUIRES: D5.2.2)
  - Initialize `CrossEncoder('cross-encoder/nli-deberta-v3-xsmall')` at module level
  - Use Mac M2 MPS acceleration: `device="mps"` if available, else `"cpu"`
  - Create `get_triage_classification(text_a: str, text_b: str)` function
  - Return: `{'label': str, 'score': float}`
  - Labels: "contradiction" (Conflict), "entailment" (Duplicate), "neutral" (Related)
- [ ] **D5.2.4** Modify main processing loop for triage workflow (REQUIRES: D5.2.3, BLOCKS: D5.2.5)
  - **Step 1**: Run Cross-Encoder triage on every pair
  - **Step 2 (Filter)**: If label="neutral" AND score > 0.5, write "related" classification and skip LLM
  - **Step 3 (Graduate)**: If label="entailment" or "contradiction", send to LLM with triage context
  - **Step 4 (Augment)**: Pass triage context to LLM prompt function
  - Log: "Graduating {section_a} vs {section_b} to LLM. Flagged as: {label}"
  - Record cross_encoder_label and cross_encoder_score in all outputs
- [ ] **D5.2.5** Update LLM prompt to use triage context (REQUIRES: D5.2.4)
  - Add `triage_context` parameter to prompt function
  - Map NLI labels to legal terms:
    - "entailment" → "NOTE: A logic analysis suggests these sections may be DUPLICATES or SUPERSEDED."
    - "contradiction" → "NOTE: A logic analysis suggests these sections may be CONFLICTING."
  - Prepend hint to prompt to ground the LLM
- [ ] **D5.2.6** Create database migration for triage metadata (BLOCKS: D5.2.8)
  ```sql
  -- File: dbtools/schema_migrations/add_triage_metadata.sql
  ALTER TABLE section_similarity_classifications
  ADD COLUMN cross_encoder_label TEXT,
  ADD COLUMN cross_encoder_score REAL;

  CREATE INDEX idx_similarity_cross_encoder
  ON section_similarity_classifications(cross_encoder_label);
  ```
- [ ] **D5.2.7** Test triage on subset data
  ```bash
  # Run with triage enabled
  python pipeline/55_similarity_classification.py \
    --similarities data/outputs/similarities_subset.ndjson \
    --sections data/outputs/sections_subset.ndjson \
    --out data/outputs/similarity_classifications_triage_subset.ndjson
  ```
  - Monitor logs for filter/graduate split
  - Verify cross_encoder fields populated in output
- [ ] **D5.2.8** Analyze triage effectiveness (REQUIRES: D5.2.7)
  ```bash
  # Count how many pairs were filtered vs graduated
  jq -r '.cross_encoder_label' data/outputs/similarity_classifications_triage_subset.ndjson | sort | uniq -c

  # Find disagreements between Cross-Encoder and LLM
  jq 'select(.cross_encoder_label == "contradiction" and .classification != "conflicting")' \
    data/outputs/similarity_classifications_triage_subset.ndjson
  ```
  - Calculate: % of pairs filtered (skipped LLM)
  - Document: Cases where Cross-Encoder and LLM disagreed
  - Expected: ~80% filtered, <5% disagreement rate

**Acceptance**: ✅ Cross-Encoder triage working, ~80% of LLM calls eliminated, triage metadata stored for audit

---

### Track B: Load Enhanced Intelligence Data

- [ ] **B5.2.1** Create `dbtools/load_obligations_enhanced.py` (REQUIRES: A5.2.7)
  - Read `obligations_enhanced.ndjson`
  - Insert to new `obligations` table (replaces deadlines + amounts)
  - Schema: jurisdiction, section_id, type, phrase, value, unit, category
  - ON CONFLICT UPDATE for idempotency
  - Batch inserts with BaseLoader pattern
  - .state file for resume
- [ ] **B5.2.2** Run enhanced obligations loader
  ```bash
  python dbtools/load_obligations_enhanced.py \
    --input data/outputs/obligations_enhanced_subset.ndjson
  ```
- [ ] **B5.2.3** Verify enhanced data loaded
  ```bash
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM obligations WHERE jurisdiction = 'dc';"
  psql $DATABASE_URL -c "SELECT category, COUNT(*) FROM obligations GROUP BY category;"
  ```
- [ ] **B5.2.4** Create migration to add `obligations` table
  ```sql
  CREATE TABLE obligations (
    id BIGSERIAL,
    jurisdiction VARCHAR(10) NOT NULL,
    section_id TEXT NOT NULL,
    type TEXT NOT NULL, -- 'deadline', 'constraint', 'allocation', 'penalty'
    phrase TEXT NOT NULL,
    value NUMERIC,
    unit TEXT, -- 'days', 'dollars', 'percent', etc.
    category TEXT,
    PRIMARY KEY (jurisdiction, id),
    FOREIGN KEY (jurisdiction, section_id) REFERENCES sections(jurisdiction, id)
  );
  ```

**Acceptance**: ✅ Enhanced obligations loaded with LLM classifications, obligations table populated

---

### Track C: UI Updates for Enhanced Intelligence

- [ ] **C5.2.1** Update section detail page to show enhanced obligations (REQUIRES: B5.2.3)
  - Query `obligations` table instead of separate deadlines/amounts
  - Group by category for display
  - Show classification badges (Deadline, Constraint, Allocation, Penalty)
  - Use existing colored panels from STYLE_GUIDE.md
- [ ] **C5.2.2** Update search filters to include obligation categories
  - Add "Has obligations" checkbox
  - Add category filter dropdown (Deadline, Constraint, etc.)
  - Update search API to support filtering
- [ ] **C5.2.3** Test enhanced obligations display
  - Verify all categories display correctly
  - Check badge colors and icons
  - Ensure filtering works in search

**Acceptance**: ✅ Enhanced obligations visible in UI with categories, filters working

---

## 🎨 Milestone 5.3: "BCG-Level" UX Polish

**Goal**: Professional legal intelligence platform UI with sophisticated navigation and visualization
**Status**: ⚪ Not Started

**Rationale**: Transform from "prototype search tool" to "professional legal intelligence platform" with in-text citations, graph visualizations, conflict dashboards, and refined typography.

### Track C: UI/UX Enhancements

- [ ] **C5.3.1** Install `shadcn/ui` component library (BLOCKS: C5.3.2-C5.3.8)
  ```bash
  cd apps/web
  npx shadcn-ui@latest init
  npx shadcn-ui@latest add button card dialog select dropdown-menu separator
  ```
  - Configure with existing Tailwind theme (slate/teal from STYLE_GUIDE.md)
  - Test components render correctly
- [ ] **C5.3.2** Implement in-text citation hyperlinking (REQUIRES: C5.3.1)
  - Create `apps/web/lib/citation-linker.ts` utility
  - Parse `text_html` on client-side to find citation patterns (§ X-XXX)
  - Wrap citations in `<Link href="/section/{jurisdiction}:{id}">` tags
  - Support cross-jurisdiction links (e.g., "see Cal. Code § 123")
  - Handle edge cases: ranges (§ 1-101 to 1-105), multiple citations in sentence
  - Add hover preview on citation links (show tooltip with section heading)
- [ ] **C5.3.3** Add citation graph visualization (REQUIRES: C5.3.1, B5.1.5)
  - Install `react-force-graph` library
  ```bash
  cd apps/web
  pnpm add react-force-graph
  ```
  - Create `apps/web/components/CitationGraph.tsx` component
  - Query inbound + outbound refs for current section
  - Render force-directed graph with D3
  - Color code nodes by relationship type (reference, similar, conflicting)
  - Click node to navigate to that section
  - Add zoom/pan controls
- [ ] **C5.3.4** Create `/legislative` conflict dashboard route (REQUIRES: B5.1.5)
  - Create `apps/web/app/legislative/page.tsx`
  - Query all sections with `classification = 'conflicting'` or `'superseded'`
  - Display in table format: Citation | Heading | Related To | Effective Date | Classification
  - Sort by effective date (newest first)
  - Filter by jurisdiction, title, classification type
  - Click row to see side-by-side diff view
  - Add export to CSV button
  - Target audience: Legislative counsel, policy analysts
- [ ] **C5.3.5** Add hover cards for citation previews (REQUIRES: C5.3.2)
  - Install `@radix-ui/react-hover-card` (part of shadcn/ui)
  - On hover over citation link, fetch section snippet via API
  - Show popover with:
    - Section heading
    - First paragraph of text
    - Link to "View full section"
  - Add debounce to avoid excessive API calls
  - Cache fetched snippets in memory
- [ ] **C5.3.6** Implement fixed sidebar hierarchy navigation (REQUIRES: B5.1.2)
  - Create `apps/web/components/HierarchyNav.tsx` component
  - Query `structure` table for current jurisdiction
  - Render collapsible tree:
    - Title (expandable)
      - Chapter (expandable)
        - Section (links to detail page)
  - Fixed position sidebar (left side, scrollable independently)
  - Highlight current section in tree
  - Collapse/expand all button
  - Search within hierarchy
- [ ] **C5.3.7** Add metadata right rail to section detail (REQUIRES: C5.3.1)
  - Create `apps/web/components/MetadataRail.tsx`
  - Fixed position right sidebar on section detail page
  - Contains:
    - Effective Date badge
    - Reporting Requirements summary
    - Deadlines/Obligations quick list
    - Similar Sections (top 3)
    - Conflict badges (if applicable)
  - Sticky scroll behavior
  - Responsive: collapses to accordion on mobile
- [ ] **C5.3.8** Upgrade typography and visual hierarchy (REQUIRES: C5.3.1)
  - Update `apps/web/tailwind.config.ts`:
    - Add Inter font for UI text
    - Add Merriweather or Playfair Display for legal text (serif)
  - Update STYLE_GUIDE.md with font pairings
  - Apply to pages:
    - Home page: Hero with refined typography
    - Search page: Cleaner filter layout
    - Section detail: Serif body text, sans-serif UI
  - Add visual enhancements:
    - Conflict badges: ⚠️ icon + amber-600
    - Related badges: 🔗 icon + sky-600
    - Superseded badges: 🔄 icon + slate-600
    - Duplicate badges: 📋 icon + indigo-600
  - Refine spacing using consistent scale from STYLE_GUIDE.md
- [ ] **C5.3.9** Update Navigation component for professional feel (REQUIRES: C5.3.1, C5.3.8)
  - Create `apps/web/components/Navigation.tsx`
  - Header with:
    - Logo/brand (Deproceduralizer)
    - Jurisdiction selector dropdown
    - Main nav links: Search, Legislative Dashboard, Reporting, About
    - User avatar placeholder (future auth)
  - Breadcrumbs bar below header (fixed, scrolls with page)
  - Mobile-responsive hamburger menu
  - Use slate/teal color palette from STYLE_GUIDE.md
- [ ] **C5.3.10** Test UX enhancements across devices (REQUIRES: C5.3.1-C5.3.9)
  - Desktop (1920x1080): Verify three-column layout (hierarchy | content | metadata)
  - Tablet (768x1024): Verify sidebars collapse appropriately
  - Mobile (375x667): Verify navigation hamburger, accordions work
  - Test citation links, hover cards, graph interactions
  - Verify WCAG 2.2 AA contrast ratios (use accessibility checker)
  - Test keyboard navigation (Tab, Enter, Escape)

**Acceptance**: ✅ Professional UI with in-text citations, graph viz, conflict dashboard, hover cards, fixed sidebars, refined typography

---

## 🔍 Milestone 5.5: Similarity Classification Analysis

**Goal**: Use LLM to classify why similar sections are related (duplicate/superseded/related/conflicting), add comprehensive filters
**Status**: ⚪ Not Started

**Note**: This milestone should apply the instructor/Pydantic improvements from Milestone 5.2 when implementing the LLM classification pipeline.

### Track A: LLM Classification Pipeline

- [ ] **A5.5.1** Install Google Gemini API client (BLOCKS: A5.5.2)
  ```bash
  source .venv/bin/activate
  pip install google-genai
  pip freeze > pipeline/requirements.txt
  ```
- [ ] **A5.5.2** Implement `pipeline/55_similarity_classification.py` (REQUIRES: A5.5.1, A4.2, BLOCKS: B5.5.2)
  - Read `similarities_subset.ndjson` (254 pairs with similarity scores)
  - For each pair, fetch text_plain for both sections from `sections_subset.ndjson`
  - Call Gemini 2.0 Flash API to classify relationship type
  - Fallback to Ollama phi3.5 when rate limited (track which model used)
  - Classifications: duplicate | superseded | related | conflicting
  - Rate limiting: 15 RPM, 1M TPM, 1500 RPD (Gemini free tier)
  - Store: section_a, section_b, similarity, classification, explanation, model_used, analyzed_at
  - Write to `data/outputs/similarity_classifications_subset.ndjson`
  - Checkpoint every 10 pairs (.ckpt file for resume)
  - Support `--similarities`, `--sections`, `--out` flags
- [ ] **A5.5.3** Run classification pipeline (REQUIRES: A5.5.2)
  ```bash
  python pipeline/55_similarity_classification.py \
    --similarities data/outputs/similarities_subset.ndjson \
    --sections data/outputs/sections_subset.ndjson \
    --out data/outputs/similarity_classifications_subset.ndjson
  ```
- [ ] **A5.5.4** Verify output (REQUIRES: A5.5.3)
  ```bash
  wc -l data/outputs/similarity_classifications_subset.ndjson  # Should be 254
  jq -r '.classification' data/outputs/similarity_classifications_subset.ndjson | sort | uniq -c
  jq -r '.model_used' data/outputs/similarity_classifications_subset.ndjson | sort | uniq -c
  ```

**Note**: Gemini API key should be set in `.env` file as `GEMINI_API_KEY`
**Acceptance**: ✅ 254 similarity pairs classified, both Gemini and phi3.5 usage tracked

---

### Track B: Store Classifications

- [ ] **B5.5.1** Create schema migration for classifications table (REQUIRES: B4.2, BLOCKS: B5.5.2)
  - Create `dbtools/schema_migrations/add_similarity_classifications.sql`
  - Table: `dc_section_similarity_classifications`
  - Columns: section_a, section_b, classification, explanation, model_used, analyzed_at
  - Primary key: (section_a, section_b)
  - Foreign key to `dc_section_similarities` with CASCADE
  - Index on classification column
  - Run migration against Neon DB
- [ ] **B5.5.2** Implement `dbtools/load_similarity_classifications.py` (REQUIRES: A5.5.3, B5.5.1)
  - Read `similarity_classifications_subset.ndjson`
  - Batch insert with ON CONFLICT UPDATE
  - .state file for resume
  - Support `--input` flag
- [ ] **B5.5.3** Run loader (REQUIRES: B5.5.2)
  ```bash
  python dbtools/load_similarity_classifications.py \
    --input data/outputs/similarity_classifications_subset.ndjson
  ```
- [ ] **B5.5.4** Verify data loaded (REQUIRES: B5.5.3)
  ```bash
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM dc_section_similarity_classifications;"
  psql $DATABASE_URL -c "SELECT classification, COUNT(*) FROM dc_section_similarity_classifications GROUP BY classification;"
  psql $DATABASE_URL -c "SELECT model_used, COUNT(*) FROM dc_section_similarity_classifications GROUP BY model_used;"
  ```

**Acceptance**: ✅ 254 classifications loaded, distribution by type and model verified

---

### Track C: Advanced Similarity Filters & UI

- [ ] **C5.5.1** Update `apps/web/db/schema.ts` (REQUIRES: B5.5.1)
  - Add `dcSectionSimilarityClassifications` table definition
  - Add proper relations to similarities and sections tables
- [ ] **C5.5.2** Update `/api/search` route (REQUIRES: C5.5.1, B5.5.4)
  - Add `hasSimilar` boolean filter (sections with any similarities)
  - Add `minSimilarity` and `maxSimilarity` number filters (0.7-1.0)
  - Add `similarityClassification` filter (duplicate|superseded|related|conflicting)
  - Join with `dc_section_similarities` and `dc_section_similarity_classifications` when filters active
- [ ] **C5.5.3** Update `/search` page UI (REQUIRES: C5.5.2)
  - Add "Similar Sections" filter panel
  - Add "Has similar sections" checkbox
  - Add similarity percentage range slider (70-100%)
  - Add classification type dropdown (All, Duplicate, Superseded, Related, Conflicting)
  - Add collapsible legend explaining each classification:
    - **Duplicate**: Nearly identical provisions, consolidation opportunity
    - **Superseded**: One section replaces/updates the other
    - **Related**: Similar topics, different purposes
    - **Conflicting**: Similar language, contradictory requirements
  - Use distinct colors for each classification type
- [ ] **C5.5.4** Update `/section/[id]` page (REQUIRES: C5.5.2)
  - Query `dc_section_similarity_classifications` for each similar section
  - Display classification badge (colored by type) next to similar sections
  - Show explanation text on hover/expand
  - Show model used in small gray text
  - Keep existing diff modal functionality
- [ ] **C5.5.5** Test all functionality (REQUIRES: C5.5.3, C5.5.4)
  - Test filters individually and in combination
  - Test with known duplicates (similarity ~1.0)
  - Verify legend clarity and accuracy
  - Check mobile responsiveness
- [x] **C5.5.6** Create reporting requirements summary page (REQUIRES: C5.3, C5.4)
  - Add `/reporting` route (`apps/web/app/reporting/page.tsx`)
  - Query all sections where `has_reporting = true`
  - Display in table/card format showing: citation, heading, summary, tags
  - Add filters: by tag, by title/chapter, search within summaries
  - Add sorting options: by citation, by title, alphabetically
  - Link each section to its detail page (`/section/[id]`)
  - Show count of total reporting requirements at top
  - Group by tag categories (collapsible sections)

**Acceptance**: ✅ Advanced filters working, legend helpful, classifications displayed with badges and explanations

---

## 🔬 Milestone 6: Medium Corpus Processing

**Goal**: Process expanded subset (Titles 1-10) to test pipeline at scale (~6 hour runtime)
**Status**: ⏸️ PAUSED - Do Milestones 5.1, 5.2, 5.3 first

**⚠️ STRATEGIC PAUSE**: Before processing medium/full corpus, we must complete architectural refinement (Milestones 5.1-5.3). Processing thousands of sections with brittle regex parsing and no multi-jurisdiction support would create technical debt at scale.

**Rationale**: Current subset (Titles 1-2, ~100 sections, ~1 hour) → Medium subset (Titles 1-10, ~500-600 sections, ~5-6 hours) → Full corpus (~50 titles, days). Provides realistic scale testing before full corpus processing.

**Prerequisites**: Milestones 5.1 (Architecture Hardening), 5.2 (Enhanced Intelligence), 5.3 (UX Polish) must be complete.

### Track A: Medium Corpus Pipeline Scripts

- [ ] **A6.1** Create `scripts/make_subset_medium.sh` (BLOCKS: A6.2)
  - Copy **all sections** from Titles 1-10 (not just first 50 like small subset)
  - Target directory: `data/subsets_medium/`
  - Include all title index files (1-10) for hierarchy information
  - Estimated ~500-600 sections total
  ```bash
  #!/bin/bash
  # Similar to make_subset.sh but for Titles 1-10 (full sections, not limited to 50)
  SOURCE_DIR="data/raw/dc-law-xml/us/dc/council/code/titles"
  DEST_DIR="data/subsets_medium"
  # Copy all sections from Titles 1-10
  for i in {1..10}; do
    cp "$SOURCE_DIR/$i/sections/"*.xml "$DEST_DIR/"
    cp "$SOURCE_DIR/$i/index.xml" "$DEST_DIR/title-$i-index.xml"
  done
  ```
- [ ] **A6.2** Create `scripts/run_all_medium.sh` (REQUIRES: A6.1, BLOCKS: B6.1)
  - Mirror structure of `run_all_subset.sh` but with ALL 6 pipeline steps
  - Run on `data/subsets_medium/` → output to `data/outputs/*_medium.ndjson`
  - Pipeline steps:
    1. Parse XML: `10_parse_xml.py --src data/subsets_medium --out sections_medium.ndjson`
    2. Extract cross-refs: `20_crossrefs.py --in sections_medium.ndjson --out refs_medium.ndjson`
    3. Extract obligations: `30_regex_obligations.py --in sections_medium.ndjson --deadlines deadlines_medium.ndjson --amounts amounts_medium.ndjson`
    4. Compute similarities: `40_similarities.py --in sections_medium.ndjson --out similarities_medium.ndjson --top-k 10 --min-similarity 0.7` ⏱️ **SLOW**
    5. **Classify similarities**: `55_similarity_classification.py --similarities similarities_medium.ndjson --sections sections_medium.ndjson --out similarity_classifications_medium.ndjson` ⏱️ **VERY SLOW (LLM)**
    6. Detect reporting: `50_llm_reporting.py --in sections_medium.ndjson --out reporting_medium.ndjson` ⏱️ **SLOW (LLM)**
- [ ] **A6.3** Run medium corpus pipeline (REQUIRES: A6.2)
  ```bash
  ./scripts/make_subset_medium.sh
  ./scripts/run_all_medium.sh  # Target: ~5-6 hours runtime
  ```
- [ ] **A6.4** Verify all medium outputs exist (REQUIRES: A6.3)
  ```bash
  ls -lh data/outputs/*_medium.ndjson
  # Should have: sections, refs, deadlines, amounts, similarities, similarity_classifications, reporting
  wc -l data/outputs/sections_medium.ndjson  # Expected: ~500-600 lines
  ```

**Acceptance**: ✅ All medium corpus NDJSON files generated (~500-600 sections from Titles 1-10)

---

### Track B: Load Medium Corpus to Database

- [ ] **B6.1** Create `scripts/load_db_medium.sh` (REQUIRES: A6.4, BLOCKS: B6.2)
  - Run all loaders pointing to medium outputs
  - Loaders will append to existing database tables (alongside small subset data)
  ```bash
  #!/bin/bash
  source .venv/bin/activate
  python dbtools/load_sections.py --input data/outputs/sections_medium.ndjson
  python dbtools/load_refs.py --input data/outputs/refs_medium.ndjson
  python dbtools/load_deadlines_amounts.py \
    --deadlines data/outputs/deadlines_medium.ndjson \
    --amounts data/outputs/amounts_medium.ndjson
  python dbtools/load_similarities.py --input data/outputs/similarities_medium.ndjson
  python dbtools/load_similarity_classifications.py --input data/outputs/similarity_classifications_medium.ndjson
  python dbtools/load_reporting.py --input data/outputs/reporting_medium.ndjson
  ```
- [ ] **B6.2** Run medium corpus loaders (REQUIRES: B6.1)
  ```bash
  ./scripts/load_db_medium.sh
  ```
- [ ] **B6.3** Verify medium data loaded (REQUIRES: B6.2)
  ```bash
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM dc_sections;"  # Should be ~600-700 (100 small + 500-600 medium)
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM dc_section_similarity_classifications;"
  psql $DATABASE_URL -c "SELECT DISTINCT title_label FROM dc_sections ORDER BY title_label;"  # Should show Titles 1-10
  ```

**Acceptance**: ✅ Medium corpus loaded to database, all tables populated, titles 1-10 visible

---

### Track C: Performance Testing & Validation

- [ ] **C6.1** Test UI performance with larger dataset (REQUIRES: B6.3)
  - Search page: measure load times, test with various queries
  - Section detail page: check rendering speed with more similar sections
  - Similar sections: verify classification badges display correctly
  - Reporting page: test filters and grouping with more data
- [ ] **C6.2** Verify all features work correctly (REQUIRES: B6.3)
  - Full-text search finds results across Titles 1-10
  - Cross-references resolve correctly (more refs should exist now)
  - Similar sections appear with classification types (duplicate/superseded/related/conflicting)
  - Reporting requirements filter and display properly
  - Title/chapter filters show expanded options (10 titles worth)
- [ ] **C6.3** Document performance findings (REQUIRES: C6.1, C6.2)
  - Record actual pipeline runtime (compare to 1 hour estimate for small subset)
  - Note any bottlenecks in UI (slow queries, large result sets)
  - Identify optimizations needed before full corpus (~50 titles)
  - Document database size and index performance

**Acceptance**: ✅ Medium corpus performs well in UI, all features functional, runtime documented (~5-6 hours)

---

## 📊 Milestone 7: Reporting Requirements Deep Analysis

**Goal**: Comprehensive analysis and visualization of reporting requirements across DC Code
**Status**: ⚪ Not Started

### Track A: Enhanced Reporting Analysis Pipeline

- [ ] **A7.1** Extend reporting analysis pipeline (REQUIRES: A5.3, BLOCKS: B7.1)
  - Create `pipeline/60_reporting_deep_analysis.py` or extend `pipeline/50_llm_reporting.py`
  - Extract additional metadata from sections with reporting requirements:
    - **Frequency**: annual, quarterly, monthly, ad-hoc, event-triggered
    - **Responsible entities**: agencies, boards, commissions mentioned in text
    - **Filing methods**: electronic, written, public notice, etc.
    - **Consequences/penalties**: what happens for non-compliance
    - **Trigger events**: time-based vs event-triggered reporting
  - Categorize reporting types: financial, compliance, informational, public notice
  - Identify cross-references between related reporting requirements
  - Use LLM (Gemini/Ollama) for extraction and categorization
  - Output: enhanced NDJSON with additional fields
  - Support `--in`, `--out` flags and checkpoint resume
- [ ] **A7.2** Run enhanced reporting analysis (REQUIRES: A7.1)
  ```bash
  python pipeline/60_reporting_deep_analysis.py \
    --in data/outputs/sections_subset.ndjson \
    --out data/outputs/reporting_enhanced_subset.ndjson
  ```
- [ ] **A7.3** Verify enhanced reporting output (REQUIRES: A7.2)
  ```bash
  jq -r '.frequency' data/outputs/reporting_enhanced_subset.ndjson | sort | uniq -c
  jq -r '.category' data/outputs/reporting_enhanced_subset.ndjson | sort | uniq -c
  ```

**Acceptance**: ✅ Enhanced reporting metadata extracted with frequency, entities, categories

---

### Track B: Store Enhanced Reporting Metadata

- [ ] **B7.1** Create schema migration for reporting metadata (REQUIRES: B5.3, BLOCKS: B7.2)
  - Create `dbtools/schema_migrations/add_reporting_metadata.sql`
  - Add columns to `dc_sections`:
    - `reporting_frequency` TEXT (annual|quarterly|monthly|ad-hoc|event-triggered|null)
    - `reporting_category` TEXT (financial|compliance|informational|notice|null)
    - `reporting_trigger` TEXT (time-based|event-triggered|null)
  - Create `dc_reporting_entities` table:
    - `id` SERIAL PRIMARY KEY
    - `section_id` TEXT REFERENCES dc_sections
    - `entity_name` TEXT (agency/board/commission name)
    - `entity_type` TEXT (agency|board|commission|department)
  - Create `dc_reporting_related` table for cross-references between reporting requirements:
    - `section_a` TEXT REFERENCES dc_sections
    - `section_b` TEXT REFERENCES dc_sections
    - `relationship_type` TEXT (duplicates|complements|conflicts)
  - Add indexes on new columns
  - Run migration against Neon DB
- [ ] **B7.2** Implement `dbtools/load_reporting_enhanced.py` (REQUIRES: A7.2, B7.1)
  - Read `reporting_enhanced_subset.ndjson`
  - Update `dc_sections` with new reporting metadata columns
  - Insert reporting entities into `dc_reporting_entities`
  - Insert related reporting requirements into `dc_reporting_related`
  - Batch operations with ON CONFLICT handling
  - .state file for resume
  - Support `--input` flag
- [ ] **B7.3** Run enhanced reporting loader (REQUIRES: B7.2)
  ```bash
  python dbtools/load_reporting_enhanced.py \
    --input data/outputs/reporting_enhanced_subset.ndjson
  ```
- [ ] **B7.4** Verify enhanced data loaded (REQUIRES: B7.3)
  ```bash
  psql $DATABASE_URL -c "SELECT reporting_frequency, COUNT(*) FROM dc_sections WHERE has_reporting = true GROUP BY reporting_frequency;"
  psql $DATABASE_URL -c "SELECT reporting_category, COUNT(*) FROM dc_sections WHERE has_reporting = true GROUP BY reporting_category;"
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM dc_reporting_entities;"
  ```

**Acceptance**: ✅ Enhanced reporting metadata stored, entities and relationships tracked

---

### Track C: Reporting Visualization & Analysis UI

- [ ] **C7.1** Create reporting dashboard foundation (REQUIRES: C5.5.6, B7.4)
  - Enhance `/reporting` page created in C5.5.6
  - Add overview stats panel:
    - Total reporting requirements
    - Breakdown by category (pie chart or bar chart)
    - Breakdown by frequency (timeline visualization)
    - Top entities with most reporting requirements
  - Keep existing table/card view and filters from C5.5.6
- [ ] **C7.2** Add reporting analytics views (REQUIRES: C7.1)
  - Create `/reporting/timeline` view:
    - Calendar/timeline view showing when reports are due
    - Filter by month, quarter, year
    - Color-code by category
  - Create `/reporting/entities` view:
    - List of agencies/boards/commissions
    - Show count of reporting requirements per entity
    - Click to see all requirements for that entity
  - Add navigation between views in `/reporting` layout
- [ ] **C7.3** Add advanced reporting visualizations (REQUIRES: C7.2)
  - Network graph showing related reporting requirements
  - Use D3.js or similar for interactive visualization
  - Show connections: duplicates, complements, conflicts
  - Click nodes to navigate to section detail
- [ ] **C7.4** Add export functionality (REQUIRES: C7.1)
  - Export filtered reporting requirements to CSV
  - Export deadline calendar to iCal format
  - "Export" button in reporting dashboard
- [ ] **C7.5** Integrate reporting into main navigation (REQUIRES: C7.1)
  - Add "Reporting Requirements" link to Navigation component
  - Add reporting category badges to search results when applicable
  - Add link to `/reporting` from section detail pages with reporting
- [ ] **C7.6** Test reporting features (REQUIRES: C7.1-C7.5)
  - Test all filtering and sorting
  - Verify visualizations render correctly
  - Test exports (CSV, iCal)
  - Check mobile responsiveness
  - Verify navigation integration

**Acceptance**: ✅ Comprehensive reporting dashboard with stats, timeline, entity views, network visualization, and export

---

## 🌐 Milestone 8: Full DC Code Corpus

**Goal**: Process entire DC Code, deploy to production
**Status**: ⏸️ PAUSED - Do Milestones 5.1, 5.2, 5.3, then 6 first

**⚠️ STRATEGIC PAUSE**: Full corpus processing requires architectural refinement (Milestones 5.1-5.3) and medium corpus validation (Milestone 6).

**Prerequisites**: Milestones 5.1, 5.2, 5.3, and 6 must be complete. After this milestone, the system will be ready to add California, New York, and other jurisdictions.

### Track A: Full Corpus Processing

- [ ] **A8.1** Create `scripts/run_all_subset.sh`
  - Runs all pipeline scripts on subset data sequentially
  - Checks for errors after each step
- [ ] **A8.2** Create `scripts/run_all_full.sh`
  - Runs all pipeline scripts on full `data/raw/dc-law-xml/`
  - Same as subset but points to full data
- [ ] **A8.3** Run full corpus pipeline
  ```bash
  ./scripts/run_all_full.sh
  # This will take hours/days depending on machine
  # All scripts resume from checkpoints if interrupted
  ```
- [ ] **A8.4** Verify all full NDJSON files exist
  ```bash
  ls -lh data/outputs/*.ndjson
  ```

**Acceptance**: ✅ All full corpus NDJSON files generated

---

### Track B: Load Full Corpus

- [ ] **B8.1** Run all loaders on full data
  ```bash
  python dbtools/load_sections.py --input data/outputs/sections.ndjson
  python dbtools/load_refs.py --input data/outputs/refs.ndjson
  python dbtools/load_deadlines_amounts.py \
    --deadlines data/outputs/deadlines.ndjson \
    --amounts data/outputs/amounts.ndjson
  python dbtools/load_similarities.py --input data/outputs/similarities.ndjson
  python dbtools/load_reporting.py --input data/outputs/reporting.ndjson
  ```
- [ ] **B8.2** Verify full corpus loaded
  ```bash
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM dc_sections;"
  # Should be full DC Code section count (thousands)
  ```
- [ ] **B8.3** Analyze database size and performance
  ```sql
  SELECT pg_size_pretty(pg_total_relation_size('dc_sections'));
  ANALYZE dc_sections;  -- Update query planner statistics
  ```

**Acceptance**: ✅ Full corpus in database

---

### Track C: Production Optimizations

- [x] **C8.1** Add pagination to `/search` (limit/offset) *(completed in Milestone 2)*
  - Pagination implemented in both API and UI
  - Search API supports page/limit parameters
  - UI has Previous/Next buttons and page count display
- [ ] **C8.2** Add caching for common queries
  - Consider React Query or SWR
- [ ] **C8.3** Optimize database queries
  - Add indexes if slow queries identified
  - Use EXPLAIN ANALYZE to check query plans
- [x] **C8.4** Create landing page (`apps/web/app/page.tsx`) *(completed early in Milestone 1)*
  - Project description
  - Quick search box (redirects to `/search`)
  - Feature highlights
  - Stats (total sections, titles, etc.)
- [ ] **C8.5** Deploy to Vercel
  ```bash
  cd apps/web
  vercel --prod
  ```
- [ ] **C8.6** Test production deployment
  - Verify search works
  - Check loading performance
  - Test on mobile

**Acceptance**: ✅ Full DC Code searchable in production

---

## 📚 Architecture Patterns & Code Examples

This appendix provides reference implementations for key architectural patterns introduced in Milestones 5.1-5.3.

### Multi-Jurisdiction Database Schema

**Purpose**: Support DC, California, New York, and other legal codes in a single database without refactoring.

**Pattern**: Composite primary keys with jurisdiction column

```sql
-- Jurisdictions metadata table
CREATE TABLE jurisdictions (
  id VARCHAR(10) PRIMARY KEY,           -- 'dc', 'ca', 'ny', etc.
  name TEXT NOT NULL,                   -- 'District of Columbia Code'
  abbreviation VARCHAR(10) NOT NULL,    -- 'DC'
  type TEXT NOT NULL,                   -- 'district', 'state', 'county', 'city'
  parser_version TEXT NOT NULL,         -- '0.2.0'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sections table with jurisdiction support
CREATE TABLE sections (
  jurisdiction VARCHAR(10) NOT NULL,
  id TEXT NOT NULL,
  citation TEXT NOT NULL,
  heading TEXT NOT NULL,
  text_plain TEXT NOT NULL,
  text_html TEXT NOT NULL,
  text_fts TSVECTOR GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(heading, '') || ' ' || coalesce(text_plain, ''))
  ) STORED,
  title_label TEXT,
  chapter_label TEXT,
  effective_date DATE,
  has_reporting BOOLEAN DEFAULT FALSE,
  reporting_summary TEXT,
  reporting_tags TEXT[],
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (jurisdiction, id),
  FOREIGN KEY (jurisdiction) REFERENCES jurisdictions(id) ON DELETE CASCADE
);

CREATE INDEX idx_sections_jurisdiction ON sections(jurisdiction);
CREATE INDEX idx_sections_text_fts ON sections USING GIN(text_fts);
CREATE INDEX idx_sections_title ON sections(jurisdiction, title_label);

-- Cross-references with jurisdiction support
CREATE TABLE section_refs (
  jurisdiction VARCHAR(10) NOT NULL,
  from_id TEXT NOT NULL,
  to_id TEXT NOT NULL,
  raw_cite TEXT NOT NULL,
  PRIMARY KEY (jurisdiction, from_id, to_id, raw_cite),
  FOREIGN KEY (jurisdiction, from_id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE,
  FOREIGN KEY (jurisdiction, to_id) REFERENCES sections(jurisdiction, id) ON DELETE CASCADE
);

-- Hierarchical structure table
CREATE TABLE structure (
  jurisdiction VARCHAR(10) NOT NULL,
  id TEXT NOT NULL,
  parent_id TEXT,
  level TEXT NOT NULL,         -- 'title', 'subtitle', 'chapter', 'subchapter', 'section'
  label TEXT NOT NULL,          -- 'Title 1', 'Chapter 3', etc.
  heading TEXT,
  ordinal INTEGER,              -- For sorting
  PRIMARY KEY (jurisdiction, id),
  FOREIGN KEY (jurisdiction, parent_id) REFERENCES structure(jurisdiction, id)
);

CREATE INDEX idx_structure_parent ON structure(jurisdiction, parent_id);
CREATE INDEX idx_structure_level ON structure(jurisdiction, level);
```

**Benefits**:
- Single schema supports multiple jurisdictions
- No table duplication per jurisdiction
- Cross-jurisdiction queries possible
- Easy to add new jurisdictions (just insert into `jurisdictions` table)

---

### BaseLoader Pattern (DRY Principle)

**Purpose**: Eliminate 200+ lines of duplicated code across loaders

**Pattern**: Abstract base class with template method pattern

```python
# dbtools/common/base_loader.py
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List
import psycopg2
from psycopg2.extras import execute_batch
from tqdm import tqdm

logger = logging.getLogger(__name__)

class BaseLoader(ABC):
    """Abstract base class for all data loaders.

    Provides common functionality:
    - Progress bars (tqdm)
    - State file checkpoint/resume
    - DB connection pooling
    - Batch insertion
    - Error handling and logging

    Subclasses must implement:
    - process_batch(): Define SQL INSERT logic
    - validate_record(): Validate individual records
    """

    def __init__(
        self,
        db_url: str,
        input_file: str,
        batch_size: int = 500,
        jurisdiction: str = "dc"
    ):
        self.db_url = db_url
        self.input_file = Path(input_file)
        self.batch_size = batch_size
        self.jurisdiction = jurisdiction
        self.state_file = self.input_file.with_suffix('.state')

        # Statistics
        self.stats = {
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "errors": 0,
            "skipped": 0
        }

    def get_checkpoint(self) -> int:
        """Load checkpoint from state file."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                state = json.load(f)
                return state.get('offset', 0)
        return 0

    def save_checkpoint(self, offset: int):
        """Save checkpoint to state file."""
        with open(self.state_file, 'w') as f:
            json.dump({
                'offset': offset,
                'stats': self.stats,
                'jurisdiction': self.jurisdiction
            }, f, indent=2)

    @abstractmethod
    def process_batch(self, cursor, batch: List[Dict[str, Any]]):
        """Process a batch of records. Must be implemented by subclass.

        Args:
            cursor: psycopg2 cursor
            batch: List of validated records

        Should update self.stats with inserted/updated counts.
        """
        pass

    @abstractmethod
    def validate_record(self, record: Dict[str, Any]) -> bool:
        """Validate a single record. Must be implemented by subclass.

        Args:
            record: Single NDJSON record

        Returns:
            True if valid, False otherwise
        """
        pass

    def run(self):
        """Main execution method."""
        logger.info(f"Starting loader: {self.__class__.__name__}")
        logger.info(f"Input: {self.input_file}")
        logger.info(f"Jurisdiction: {self.jurisdiction}")

        # Get starting offset from checkpoint
        start_offset = self.get_checkpoint()
        if start_offset > 0:
            logger.info(f"Resuming from offset {start_offset}")

        # Open DB connection
        conn = psycopg2.connect(self.db_url)
        conn.autocommit = False
        cursor = conn.cursor()

        try:
            # Read NDJSON file
            with open(self.input_file) as f:
                lines = f.readlines()

            # Progress bar
            pbar = tqdm(total=len(lines), initial=start_offset, desc="Loading")

            batch = []
            for i, line in enumerate(lines[start_offset:], start=start_offset):
                try:
                    record = json.loads(line)

                    # Validate
                    if not self.validate_record(record):
                        self.stats['skipped'] += 1
                        continue

                    # Add jurisdiction if not present
                    if 'jurisdiction' not in record:
                        record['jurisdiction'] = self.jurisdiction

                    batch.append(record)

                    # Process batch when full
                    if len(batch) >= self.batch_size:
                        self.process_batch(cursor, batch)
                        conn.commit()
                        batch = []
                        self.save_checkpoint(i + 1)

                    self.stats['processed'] += 1
                    pbar.update(1)

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON at line {i}: {e}")
                    self.stats['errors'] += 1
                except Exception as e:
                    logger.error(f"Error processing line {i}: {e}")
                    self.stats['errors'] += 1
                    conn.rollback()

            # Process remaining batch
            if batch:
                self.process_batch(cursor, batch)
                conn.commit()
                self.save_checkpoint(len(lines))

            pbar.close()

            # Final stats
            logger.info(f"Completed: {self.stats}")

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()


# Example subclass: dbtools/load_sections.py
from dbtools.common.base_loader import BaseLoader

class SectionsLoader(BaseLoader):
    def validate_record(self, record):
        required = ['id', 'citation', 'heading', 'text_plain', 'text_html']
        for field in required:
            if field not in record:
                logger.error(f"Missing field: {field}")
                return False
        return True

    def process_batch(self, cursor, batch):
        sql = """
        INSERT INTO sections (
            jurisdiction, id, citation, heading, text_plain, text_html,
            title_label, chapter_label
        ) VALUES (
            %(jurisdiction)s, %(id)s, %(citation)s, %(heading)s,
            %(text_plain)s, %(text_html)s, %(title_label)s, %(chapter_label)s
        )
        ON CONFLICT (jurisdiction, id) DO UPDATE SET
            citation = EXCLUDED.citation,
            heading = EXCLUDED.heading,
            text_plain = EXCLUDED.text_plain,
            text_html = EXCLUDED.text_html,
            title_label = EXCLUDED.title_label,
            chapter_label = EXCLUDED.chapter_label,
            updated_at = NOW()
        """

        execute_batch(cursor, sql, batch, page_size=self.batch_size)
        self.stats['inserted'] += len(batch)

# Usage
if __name__ == "__main__":
    import sys
    loader = SectionsLoader(
        db_url=os.getenv("DATABASE_URL"),
        input_file=sys.argv[1],
        jurisdiction="dc"
    )
    loader.run()
```

**Benefits**:
- No code duplication across loaders
- Consistent progress bars, logging, error handling
- Easy to add new loaders (just implement 2 methods)
- Checkpoint/resume logic in one place

---

### Structured LLM with Pydantic + Instructor

**Purpose**: Replace 200+ lines of brittle regex JSON parsing with automatic validation

**Pattern**: Pydantic models + instructor library

```python
# pipeline/models.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal

class ReportingRequirement(BaseModel):
    """LLM-extracted reporting requirement from legal section."""

    has_reporting: bool = Field(
        ...,
        description="True if section mandates any reporting, filing, or notice requirement"
    )

    reporting_summary: str = Field(
        default="",
        description="Concise 1-2 sentence summary of what must be reported and to whom",
        max_length=500
    )

    frequency: Optional[Literal["annual", "quarterly", "monthly", "ad-hoc", "event-triggered"]] = Field(
        None,
        description="How often the report is required"
    )

    entities: List[str] = Field(
        default_factory=list,
        description="List of entities responsible for reporting (e.g., 'Mayor', 'Board of Education')"
    )

    tags: List[str] = Field(
        default_factory=list,
        description="High-level categorization tags (lowercase, kebab-case)",
        max_length=10
    )

    highlight_phrases: List[str] = Field(
        default_factory=list,
        description="Exact phrases from the text that indicate reporting requirements"
    )

    @field_validator('tags')
    @classmethod
    def lowercase_tags(cls, v):
        """Ensure tags are lowercase."""
        return [tag.lower().replace(' ', '-') for tag in v]


class Obligation(BaseModel):
    """LLM-extracted obligation (deadline, constraint, allocation, penalty)."""

    category: Literal["deadline", "constraint", "allocation", "penalty"] = Field(
        ...,
        description="Type of obligation"
    )

    phrase: str = Field(
        ...,
        description="Exact text phrase from the section",
        min_length=5,
        max_length=500
    )

    value: Optional[float] = Field(
        None,
        description="Numeric value (days for deadlines, dollars for amounts)"
    )

    unit: Optional[str] = Field(
        None,
        description="Unit of measurement (days, dollars, percent, etc.)"
    )


class SimilarityClassification(BaseModel):
    """LLM classification of why two sections are similar."""

    classification: Literal["duplicate", "superseded", "related", "conflicting"] = Field(
        ...,
        description="Type of relationship between the sections"
    )

    explanation: str = Field(
        ...,
        description="Brief explanation of why they are classified this way",
        min_length=20,
        max_length=500
    )

    confidence: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="LLM's confidence in this classification"
    )


# pipeline/llm_client.py
import os
import logging
from typing import Type, TypeVar
import instructor
from pydantic import BaseModel
from google import genai
import requests

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    """Unified LLM client with Gemini + Ollama fallback."""

    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.ollama_url = "http://localhost:11434"

        # Initialize Gemini client with instructor
        if self.gemini_key:
            client = genai.Client(api_key=self.gemini_key)
            self.gemini_client = instructor.from_gemini(client)
        else:
            self.gemini_client = None
            logger.warning("No GEMINI_API_KEY found, will use Ollama only")

    def generate(
        self,
        prompt: str,
        response_model: Type[T],
        model: str = "gemini-2.5-flash",
        max_retries: int = 3
    ) -> T:
        """Generate structured output from LLM.

        Args:
            prompt: User prompt
            response_model: Pydantic model for validation
            model: Model name (Gemini or Ollama)
            max_retries: Number of retries on validation failure

        Returns:
            Validated Pydantic model instance

        Raises:
            ValueError: If all attempts fail
        """
        # Try Gemini first
        if self.gemini_client and model.startswith("gemini"):
            try:
                result = self.gemini_client.chat.completions.create(
                    model=model,
                    response_model=response_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_retries=max_retries
                )
                logger.info(f"Generated with {model}")
                return result
            except Exception as e:
                logger.warning(f"Gemini failed: {e}, falling back to Ollama")

        # Fallback to Ollama
        return self._generate_ollama(prompt, response_model, max_retries)

    def _generate_ollama(
        self,
        prompt: str,
        response_model: Type[T],
        max_retries: int
    ) -> T:
        """Generate with Ollama + manual validation."""
        import json

        # Add schema to prompt
        schema = response_model.model_json_schema()
        enhanced_prompt = f"""
{prompt}

IMPORTANT: Return ONLY valid JSON matching this schema:
{json.dumps(schema, indent=2)}
"""

        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": "phi4-mini",
                        "prompt": enhanced_prompt,
                        "stream": False,
                        "format": "json"
                    },
                    timeout=60
                )
                resp.raise_for_status()

                # Parse and validate
                raw_json = resp.json()["response"]
                data = json.loads(raw_json)
                result = response_model.model_validate(data)

                logger.info("Generated with Ollama phi4-mini")
                return result

            except Exception as e:
                logger.warning(f"Ollama attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise ValueError(f"All {max_retries} attempts failed")

        raise ValueError("Unreachable")


# Usage in pipeline scripts
from pipeline.models import ReportingRequirement
from pipeline.llm_client import LLMClient

client = LLMClient()

def analyze_section(section_text: str) -> ReportingRequirement:
    prompt = f"""
Analyze this legal code section for reporting requirements.

SECTION TEXT:
{section_text}

Identify:
1. Does it require any reports, filings, or notices?
2. Who must report and to whom?
3. How often?
4. Extract exact phrases that indicate these requirements.
"""

    # Returns validated ReportingRequirement instance (not raw JSON!)
    return client.generate(
        prompt=prompt,
        response_model=ReportingRequirement,
        model="gemini-2.5-flash"
    )

# No more parse_llm_json() needed!
# No more manual field validation!
# Automatic retries on malformed responses!
```

**Benefits**:
- Eliminate 40+ lines of regex JSON parsing per script
- Automatic validation with helpful error messages
- Type safety with IDE autocomplete
- Built-in retry logic
- Single source of truth for schemas (Pydantic models)

---

### Jurisdiction-Aware Parser (Abstract Base + DC Subclass)

**Purpose**: Support different XML formats for DC, California, etc. without code duplication

**Pattern**: Abstract base parser with jurisdiction-specific subclasses

```python
# pipeline/parsers/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pathlib import Path

class BaseParser(ABC):
    """Abstract base parser for legal code XML."""

    def __init__(self, jurisdiction: str):
        self.jurisdiction = jurisdiction

    @abstractmethod
    def parse_structure(self, index_file: Path) -> List[Dict[str, Any]]:
        """Parse index.xml to extract hierarchical structure.

        Returns list of structure records:
        {
            "jurisdiction": "dc",
            "id": "dc-title-1",
            "parent_id": None,
            "level": "title",
            "label": "Title 1",
            "heading": "Government Organization",
            "ordinal": 1
        }
        """
        pass

    @abstractmethod
    def parse_section(self, section_file: Path) -> Dict[str, Any]:
        """Parse individual section XML.

        Returns section record:
        {
            "jurisdiction": "dc",
            "id": "dc-1-101",
            "citation": "§ 1-101",
            "heading": "Title and short title",
            "text_plain": "...",
            "text_html": "...",
            "effective_date": "2024-01-01"
        }
        """
        pass


# pipeline/parsers/dc.py
import xml.etree.ElementTree as ET
from pipeline.parsers.base import BaseParser

class DCParser(BaseParser):
    """Parser for DC Code XML format."""

    def parse_structure(self, index_file):
        tree = ET.parse(index_file)
        root = tree.getroot()

        # DC-specific XML structure
        # <collection>
        #   <container id="dc-title-1" type="title">
        #     <heading>Government Organization</heading>
        #     <num>1</num>
        #   </container>
        # </collection>

        structures = []
        for container in root.findall(".//container"):
            structures.append({
                "jurisdiction": self.jurisdiction,
                "id": container.get("id"),
                "parent_id": container.get("parent_id"),
                "level": container.get("type"),
                "label": f"Title {container.find('num').text}",
                "heading": container.find("heading").text,
                "ordinal": int(container.find("num").text)
            })

        return structures

    def parse_section(self, section_file):
        tree = ET.parse(section_file)
        root = tree.getroot()

        # DC-specific section structure
        section_id = root.get("id")
        citation = root.find(".//num").text
        heading = root.find(".//heading").text

        # Extract text
        text_elem = root.find(".//text")
        text_html = ET.tostring(text_elem, encoding='unicode', method='html')
        text_plain = ''.join(text_elem.itertext())

        # Extract effective date from history
        history = root.find(".//history")
        effective_date = None
        if history is not None:
            date_elem = history.find(".//date[@type='effective']")
            if date_elem is not None:
                effective_date = date_elem.text

        return {
            "jurisdiction": self.jurisdiction,
            "id": section_id,
            "citation": f"§ {citation}",
            "heading": heading,
            "text_plain": text_plain,
            "text_html": text_html,
            "effective_date": effective_date
        }


# Future: pipeline/parsers/california.py
class CaliforniaParser(BaseParser):
    """Parser for California Code XML format (different structure)."""

    def parse_structure(self, index_file):
        # California uses different XML tags
        pass

    def parse_section(self, section_file):
        # California sections have different structure
        pass


# Usage in pipeline scripts
def get_parser(jurisdiction: str) -> BaseParser:
    """Factory function to get appropriate parser."""
    if jurisdiction == "dc":
        return DCParser(jurisdiction)
    elif jurisdiction == "ca":
        return CaliforniaParser(jurisdiction)
    else:
        raise ValueError(f"Unknown jurisdiction: {jurisdiction}")

# In 10_parse_xml.py
parser = get_parser(args.jurisdiction)
sections = []
for section_file in section_files:
    section = parser.parse_section(section_file)
    sections.append(section)
```

**Benefits**:
- No code duplication when adding new jurisdictions
- Jurisdiction-specific logic is isolated
- Easy to test individual parsers
- Clear extension point for new legal codes

---

## 📋 Project Maintenance

### Ongoing Tasks

- [ ] **M1** Set up CI/CD (GitHub Actions)
  - Run tests on pull requests
  - Type checking for Next.js
  - Python linting (ruff/black)
- [ ] **M2** Add monitoring/analytics
  - Track search queries
  - Monitor API response times
- [ ] **M3** Documentation
  - API documentation
  - Architecture Decision Records (ADRs)
  - Contributing guide
- [ ] **M4** Error handling
  - Better error messages in UI
  - Error logging/reporting
  - Retry logic for Ollama calls
- [ ] **M5** Testing
  - Unit tests for pipeline scripts
  - Integration tests for loaders
  - E2E tests for web app (Playwright)

---

## Notes

- Keep this file updated as tasks are completed
- Add new tasks as they're discovered
- Track blockers and dependencies
- Each track can work independently within a milestone
- Cross-track dependencies are explicitly marked
