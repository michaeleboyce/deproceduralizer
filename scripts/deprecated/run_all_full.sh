#!/bin/bash
# DEPRECATED: Run all pipeline scripts on full DC Code corpus
#
# ⚠️  WARNING: This script is DEPRECATED and OUTDATED
# ⚠️
# ⚠️  This script is missing:
# ⚠️  - Multi-jurisdiction support (--jurisdiction dc)
# ⚠️  - Structure data generation
# ⚠️  - Enhanced LLM obligations
# ⚠️  - Similarity classification
# ⚠️
# ⚠️  Use instead: ./scripts/run-pipeline.sh --corpus=large
# ⚠️  Or use Make: make pipeline-large
#

echo "========================================="
echo "⚠️  DEPRECATED SCRIPT"
echo "========================================="
echo ""
echo "This script is outdated and missing several features."
echo ""
echo "Use instead:"
echo "  ./scripts/run-pipeline.sh --corpus=large"
echo "Or:"
echo "  make pipeline-large"
echo ""
read -p "Continue with deprecated script anyway? (y/N) " -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted. Please use the new scripts."
    exit 0
fi

set -e

echo "========================================="
echo "Running full pipeline on FULL CORPUS"
echo "========================================="
echo ""
echo "WARNING: This will take several hours/days depending on your machine."
echo "All scripts support pause/resume via checkpoints."
echo "Press Ctrl+C to stop at any time; re-run to resume."
echo ""

# Activate virtual environment
source .venv/bin/activate

# Step 1: Parse XML
echo "Step 1/5: Parsing XML sections..."
python pipeline/10_parse_xml.py \
    --src data/raw/dc-law-xml \
    --out data/outputs/sections.ndjson

echo ""
echo "Step 2/5: Extracting cross-references..."
python pipeline/20_crossrefs.py \
    --in data/outputs/sections.ndjson \
    --out data/outputs/refs.ndjson

echo ""
echo "Step 3/5: Extracting obligations (deadlines & amounts)..."
python pipeline/30_regex_obligations.py \
    --in data/outputs/sections.ndjson \
    --deadlines data/outputs/deadlines.ndjson \
    --amounts data/outputs/amounts.ndjson

echo ""
echo "Step 4/5: Computing similar sections (this may take a LONG time)..."
python pipeline/40_similarities.py \
    --in data/outputs/sections.ndjson \
    --out data/outputs/similarities.ndjson \
    --top-k 10 \
    --min-similarity 0.7

echo ""
echo "Step 5/5: Detecting reporting requirements (this may take a LONG time)..."
python pipeline/50_llm_reporting.py \
    --in data/outputs/sections.ndjson \
    --out data/outputs/reporting.ndjson

echo ""
echo "========================================="
echo "✓ Full pipeline complete!"
echo "========================================="
echo ""
echo "Output files:"
ls -lh data/outputs/*.ndjson
echo ""
echo "Next step: Load data to database with:"
echo "  make db-load-full"
