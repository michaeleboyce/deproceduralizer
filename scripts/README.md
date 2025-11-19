# Pipeline Scripts - Quick Reference

This directory contains scripts to process DC Code data through the complete pipeline.

## Quick Start

### Most Common Use Case

```bash
# Process small corpus (fastest, for testing)
./scripts/full-pipeline.sh --corpus=small

# Process medium corpus (recommended for development)
./scripts/full-pipeline.sh --corpus=medium

# Process large corpus (full DC Code, takes hours)
./scripts/full-pipeline.sh --corpus=large
```

### Switching Between Corpus Sizes

```bash
# Clean database and state, then run medium corpus
./scripts/full-pipeline.sh --corpus=medium --clean
```

## Available Scripts

### Main Scripts

| Script | Purpose | Example |
|--------|---------|---------|
| `full-pipeline.sh` | **ONE-STOP SHOP**: Create subset → Run pipeline → Load database | `./scripts/full-pipeline.sh --corpus=medium` |
| `run-pipeline.sh` | Run processing pipeline steps | `./scripts/run-pipeline.sh --corpus=small --steps=1-6` |
| `load-database.sh` | Load pipeline results to database | `./scripts/load-database.sh --corpus=small` |

### Subset Creation Scripts

| Script | Purpose | Output Size |
|--------|---------|-------------|
| `make_subset.sh` | Create small subset (Titles 1-2) | ~100 sections |
| `make_subset_medium.sh` | Create medium subset (Titles 1-10) | ~500-600 sections |

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `clean-state.sh` | Clean pipeline checkpoints and output files |
| `status.sh` | Show pipeline status and output file sizes |

## Common Workflows

### 1. First Time Setup

```bash
# Run small corpus to test everything works
./scripts/full-pipeline.sh --corpus=small
```

### 2. Switching from Small to Medium

```bash
# Clean first to avoid data mixing
./scripts/full-pipeline.sh --corpus=medium --clean
```

### 3. Re-run Just LLM Steps

```bash
# Only run steps 5-6 (reporting + classifications)
./scripts/full-pipeline.sh --corpus=small --skip-subset --steps=5-6
```

### 4. Run Pipeline Without Database Load

```bash
# Generate output files but don't load to database
./scripts/full-pipeline.sh --corpus=medium --skip-load
```

## Pipeline Steps

The pipeline consists of 6 steps:

1. **Parse XML sections** - Extract sections from DC Code XML
2. **Extract cross-references** - Find citations between sections
3. **Extract obligations (LLM)** - Detect deadlines and requirements
4. **Compute similarities** - Find similar sections using embeddings
5. **Detect reporting (LLM)** - Identify reporting requirements
6. **Classify similarity relationships (LLM)** - Categorize relationships

## Corpus Sizes

| Corpus | Titles | Sections | Processing Time | Use Case |
|--------|--------|----------|-----------------|----------|
| **small** | 1-2 | ~100 | 5-10 minutes | Testing, development |
| **medium** | 1-10 | ~500-600 | 30-60 minutes | Development, demos |
| **large** | 1-50 | ~thousands | Several hours | Production |

## LLM Cascade Strategies

### Extended (Default, Recommended)
```bash
./scripts/full-pipeline.sh --corpus=medium --cascade=extended
```
- **Flow**: Gemini (4 models) → Groq (9 models) → Ollama
- **Pros**: Fastest, most resilient
- **Cons**: Uses Groq API quota

### Simple (Preserves Groq Quota)
```bash
./scripts/full-pipeline.sh --corpus=medium --cascade=simple
```
- **Flow**: Gemini (4 models) → Ollama
- **Pros**: Preserves Groq quota
- **Cons**: Slower, less resilient

## Troubleshooting

### "ERROR: DATABASE_URL not set in .env"
Make sure your `.env` file has DATABASE_URL in quotes:
```bash
DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"
```

### Mixed Data in Database
Run with `--clean` to clear database before loading new corpus:
```bash
./scripts/full-pipeline.sh --corpus=medium --clean
```

### Pipeline Runs Too Slow
- Use `--cascade=extended` for faster Groq models
- Or use smaller corpus size for testing

### Rate Limit Errors
The pipeline automatically handles rate limits by:
- Cascading through multiple models
- Waiting 10 minutes before retrying Gemini
- Using checkpoints to resume after interruptions

## Advanced Usage

### Full Pipeline Options

```bash
./scripts/full-pipeline.sh \
  --corpus=medium \           # Corpus size (required)
  --steps=5-6 \              # Only run specific steps
  --cascade=extended \       # LLM cascade strategy
  --clean \                  # Clean database and state first
  --skip-subset \            # Assume subset already created
  --skip-load                # Don't load to database
```

### Run Pipeline with Custom Steps

```bash
# Run only parsing and cross-refs
./scripts/run-pipeline.sh --corpus=small --steps=1-2

# Run only LLM steps
./scripts/run-pipeline.sh --corpus=small --steps=3,5,6

# Run all steps
./scripts/run-pipeline.sh --corpus=medium --steps=all
```

### Load Specific Tables to Database

```bash
# Load only sections and structure
./scripts/load-database.sh --corpus=small --tables=sections,structure

# Load all tables
./scripts/load-database.sh --corpus=medium --tables=all
```

## Files and Directories

```
scripts/
├── full-pipeline.sh          # Main convenience script
├── run-pipeline.sh           # Pipeline orchestrator
├── load-database.sh          # Database loader
├── make_subset.sh            # Create small subset
├── make_subset_medium.sh     # Create medium subset
├── clean-state.sh            # Clean checkpoints
├── status.sh                 # Show status
└── lib/
    ├── common.sh             # Shared utilities
    └── db-loaders.sh         # Database loading functions

data/
├── outputs/                  # Pipeline output files
│   ├── sections_small.ndjson
│   ├── reporting_small.ndjson
│   └── ...
└── interim/                  # Checkpoints and state
    ├── reporting.ckpt
    ├── similarities.state
    └── ...
```

## Getting Help

```bash
# Show help for any script
./scripts/full-pipeline.sh --help
./scripts/run-pipeline.sh --help
./scripts/load-database.sh --help
```

## Next Steps After Pipeline

Once the pipeline completes and data is loaded:

```bash
# Start the web application
cd apps/web
pnpm dev
```

Then open http://localhost:3000
