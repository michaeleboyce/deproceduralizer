#!/bin/bash
# Create a medium subset of DC Code XML files for scale testing
# Copies ALL sections from Titles 1-10 (not limited like small subset)

set -e

SOURCE_DIR="data/raw/dc-law-xml/us/dc/council/code/titles"
DEST_DIR="data/subsets_medium"

echo "Creating MEDIUM subset of DC Code XML files (Titles 1-10)..."

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

echo "Copying ALL sections from Titles 1-10..."

# Copy all sections from Titles 1-10
for i in {1..10}; do
    TITLE_DIR="$SOURCE_DIR/$i/sections"

    if [ -d "$TITLE_DIR" ]; then
        echo "  Copying Title $i sections..."
        find "$TITLE_DIR" -name "*.xml" -type f | while read file; do
            cp "$file" "$DEST_DIR/"
        done

        # Also copy the title index file for hierarchy information
        if [ -f "$SOURCE_DIR/$i/index.xml" ]; then
            cp "$SOURCE_DIR/$i/index.xml" "$DEST_DIR/title-$i-index.xml"
        fi
    else
        echo "  Warning: Title $i directory not found at $TITLE_DIR"
    fi
done

COUNT=$(find "$DEST_DIR" -name "*.xml" -type f ! -name "*-index.xml" | wc -l | tr -d ' ')
INDEX_COUNT=$(find "$DEST_DIR" -name "*-index.xml" -type f | wc -l | tr -d ' ')

echo ""
echo "✓ Copied $COUNT section XML files to $DEST_DIR"
echo "✓ Also copied $INDEX_COUNT title index files for hierarchy information"
echo ""
echo "Next step: Run the pipeline with:"
echo "  ./scripts/run_all_medium.sh"
echo ""
echo "Estimated runtime: ~5-6 hours"
