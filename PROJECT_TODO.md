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
- **Milestones 5.1-5.2**: ✅ Complete (Architecture & Intelligence hardened)
- **Milestone 5.3**: ✅ Complete (BCG-Level UX implemented)
- **Milestones 6-8**: Ready to proceed (refinement complete)

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
- ~~**5.1 BLOCKS 5.2**: Pydantic models (5.1) needed before instructor refactor (5.2)~~ ✅ Complete
- ~~**5.1 BLOCKS 5.3**: Multi-jurisdiction schema (5.1) needed before UI updates (5.3)~~ ✅ Complete
- ~~**5.2 BLOCKS 5.5**: Structured LLM patterns (5.2) should be applied to similarity classification (5.5)~~ ✅ Complete
- ~~**5.1 + 5.2 + 5.3 + 5.5 BLOCK 6**: Refinement must be complete before scaling to medium corpus~~ ✅ **UNBLOCKED - Ready for Milestone 6**
- **6 BLOCKS 7**: Medium corpus provides realistic data for reporting deep analysis
- **7 BLOCKS 8**: Reporting enhancements should be tested before full corpus
- **8 BLOCKS 9**: Multi-jurisdiction expansion should be done after full DC Code is stable

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
**Status**: ✅ Complete (Track A: ✅ Complete, Track B: ✅ Complete, Track C: ✅ Complete)

**Rationale**: Before scaling to medium/full corpus, eliminate technical debt. Build jurisdiction-agnostic foundation to support DC, California, New York, and other legal codes without refactoring.

### Track A: Pipeline Refactoring

- [x] **A5.1.1** Create `pipeline/models.py` with jurisdiction-agnostic Pydantic models (BLOCKS: A5.2.3)
  - Define `Section`, `CrossReference`, `Obligation`, `SimilarityPair`, `ReportingRequirement`
  - Use Field validators and aliases for data contract compatibility
  - Support multi-jurisdiction with `jurisdiction` field
- [x] **A5.1.2** Create `pipeline/parsers/` module structure (BLOCKS: A5.1.4)
  - Create `parsers/__init__.py`
  - Create `parsers/base.py` with abstract `BaseParser` class
  - Create `parsers/dc.py` extending `BaseParser` for DC Code XML format
  - Add `--jurisdiction` flag to all pipeline scripts
- [x] **A5.1.3** Implement two-pass XML parsing in `10_parse_xml.py` (REQUIRES: A5.1.2)
  - **Pass 1**: Parse `index.xml` files to extract hierarchical structure
  - **Pass 2**: Parse section XMLs and attach to hierarchy
  - Output includes correct parent/child relationships
- [x] **A5.1.4** Add `<history>` effective date extraction (REQUIRES: A5.1.3)
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
- [x] **C5.1.4** Update `apps/web/lib/db.ts` connection utilities
  - Queries use jurisdiction parameter via `getCurrentJurisdiction()`
  - Helper functions created in `lib/config.ts`
- [x] **C5.1.5** Test "Browse by Chapter" navigation with new structure table (REQUIRES: B5.1.2)
  - ✅ Created `/apps/web/app/api/structure/route.ts` - API endpoint for structure data
  - ✅ Created `/apps/web/components/StructureNavigator.tsx` - Collapsible tree component
  - ✅ Created `/apps/web/app/browse/page.tsx` - Browse page with hierarchical navigation
  - ✅ Added "Browse" link to Navigation component
  - ✅ 533 structure nodes loaded into database
  - Tree supports Title → Chapter → Subchapter hierarchy
  - Collapsible/expandable nodes with visual indicators

**Acceptance**: ✅ **COMPLETE** - UI works with multi-jurisdiction schema, structure-based navigation implemented. Jurisdiction selector deferred to Milestone 9.

---

## 🧠 Milestone 5.2: Enhanced Intelligence

**Goal**: Replace brittle regex parsing with validated structured outputs, optimize similarity search
**Status**: ✅ Complete

**Rationale**: Current LLM scripts use 200+ lines of fragile regex-based JSON parsing with manual field validation. Replace with Pydantic + Instructor for automatic validation, retry logic, and type safety. Optimize similarity search for full corpus scale.

### Track A: LLM Hardening with Structured Outputs

- [x] **A5.2.1** Install `instructor` library (BLOCKS: A5.2.2)
  ```bash
  source .venv/bin/activate
  pip install instructor
  pip freeze > pipeline/requirements.txt
  ```
