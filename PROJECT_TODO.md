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
- [ ] **C5.5** Improve overall look/feel/navigation with modern design system
  - Create comprehensive STYLE_GUIDE.md with color palette and design tokens
  - Implement sophisticated slate/teal color palette (replacing basic blues)
  - Add navigation header component with breadcrumbs across all pages
  - Enhance typography hierarchy and spacing consistency
  - Refine component styling (buttons, badges, cards, forms)
  - Update home page with refined hero and CTAs
  - Update search page with cleaner filters and results layout
  - Update section detail page with improved hierarchy
  - Refine diff viewer colors for better readability

**Acceptance**: ✅ **COMPLETE** - Full reporting UI with filters, badges, summaries, tags, and highlighted phrases

---

## 🔍 Milestone 5.5: Similarity Classification Analysis

**Goal**: Use LLM to classify why similar sections are related (duplicate/superseded/related/conflicting), add comprehensive filters
**Status**: ⚪ Not Started

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
**Status**: ⚪ Not Started

**Rationale**: Current subset (Titles 1-2, ~100 sections, ~1 hour) → Medium subset (Titles 1-10, ~500-600 sections, ~5-6 hours) → Full corpus (~50 titles, days). Provides realistic scale testing before full corpus processing.

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
**Status**: ⚪ Not Started

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
