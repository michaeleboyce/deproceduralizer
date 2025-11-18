#!/bin/bash
# Create a subset of DC Code XML files for testing
# Copies sections from Title 1 and Title 2

set -e

SOURCE_DIR="data/raw/dc-law-xml/us/dc/council/code/titles"
DEST_DIR="data/subsets"

echo "Creating subset of DC Code XML files..."

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

echo "Copying subset from Title 1 and Title 2..."

# Copy first 50 sections from Title 1
find "$SOURCE_DIR/1/sections" -name "*.xml" -type f | sort | head -50 | while read file; do
    cp "$file" "$DEST_DIR/"
done

# Copy first 50 sections from Title 2
find "$SOURCE_DIR/2/sections" -name "*.xml" -type f | sort | head -50 | while read file; do
    cp "$file" "$DEST_DIR/"
done

# Also copy the title index files for hierarchy information
cp "$SOURCE_DIR/1/index.xml" "$DEST_DIR/title-1-index.xml"
cp "$SOURCE_DIR/2/index.xml" "$DEST_DIR/title-2-index.xml"

COUNT=$(find "$DEST_DIR" -name "*.xml" -type f ! -name "*-index.xml" | wc -l | tr -d ' ')
echo "✓ Copied $COUNT section XML files to $DEST_DIR"
echo "✓ Also copied 2 title index files for hierarchy information"
echo ""
echo "Next step: Run the parser with:"
echo "  source .venv/bin/activate"
echo "  python pipeline/10_parse_xml.py --src data/subsets --out data/outputs/sections_subset.ndjson"