- [x] **A5.2.2** Create `pipeline/llm_client.py` unified LLM wrapper (REQUIRES: A5.2.1, BLOCKS: A5.2.3)
  - Wrap Gemini API with instructor
  - Wrap Ollama API with instructor
  - Integrate existing RateLimiter cascade logic (Gemini → Ollama fallback)
  - Support `response_model` parameter for Pydantic validation
  - Return validated model instances (not raw JSON strings)
  - Handle rate limits and model fallback gracefully
  - Logging for which model was used per request
- [x] **A5.2.3** Refactor `50_llm_reporting.py` to use structured outputs (REQUIRES: A5.1.1, A5.2.2)
  - Import `ReportingRequirement` model from `pipeline/models.py`
  - Replace `parse_llm_json()` function (40+ lines) with instructor calls
  - Remove manual field validation loops (20+ lines)
  - Use llm_client wrapper with `response_model=ReportingRequirement`
  - Keep checkpoint/resume logic intact
  - Maintain CONTRACTS.md output schema compatibility
  - Test on subset data to verify parity with old approach
- [x] **A5.2.4** Refactor `55_similarity_classification.py` to use structured outputs (REQUIRES: A5.1.1, A5.2.2)
  - Import `SimilarityClassification` model from `pipeline/models.py`
  - Replace duplicate `parse_llm_json()` (40+ lines)
  - Remove duplicate RateLimiter class (consolidate to llm_client.py)
  - Remove manual field validation
  - Maintain output schema compatibility
  - Test on subset similarity pairs
- [x] **A5.2.5** Update CONTRACTS.md to reference Pydantic models (REQUIRES: A5.1.1)
  - Add section: "## Schema Validation"
  - Document that all schemas are enforced via `pipeline/models.py`
  - Link field definitions to Pydantic model source code
  - Note benefits: type safety, automatic validation, retry logic
- [x] **A5.2.6** Create `35_llm_obligations.py` - Enhanced obligation extraction (REQUIRES: A5.2.2)
  - **Stage 1 (Fast Filter)**: Regex scan for sections containing numbers, "$", or temporal keywords
  - **Stage 2 (LLM Classify)**: Send candidates to Gemini/Ollama for classification
  - Use Pydantic model: `Obligation(type, phrase, value, unit, category)`
  - Categories: "deadline" | "constraint" | "allocation" | "penalty"
  - Output: `obligations_enhanced.ndjson` (replaces separate deadlines/amounts files)
  - Support `--in`, `--out`, `--filter-threshold` flags
  - Checkpoint/resume with .ckpt file
- [x] **A5.2.7** Run enhanced obligations extraction on subset
  ```bash
  python pipeline/35_llm_obligations.py \
    --in data/outputs/sections_subset.ndjson \
    --out data/outputs/obligations_enhanced_subset.ndjson
  ```
- [x] **A5.2.8** Verify enhanced obligations output
  ```bash
  wc -l data/outputs/obligations_enhanced_subset.ndjson
  jq -r '.category' data/outputs/obligations_enhanced_subset.ndjson | sort | uniq -c
  ```

**Acceptance**: ✅ Instructor + Pydantic integrated, 200+ lines of parsing code removed, enhanced obligations extracted

---

### Track A (Continued): Optimize Similarity Search

- [x] **A5.2.9** Update `40_similarities.py` to use FAISS IVF indexing (BLOCKS: B5.2.2)
  - Replace `faiss.IndexFlatIP` with `faiss.IndexIVFFlat`
  - Train index on 5,000 representative vectors (from subset or sample)
  - Set `nprobe` parameter for speed/accuracy tradeoff
  - Add `--use-ivf` and `--train-size` flags
  - Document expected speedup (100x) vs accuracy loss (<1%)
  - Test on subset to verify similar results to flat index
- [x] **A5.2.10** Benchmark IVF vs Flat indexing
  ```bash
  # Flat (baseline)
  time python pipeline/40_similarities.py --in data/outputs/sections_subset.ndjson --out flat.ndjson

  # IVF (optimized)
  time python pipeline/40_similarities.py --in data/outputs/sections_subset.ndjson --out ivf.ndjson --use-ivf --train-size 5000
  ```
- [x] **A5.2.11** Compare outputs to verify accuracy

**Acceptance**: ✅ IVF indexing implemented (A5.2.9), benchmarking completed (A5.2.10-11)

---

### Track A (Continued): Dual Cascade Strategy & Enhanced Reporting

