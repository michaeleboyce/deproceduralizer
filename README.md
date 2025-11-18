# Deproceduralizer

Transform the DC Code (Washington DC legal code) from procedural XML into a searchable, analyzable database with semantic search, cross-references, and intelligent reporting detection.

## Project Structure

```
deproceduralizer/
├─ apps/web/          # Next.js application (Track C)
├─ pipeline/          # Python processing scripts (Track A)
├─ dbtools/           # Database loaders (Track B)
├─ data/              # All data files (gitignored)
│  ├─ raw/            # DC XML source
│  ├─ subsets/        # Small test datasets
│  ├─ interim/        # Processing state files
│  └─ outputs/        # NDJSON output files
└─ scripts/           # Shell utilities
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node 20+ / PNPM
- Ollama with `nomic-embed-text` and `phi3.5` models
- Neon account (for Postgres database)
- Git

### Initial Setup

1. **Clone and configure**
   ```bash
   git clone <repo-url>
   cd deproceduralizer
   cp .env.example .env
   # Edit .env with your DATABASE_URL and other settings
   ```

2. **Bootstrap all tracks**
   ```bash
   make bootstrap
   ```

## Track-Specific Quick Starts

### Track A: Pipeline (Python)

**Goal**: Parse DC Code XML and extract structured data

```bash
# Set up Python environment
make pipeline-setup

# Or manually:
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r pipeline/requirements.txt

# Clone DC Law XML
git clone https://github.com/DCCouncil/law-xml.git data/raw/dc-law-xml

# Test with a subset
./scripts/make_subset.sh
python pipeline/10_parse_xml.py --src data/subsets --out data/outputs/sections_subset.ndjson
```

**Key Scripts**:
- `10_parse_xml.py` - Parse XML to sections
- `20_crossrefs.py` - Extract cross-references
- `30_regex_obligations.py` - Find deadlines and dollar amounts
- `40_similarities.py` - Compute similar sections (uses Ollama)
- `50_llm_reporting.py` - Detect reporting requirements (uses Ollama)

### Track B: Database & Loaders (Python + SQL)

**Goal**: Load processed data into Neon Postgres

```bash
# Create database tables
make db-create

# Or manually:
psql $DATABASE_URL -f dbtools/create_tables.sql

# Load data (after Track A produces NDJSON files)
python dbtools/load_sections.py --input data/outputs/sections_subset.ndjson
python dbtools/load_refs.py --input data/outputs/refs_subset.ndjson
# ... etc
```

**Key Tools**:
- `create_tables.sql` - Full database schema
- `load_sections.py` - Load sections with resume capability
- `load_refs.py` - Load cross-references
- `load_deadlines_amounts.py` - Load extracted obligations
- `load_similarities.py` - Load similarity scores
- `load_reporting.py` - Load reporting metadata

### Track C: Web Application (Next.js + Drizzle)

**Goal**: Build searchable web interface

```bash
cd apps/web

# Install dependencies
pnpm install

# Configure database (copy from root .env)
cp ../../.env.example .env.local
# Edit .env.local with your DATABASE_URL

# Start development server
pnpm dev
```

**Access**: http://localhost:3000

**Key Routes**:
- `/` - Landing page
- `/search` - Search interface with filters
- `/section/[id]` - Section detail with cross-refs, similar sections, etc.

**Key Files**:
- `lib/db.ts` - Drizzle database connection
- `db/schema.ts` - Drizzle schema
- `app/api/search/route.ts` - Search API (Postgres FTS)

## Development Workflow

### Working with Subsets

For rapid development, work with small subsets of the DC Code:

```bash
# Create a subset (1-2 titles)
./scripts/make_subset.sh

# Run full pipeline on subset
./scripts/run_all_subset.sh

# This creates:
# - data/outputs/sections_subset.ndjson
# - data/outputs/refs_subset.ndjson
# - data/outputs/deadlines_subset.ndjson
# - data/outputs/amounts_subset.ndjson
# - data/outputs/similarities_subset.ndjson
# - data/outputs/reporting_subset.ndjson
```

### Working with Full Corpus

When ready to process the entire DC Code:

```bash
./scripts/run_all_full.sh
```

All pipeline scripts support:
- **Progress bars** (`tqdm`)
- **Pause/resume** (`.state` and `.ckpt` files)
- **Incremental processing** (batched, line-by-line NDJSON)

## Milestones

See `PROJECT_TODO.md` for detailed task tracking across all three tracks.

**High-level milestones**:
1. ✅ Environment ready (you are here)
2. Minimal subset searchable
3. Enhanced search with filters
4. Cross-references and obligations
5. Semantic similarity
6. Reporting detection
7. Full corpus deployment

## Common Commands (Makefile)

```bash
make bootstrap          # Set up all tracks from scratch
make pipeline-setup     # Set up Python environment
make pipeline-subset    # Run pipeline on subset
make pipeline-full      # Run pipeline on full corpus
make db-create          # Create database tables
make db-load-subset     # Load subset data
make web-dev            # Start web dev server
```

## Data Contracts

See `CONTRACTS.md` for NDJSON schema specifications between tracks.

## Technology Stack

- **Pipeline**: Python 3.11+, Ollama (nomic-embed-text, phi3.5), FAISS
- **Database**: Neon Postgres, Drizzle ORM
- **Web**: Next.js 14+, TypeScript, Tailwind CSS, App Router
- **Search**: Postgres Full-Text Search (FTS)

## Contributing

Each track can work independently:
- **Track A** produces NDJSON files
- **Track B** consumes NDJSON and populates database
- **Track C** reads from database

See `PROJECT_TODO.md` for current tasks and dependencies.
