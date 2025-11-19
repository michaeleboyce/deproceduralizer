#!/bin/bash
# DEPRECATED: Run all pipeline scripts on MEDIUM subset data (Titles 1-10)
#
# ⚠️  WARNING: This script is DEPRECATED and OUTDATED
# ⚠️
# ⚠️  This script is missing:
# ⚠️  - Multi-jurisdiction support (--jurisdiction dc)
# ⚠️  - Structure data generation
# ⚠️  - Correct CLI flags for similarity classification
# ⚠️
# ⚠️  Use instead: ./scripts/run-pipeline.sh --corpus=medium
# ⚠️  Or use Make: make pipeline-medium
#

echo "========================================="
echo "⚠️  DEPRECATED SCRIPT"
echo "========================================="
echo ""
echo "This script is outdated and missing several features."
echo ""
echo "Use instead:"
echo "  ./scripts/run-pipeline.sh --corpus=medium"
echo "Or:"
echo "  make pipeline-medium"
echo ""
read -p "Continue with deprecated script anyway? (y/N) " -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted. Please use the new scripts."
    exit 0
fi

set -e

echo "========================================="
echo "Running full pipeline on MEDIUM data"
echo "========================================="
echo ""
echo "Processing Titles 1-10 (~500-600 sections)"
echo "Estimated runtime: 5-6 hours"
echo ""

# Activate virtual environment
source .venv/bin/activate

# Step 1: Parse XML
echo "Step 1/6: Parsing XML sections..."
python pipeline/10_parse_xml.py \
    --src data/subsets_medium \
    --out data/outputs/sections_medium.ndjson

echo ""
echo "Step 2/6: Extracting cross-references..."
python pipeline/20_crossrefs.py \
    --in data/outputs/sections_medium.ndjson \
    --out data/outputs/refs_medium.ndjson

echo ""
echo "Step 3/6: Extracting obligations (deadlines & amounts)..."
python pipeline/30_regex_obligations.py \
    --in data/outputs/sections_medium.ndjson \
    --deadlines data/outputs/deadlines_medium.ndjson \
    --amounts data/outputs/amounts_medium.ndjson

echo ""
echo "Step 4/6: Computing similar sections (this will take a while)..."
python pipeline/40_similarities.py \
    --in data/outputs/sections_medium.ndjson \
    --out data/outputs/similarities_medium.ndjson \
    --top-k 10 \
    --min-similarity 0.7

echo ""
echo "Step 5/6: Classifying similarity relationships (this will take a while - LLM calls)..."
python pipeline/55_similarity_classification.py \
    --similarities data/outputs/similarities_medium.ndjson \
    --sections data/outputs/sections_medium.ndjson \
    --out data/outputs/similarity_classifications_medium.ndjson

echo ""
echo "Step 6/6: Detecting reporting requirements (this will take a while - LLM calls)..."
python pipeline/50_llm_reporting.py \
    --in data/outputs/sections_medium.ndjson \
    --out data/outputs/reporting_medium.ndjson

echo ""
echo "========================================="
echo "✓ Pipeline complete!"
echo "========================================="
echo ""
echo "Output files:"
ls -lh data/outputs/*_medium.ndjson
echo ""
echo "Next step: Load data to database with:"
echo "  ./scripts/load_db_medium.sh"