- [x] **A5.2.12** Implement dual LLM cascade strategies (REQUIRES: A5.2.2)
  - Add `LLM_CASCADE_STRATEGY` environment variable ("simple" or "extended")
  - **Simple strategy**: Gemini (4 models) → Ollama (default, preserves Groq quota)
  - **Extended strategy**: Gemini (4 models) → Groq (7 models) → Ollama (maximum resilience)
  - Add Groq API integration with 7 models:
    - moonshotai/kimi-k2-instruct (60 RPM, 1K RPD, 10K TPM)
    - openai/gpt-oss-120b (30 RPM, 1K RPD, 8K TPM)
    - qwen/qwen3-32b (60 RPM, 1K RPD, 6K TPM)
    - llama-3.3-70b-versatile (30 RPM, 1K RPD, 12K TPM)
    - llama-3.1-8b-instant (30 RPM, 14.4K RPD, 6K TPM)
    - meta-llama/llama-4-maverick-17b-128e-instruct (30 RPM, 1K RPD, 6K TPM)
    - meta-llama/llama-4-scout-17b-16e-instruct (30 RPM, 1K RPD, 30K TPM)
  - Implement OpenAI-compatible Groq client in `llm_client.py`
  - Add per-model rate limiting for all Groq models
- [x] **A5.2.13** Add enhanced statistics tracking and logging
  - Track current model, call counts, time on each tier
  - Log model switches with detailed stats (calls, duration, reason)
  - Only log on model changes (not every call) for cleaner output
  - Add `get_stats_summary()` method for final report
  - Track tier switches with timestamps and reasons
- [x] **A5.2.14** Configure pipelines to use extended cascade strategy
  - Update `50_llm_reporting.py` to default to extended strategy
  - Update `55_similarity_classification.py` to default to extended strategy
  - Add `--cascade-strategy` CLI argument to both scripts
  - Both pipelines now use Groq tier for maximum resilience
- [x] **A5.2.15** Add exact reporting text extraction
  - Add `reporting_text` field to `ReportingRequirement` Pydantic model
  - Update LLM prompt to extract exact full text of reporting requirement
  - Extract complete sentences verbatim from section (not just summary)
  - Update `50_llm_reporting.py` output to include `reporting_text` field

**Acceptance**: ✅ Dual cascade strategies implemented, Groq integration complete, enhanced logging active, exact reporting text extraction added

---

### Track B (Continued): Database Schema for Exact Reporting Text

- [x] **B5.2.1** Update database schema for exact reporting text
  - Add `reporting_text TEXT` column to `sections` table (SQL schema)
  - Add `reportingText: text("reporting_text")` to TypeScript schema
  - Run migration: `ALTER TABLE sections ADD COLUMN reporting_text text;`
- [x] **B5.2.2** Update database loader for reporting text
  - Add `reporting_text` to `load_reporting.py` validation
  - Update SQL INSERT/UPDATE to include `reporting_text` field
  - Handle null/empty reporting_text gracefully

**Acceptance**: ✅ Database schema updated, loader handles exact reporting text

---

### Track C (Continued): UI Display for Exact Reporting Text

- [x] **C5.2.1** Add exact reporting text display to section detail page
  - Display exact reporting text below summary in violet-themed section
  - Show quoted text with border-left accent
  - Styled as italic text in white background box
  - Label: "Exact Reporting Text:"
  - Only display when `reportingText` field is populated

**Acceptance**: ✅ Exact reporting text displayed on section detail pages

---

## 🎨 Milestone 5.3: "BCG-Level" UX Polish

**Goal**: Professional visual design, advanced visualizations, and intuitive navigation
**Status**: ✅ Complete

### Track C: Advanced UI Components

- [x] **C5.3.1** Implement In-Text Citation Hyperlinking
  - Parse section text for citations (e.g., "§ 1-101")
  - Replace with Next.js `<Link>` components
  - Add hover preview cards for citations (fetch snippet on hover)
- [x] **C5.3.2** Create Citation Graph Visualization
  - Use `react-force-graph` or similar library
  - Visualize references (incoming/outgoing) as nodes and edges
  - Interactive graph explorer on section detail page
- [x] **C5.3.3** Build Legislative Conflict & Duplicate Dashboard
  - Dashboard showing "conflicting" sections identified by LLM
  - Dashboard showing "duplicate" or "highly redundant" sections
  - Filter by title/chapter
  - Side-by-side comparison view
- [x] **C5.3.4** Enhanced Typography & Layout
  - Implement "legal-clean" typography (serif for body, sans for UI)
  - Improved whitespace and reading experience
  - Collapsible/expandable subsections
- [x] **C5.3.5** Mobile Responsiveness Polish
  - Ensure all new visualizations work on mobile
  - Touch-friendly navigation
