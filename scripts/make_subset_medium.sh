#!/bin/bash
# Create a medium subset of DC Code XML files for scale testing
# Copies ALL sections from Titles 1-7 with proper directory structure

set -e

SOURCE_DIR="data/raw/dc-law-xml/us/dc/council/code/titles"
DEST_DIR="data/subsets_medium"

echo "Creating MEDIUM subset of DC Code XML files (Titles 1-7)..."

# Check if source exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory $SOURCE_DIR not found"
    echo "Clone it with: git clone https://github.com/DCCouncil/law-xml.git data/raw/dc-law-xml"
    exit 1
fi

# Remove and recreate destination directory
rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

echo "Copying ALL sections from Titles 1-7 with directory structure..."

# Copy all sections from Titles 1-7 preserving directory structure
for i in {1..7}; do
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

        # Copy all section files preserving directory structure
        if [ -d "$TITLE_SOURCE/sections" ]; then
            mkdir -p "$TITLE_DEST/sections"
            cp -r "$TITLE_SOURCE/sections/"* "$TITLE_DEST/sections/" 2>/dev/null || true
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
echo "  ./scripts/run_all_medium.sh"
echo ""
echo "Estimated runtime: ~5-6 hours"
