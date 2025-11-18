# Deproceduralizer Development TODO

Track development progress across all three parallel tracks (A: Pipeline, B: Database, C: Web). Update this file as tasks are completed.

**Legend**:
- [ ] Not started
- [~] In progress
- [x] Completed
- **BLOCKS** - This task blocks another task
- **REQUIRES** - This task requires another task to be completed first

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
**Status**: ⚪ Not Started

### Track A: LLM Reporting Detection

- [ ] **A5.1** Implement `pipeline/50_llm_reporting.py` (REQUIRES: A0.5, A1.2, BLOCKS: B5.1)
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
- [ ] **A5.2** Run reporting detection
  ```bash
  python pipeline/50_llm_reporting.py \
    --in data/outputs/sections_subset.ndjson \
    --out data/outputs/reporting_subset.ndjson
  ```

**Acceptance**: ✅ `reporting_subset.ndjson` exists

---

### Track B: Load Reporting Data

- [ ] **B5.1** Implement `dbtools/load_reporting.py` (REQUIRES: A5.2)
  - Read `reporting_subset.ndjson`
  - UPDATE `dc_sections` SET has_reporting, reporting_summary, reporting_tags
  - INSERT tags into `dc_global_tags` (ON CONFLICT DO NOTHING)
  - INSERT section-tag pairs into `dc_section_tags`
  - Store `highlight_phrases` in new table `dc_section_highlights(section_id, phrase)` if needed
  - .state for resume
- [ ] **B5.2** Add highlights table if needed
  ```sql
  CREATE TABLE IF NOT EXISTS dc_section_highlights (
    id bigserial PRIMARY KEY,
    section_id text REFERENCES dc_sections(id),
    phrase text NOT NULL
  );
  ```
- [ ] **B5.3** Run loader
  ```bash
  python dbtools/load_reporting.py --input data/outputs/reporting_subset.ndjson
  ```

**Acceptance**: ✅ Reporting metadata in database

---

### Track C: Reporting UI

- [ ] **C5.1** Update `/api/search` to support `hasReporting` filter (REQUIRES: B5.3)
  - Add `WHERE has_reporting = true` when filter enabled
- [ ] **C5.2** Update `/search` page
  - Add "Has reporting requirement" checkbox
  - Test filtering
- [ ] **C5.3** Update `/section/[id]` page (REQUIRES: B5.3)
  - If `has_reporting = true`, show badge and `reporting_summary`
  - Create `apps/web/lib/highlight.ts` utility to highlight phrases
  - Highlight `highlight_phrases` in section text using `<mark>` tags
- [ ] **C5.4** Test reporting highlights
  ```bash
  # Visit a section with reporting requirements
  # Verify summary badge and highlighted phrases
  ```

**Acceptance**: ✅ Can filter for reporting, see highlights on section page

---

## 🌐 Milestone 6: Full DC Code Corpus

**Goal**: Process entire DC Code, deploy to production
**Status**: ⚪ Not Started

### Track A: Full Corpus Processing

- [ ] **A6.1** Create `scripts/run_all_subset.sh`
  - Runs all pipeline scripts on subset data sequentially
  - Checks for errors after each step
- [ ] **A6.2** Create `scripts/run_all_full.sh`
  - Runs all pipeline scripts on full `data/raw/dc-law-xml/`
  - Same as subset but points to full data
- [ ] **A6.3** Run full corpus pipeline
  ```bash
  ./scripts/run_all_full.sh
  # This will take hours/days depending on machine
  # All scripts resume from checkpoints if interrupted
  ```
- [ ] **A6.4** Verify all full NDJSON files exist
  ```bash
  ls -lh data/outputs/*.ndjson
  ```

**Acceptance**: ✅ All full corpus NDJSON files generated

---

### Track B: Load Full Corpus

- [ ] **B6.1** Run all loaders on full data
  ```bash
  python dbtools/load_sections.py --input data/outputs/sections.ndjson
  python dbtools/load_refs.py --input data/outputs/refs.ndjson
  python dbtools/load_deadlines_amounts.py \
    --deadlines data/outputs/deadlines.ndjson \
    --amounts data/outputs/amounts.ndjson
  python dbtools/load_similarities.py --input data/outputs/similarities.ndjson
  python dbtools/load_reporting.py --input data/outputs/reporting.ndjson
  ```
- [ ] **B6.2** Verify full corpus loaded
  ```bash
  psql $DATABASE_URL -c "SELECT COUNT(*) FROM dc_sections;"
  # Should be full DC Code section count (thousands)
  ```
- [ ] **B6.3** Analyze database size and performance
  ```sql
  SELECT pg_size_pretty(pg_total_relation_size('dc_sections'));
  ANALYZE dc_sections;  -- Update query planner statistics
  ```

**Acceptance**: ✅ Full corpus in database

---

### Track C: Production Optimizations

- [x] **C6.1** Add pagination to `/search` (limit/offset) *(completed in Milestone 2)*
  - Pagination implemented in both API and UI
  - Search API supports page/limit parameters
  - UI has Previous/Next buttons and page count display
- [ ] **C6.2** Add caching for common queries
  - Consider React Query or SWR
- [ ] **C6.3** Optimize database queries
  - Add indexes if slow queries identified
  - Use EXPLAIN ANALYZE to check query plans
- [x] **C6.4** Create landing page (`apps/web/app/page.tsx`) *(completed early in Milestone 1)*
  - Project description
  - Quick search box (redirects to `/search`)
  - Feature highlights
  - Stats (total sections, titles, etc.)
- [ ] **C6.5** Deploy to Vercel
  ```bash
  cd apps/web
  vercel --prod
  ```
- [ ] **C6.6** Test production deployment
  - Verify search works
  - Check loading performance
  - Test on mobile

**Acceptance**: ✅ Full DC Code searchable in production

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
