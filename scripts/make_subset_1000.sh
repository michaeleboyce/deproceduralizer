#!/bin/bash
# Create a ~1000-section subset of DC Code XML files for testing.
# Copies the first 200 sections from Titles 1-5, preserving directory structure.

set -e

SOURCE_DIR="data/raw/dc-law-xml/us/dc/council/code/titles"
DEST_DIR="data/subsets_1000"
SECTIONS_PER_TITLE=200
START_TITLE=1
END_TITLE=5

echo "Creating ~1000-section subset of DC Code XML files (Titles ${START_TITLE}-${END_TITLE}, ${SECTIONS_PER_TITLE} sections each)..."

# Check if source exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory $SOURCE_DIR not found"
    echo "Clone it with: git clone https://github.com/DCCouncil/law-xml.git data/raw/dc-law-xml"
    exit 1
fi

# Remove and recreate destination directory
rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

echo "Copying sections..."

for i in $(seq $START_TITLE $END_TITLE); do
    TITLE_SOURCE="$SOURCE_DIR/$i"
    TITLE_DEST="$DEST_DIR/$i"

    if [ -d "$TITLE_SOURCE" ]; then
        echo "  Copying Title $i..."

        mkdir -p "$TITLE_DEST"

        # Copy index.xml if it exists
        if [ -f "$TITLE_SOURCE/index.xml" ]; then
            cp "$TITLE_SOURCE/index.xml" "$TITLE_DEST/"
        fi

        # Copy first N section files
        if [ -d "$TITLE_SOURCE/sections" ]; then
            mkdir -p "$TITLE_DEST/sections"
            find "$TITLE_SOURCE/sections" -name "*.xml" -type f | sort | head -"$SECTIONS_PER_TITLE" | while read file; do
                cp "$file" "$TITLE_DEST/sections/"
            done
        else
            echo "  Warning: No sections directory for Title $i at $TITLE_SOURCE"
        fi
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
echo "  ./scripts/run-pipeline.sh --corpus=1000"
echo ""
