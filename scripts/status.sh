#!/bin/bash
# Show pipeline status and database statistics

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

show_help() {
    cat << EOF
Pipeline Status Checker

Usage: $0 [--corpus={small|medium|large}]

Optional Arguments:
  --corpus=CORPUS        Show status for specific corpus (default: all)
  --help                 Show this help message

Examples:
  # Show status for all corpora
  $0

  # Show status for small corpus only
  $0 --corpus=small

EOF
}

CORPUS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --corpus=*)
            CORPUS="${1#*=}"
            validate_corpus "$CORPUS"
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

show_corpus_status() {
    local corpus=$1
    local suffix=$(get_output_suffix "$corpus")

    echo ""
    echo "=== $corpus Corpus ==="
    echo ""

    # Check output files
    local files=(
        "sections${suffix}.ndjson"
        "structure${suffix}.ndjson"
        "refs${suffix}.ndjson"
        "obligations_enhanced${suffix}.ndjson"
        "similarities${suffix}.ndjson"
        "reporting${suffix}.ndjson"
        "similarity_classifications${suffix}.ndjson"
    )

    local fallback_files=(
        "deadlines${suffix}.ndjson"
        "amounts${suffix}.ndjson"
    )

    echo "Pipeline Output Files:"
    for file in "${files[@]}"; do
        local path="data/outputs/$file"
        if [[ -f "$path" ]]; then
            local size=$(ls -lh "$path" | awk '{print $5}')
            local lines=$(wc -l < "$path" | tr -d ' ')
            printf "  ${GREEN}✓${NC} %-45s %8s  %6s lines\n" "$file" "$size" "$lines"
        else
            printf "  ${YELLOW}✗${NC} %-45s %s\n" "$file" "missing"
        fi
    done

    # Check fallback files
    local has_fallback=false
    for file in "${fallback_files[@]}"; do
        if [[ -f "data/outputs/$file" ]]; then
            has_fallback=true
            break
        fi
    done

    if [[ "$has_fallback" == true ]]; then
        echo ""
        echo "Legacy Obligation Files (regex-based):"
        for file in "${fallback_files[@]}"; do
            local path="data/outputs/$file"
            if [[ -f "$path" ]]; then
                local size=$(ls -lh "$path" | awk '{print $5}')
                local lines=$(wc -l < "$path" | tr -d ' ')
                printf "  ${GREEN}✓${NC} %-45s %8s  %6s lines\n" "$file" "$size" "$lines"
            fi
        done
    fi
}

print_header "PIPELINE STATUS"

if [[ -n "$CORPUS" ]]; then
    show_corpus_status "$CORPUS"
else
    for corpus in small medium large; do
        show_corpus_status "$corpus"
    done
fi

# Database statistics (if .env exists)
if [[ -f ".env" ]]; then
    set -a
    source .env
    set +a

    if [[ -n "$DATABASE_URL" ]] && command -v psql &> /dev/null; then
        echo ""
        echo "=== Database Statistics ==="
        echo ""

        # Try to query database
        if psql "$DATABASE_URL" -c "SELECT 1" &> /dev/null; then
            echo "Section counts by jurisdiction:"
            psql "$DATABASE_URL" -t -c "
                SELECT
                    COALESCE(jurisdiction, 'NULL') as jurisdiction,
                    COUNT(*) as count
                FROM sections
                GROUP BY jurisdiction
                ORDER BY jurisdiction;
            " 2>/dev/null | sed 's/^/  /' || echo "  Unable to query database"

            echo ""
            echo "Table row counts:"
            for table in sections structure section_refs section_similarities section_similarity_classifications; do
                local count=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM $table" 2>/dev/null | tr -d ' ')
                if [[ -n "$count" ]]; then
                    printf "  %-40s %8s rows\n" "$table" "$count"
                fi
            done
        else
            echo "  Unable to connect to database"
        fi
    else
        echo ""
        log_info "psql not available - skipping database statistics"
    fi
fi

echo ""