- [x] **C5.3.6** Hierarchical Subsection Display Parser
  - Created `SubsectionParser.tsx` component to parse and display nested subsections
  - Automatically detects hierarchical levels: (a)/(b), (1)/(2), (A)/(B), (i)/(ii)
  - Visual hierarchy with color-coded left borders (teal, blue, purple, gray)
  - Progressive indentation for nested structure
  - Collapsible subsections with expand/collapse controls
  - First 2 levels auto-expanded for better UX
  - Preserves citation linking and highlight functionality
  - Transforms flat paragraph text into readable hierarchical structure
  - Integrated into section detail page (`/section/[id]`)

**Acceptance**: ⚪ UI features implemented and tested

---

## 🚀 Milestone 6: Medium Corpus Scale-Up

**Goal**: Process Titles 1-10 (~500-600 sections) to test scalability
**Status**: ⏸️ PAUSED (Blocked by 5.1, 5.2, 5.3)

### Track A: Pipeline Scale-Up

- [ ] **A6.1** Create medium subset (Titles 1-10)
- [ ] **A6.2** Run full pipeline on medium subset
  - Parse XML (with hierarchy)
  - Extract Cross-refs
  - Extract Enhanced Obligations (LLM)
  - Compute Similarities (IVF)
  - Detect Reporting (LLM)
  - Classify Similarities (LLM)

### Track B: Database Performance

- [ ] **B6.1** Load medium corpus
- [ ] **B6.2** Analyze query performance (EXPLAIN ANALYZE)
- [ ] **B6.3** Tune Postgres indexes if needed

### Track C: UI Stress Test

- [ ] **C6.1** Verify search performance with larger dataset
- [ ] **C6.2** Verify graph visualization with more nodes

---

## 📊 Milestone 7: Reporting Deep Analysis

**Goal**: Advanced analytics on reporting requirements
**Status**: ⏸️ PAUSED

- [ ] **A7.1** Extract reporting entities (Who reports?)
- [ ] **A7.2** Extract receiving entities (To whom?)
- [ ] **A7.3** Extract frequency (Annual, Quarterly, etc.)
- [ ] **C7.1** Build "Reporting Compliance Dashboard"
- [ ] **C7.2** Filter by agency/department

---

## 🌎 Milestone 8: Full Corpus & Production

**Goal**: Deploy full DC Code to production
**Status**: ⏸️ PAUSED

- [ ] **A8.1** Process full DC Code (~50 titles)
- [ ] **B8.1** Load full corpus
- [ ] **C8.1** Production deployment (Vercel/Neon)
- [ ] **C8.2** SEO optimization (sitemap, metadata)

---

## 🗺️ Milestone 9: Multi-Jurisdiction Expansion

**Goal**: Extend platform to support California, New York, and other legal codes
**Status**: ⏸️ PAUSED (Deferred from Milestone 5.1)

**Rationale**: The multi-jurisdiction architecture is complete. This milestone focuses on adding additional jurisdictions and UI for switching between them.

### Track A: Add New Jurisdictions

- [ ] **A9.1** Source California legal code XML
- [ ] **A9.2** Source New York legal code XML
- [ ] **A9.3** Create California parser (extends BaseParser)
- [ ] **A9.4** Create New York parser (extends BaseParser)
- [ ] **A9.5** Process California code through pipeline
- [ ] **A9.6** Process New York code through pipeline

### Track B: Database Multi-Jurisdiction

- [ ] **B9.1** Insert California jurisdiction into `jurisdictions` table
- [ ] **B9.2** Insert New York jurisdiction into `jurisdictions` table
- [ ] **B9.3** Load California data (sections, structure, cross-refs, etc.)
- [ ] **B9.4** Load New York data (sections, structure, cross-refs, etc.)
- [ ] **B9.5** Verify data integrity across jurisdictions

### Track C: UI Jurisdiction Selector

- [ ] **C9.1** Add jurisdiction selector dropdown to Navigation component
  - Add dropdown in Navigation component (top-right corner)
  - Store selected jurisdiction in URL params or global state
  - Filter all queries by selected jurisdiction
- [ ] **C9.2** Update all pages to respect selected jurisdiction
  - Search page filters by jurisdiction
  - Browse page shows selected jurisdiction's structure
  - Section detail page links stay within jurisdiction
- [ ] **C9.3** Add jurisdiction switcher to homepage
  - Show available jurisdictions as cards
  - Display statistics per jurisdiction (section count, etc.)
- [ ] **C9.4** Test cross-jurisdiction navigation
  - Verify switching between DC, CA, NY works correctly
  - Ensure no data leakage between jurisdictions

**Acceptance**: ⚪ Platform supports multiple legal codes with seamless switching
