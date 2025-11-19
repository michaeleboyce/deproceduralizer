#!/bin/bash
# Create a small-plus subset of DC Code XML files for testing
# Copies first 50 sections from Titles 1-4
# Target: ~200 sections (2x small corpus size)

set -e

SOURCE_DIR="data/raw/dc-law-xml/us/dc/council/code/titles"
DEST_DIR="data/subsets_small_plus"

echo "Creating SMALL-PLUS subset of DC Code XML files (Titles 1-4)..."

# Check if source exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory $SOURCE_DIR not found"
    echo "Clone it with: git clone https://github.com/DCCouncil/law-xml.git data/raw/dc-law-xml"
    exit 1
fi

# Create destination directory
mkdir -p "$DEST_DIR"

# Remove any existing subset files
rm -f "$DEST_DIR"/*.xml

echo "Copying first 50 sections from each of Titles 1-4..."

# Copy first 50 sections from each title
for i in {1..4}; do
    echo "  Copying Title $i..."
    find "$SOURCE_DIR/$i/sections" -name "*.xml" -type f | sort | head -50 | while read file; do
        cp "$file" "$DEST_DIR/"
    done
done

# Also copy the title index files for hierarchy information
for i in {1..4}; do
    if [ -f "$SOURCE_DIR/$i/index.xml" ]; then
        cp "$SOURCE_DIR/$i/index.xml" "$DEST_DIR/title-$i-index.xml"
    fi
done

COUNT=$(find "$DEST_DIR" -name "*.xml" -type f ! -name "*-index.xml" | wc -l | tr -d ' ')
INDEX_COUNT=$(find "$DEST_DIR" -name "*-index.xml" -type f | wc -l | tr -d ' ')

echo ""
echo "✓ Copied $COUNT section XML files to $DEST_DIR"
echo "✓ Also copied $INDEX_COUNT title index files for hierarchy information"
echo ""
echo "Next step: Run the pipeline with:"
echo "  ./scripts/run-pipeline.sh --corpus=small_plus"
echo ""
echo "Estimated runtime: ~30-45 minutes (2x small corpus)"
