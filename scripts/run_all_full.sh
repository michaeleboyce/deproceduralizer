#!/bin/bash
# Run all pipeline scripts on full DC Code corpus

set -e

echo "========================================="
echo "Running full pipeline on FULL CORPUS"
echo "========================================="
echo ""
echo "WARNING: This will take several hours/days depending on your machine."
echo "All scripts support pause/resume via checkpoints."
echo "Press Ctrl+C to stop at any time; re-run to resume."
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

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
