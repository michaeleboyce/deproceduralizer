#!/bin/bash
# Run all pipeline scripts on subset data

set -e

echo "========================================="
echo "Running full pipeline on SUBSET data"
echo "========================================="
echo ""

# Activate virtual environment
source .venv/bin/activate

# Step 1: Parse XML
echo "Step 1/5: Parsing XML sections..."
python pipeline/10_parse_xml.py \
    --src data/subsets \
    --out data/outputs/sections_subset.ndjson

echo ""
echo "Step 2/5: Extracting cross-references..."
python pipeline/20_crossrefs.py \
    --in data/outputs/sections_subset.ndjson \
    --out data/outputs/refs_subset.ndjson

echo ""
echo "Step 3/5: Extracting obligations (deadlines & amounts)..."
python pipeline/30_regex_obligations.py \
    --in data/outputs/sections_subset.ndjson \
    --deadlines data/outputs/deadlines_subset.ndjson \
    --amounts data/outputs/amounts_subset.ndjson

echo ""
echo "Step 4/5: Computing similar sections (this may take a while)..."
python pipeline/40_similarities.py \
    --in data/outputs/sections_subset.ndjson \
    --out data/outputs/similarities_subset.ndjson \
    --top-k 10 \
    --min-similarity 0.7

echo ""
echo "Step 5/5: Detecting reporting requirements (this may take a while)..."
python pipeline/50_llm_reporting.py \
    --in data/outputs/sections_subset.ndjson \
    --out data/outputs/reporting_subset.ndjson

echo ""
echo "========================================="
echo "✓ Pipeline complete!"
echo "========================================="
echo ""
echo "Output files:"
ls -lh data/outputs/*_subset.ndjson
echo ""
echo "Next step: Load data to database with:"
echo "  make db-load-subset"
