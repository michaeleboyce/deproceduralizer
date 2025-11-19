#!/bin/bash
# Clean pipeline checkpoints and state files

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

show_help() {
    cat << EOF
Clean Pipeline State

Usage: $0 [--corpus={small|medium|large}] [--force]

Optional Arguments:
  --corpus=CORPUS        Clean only specific corpus (default: all)
  --force                Skip confirmation prompt
  --help                 Show this help message

Examples:
  # Clean all checkpoints (with confirmation)
  $0

  # Clean only small corpus
  $0 --corpus=small

  # Clean all without confirmation
  $0 --force

EOF
}

CORPUS=""
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --corpus=*)
            CORPUS="${1#*=}"
            validate_corpus "$CORPUS"
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR: Unknown option '$1'${NC}" >&2
            exit 1
            ;;
    esac
done

print_header "CLEAN PIPELINE STATE"

if [[ -n "$CORPUS" ]]; then
    echo "Cleaning checkpoints for: $CORPUS corpus"
else
    echo "Cleaning checkpoints for: ALL corpora"
fi
echo ""

# Find files to delete
if [[ -n "$CORPUS" ]]; then
    FILES=$(find data/outputs data/interim -type f \( -name "*_${CORPUS}.*" -o -name "*_${CORPUS}.ndjson" \) 2>/dev/null)
else
    FILES=$(find data/outputs data/interim -type f \( -name "*.state" -o -name "*.ckpt" -o -name "*_small.*" -o -name "*_medium.*" -o -name "*_large.*" \) 2>/dev/null)
fi

FILE_COUNT=$(echo "$FILES" | grep -v '^$' | wc -l | tr -d ' ')

if [[ $FILE_COUNT -eq 0 ]]; then
    log_info "No checkpoint files found"
    exit 0
fi

echo "Files to delete ($FILE_COUNT):"
echo "$FILES"
echo ""

if [[ "$FORCE" != true ]]; then
    read -p "Delete these files? (y/N) " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

echo ""
log_info "Deleting checkpoint files..."

echo "$FILES" | while read -r file; do
    if [[ -n "$file" ]]; then
        rm -f "$file"
        echo "  Deleted: $file"
    fi
done

echo ""
log_success "Cleaned $FILE_COUNT files"
