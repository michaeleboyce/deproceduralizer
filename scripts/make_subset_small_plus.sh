#!/bin/bash
# Create a small-plus subset of DC Code XML files for testing
# Copies first 50 sections from Titles 1-4 with full directory structure
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

# Remove and recreate destination directory
rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

echo "Copying first 50 sections from each of Titles 1-4 with directory structure..."

# Copy first 50 sections from each title, preserving directory structure
for i in {1..4}; do
    TITLE_SOURCE="$SOURCE_DIR/$i"
    TITLE_DEST="$DEST_DIR/$i"

    if [ -d "$TITLE_SOURCE" ]; then
        echo "  Copying Title $i..."

        # Create title directory
        mkdir -p "$TITLE_DEST"

        # Copy index.xml if it exists
        if [ -f "$TITLE_SOURCE/index.xml" ]; then
            cp "$TITLE_SOURCE/index.xml" "$TITLE_DEST/"
        fi

        # Create sections directory
        mkdir -p "$TITLE_DEST/sections"

        # Copy first 50 section files
        find "$TITLE_SOURCE/sections" -name "*.xml" -type f | sort | head -50 | while read file; do
            cp "$file" "$TITLE_DEST/sections/"
        done
    else
        echo "  Warning: Title $i directory not found at $TITLE_SOURCE"
    fi
done

COUNT=$(find "$DEST_DIR" -type f -name "*.xml" ! -name "index.xml" | wc -l | tr -d ' ')
INDEX_COUNT=$(find "$DEST_DIR" -type f -name "index.xml" | wc -l | tr -d ' ')

echo ""
echo "✓ Copied $COUNT section XML files to $DEST_DIR"
echo "✓ Also copied $INDEX_COUNT title index files for hierarchy information"
echo ""
echo "Next step: Run the pipeline with:"
echo "  ./scripts/run-pipeline.sh --corpus=small_plus"
echo ""
echo "Estimated runtime: ~30-45 minutes (2x small corpus)"
