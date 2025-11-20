#!/bin/bash
# Database loading orchestrator
# Loads processed pipeline data into Postgres database

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/db-loaders.sh"

#===============================================================================
# HELP
#===============================================================================

show_help() {
    cat << EOF
DC Code Database Loader

Usage: $0 --corpus={small|medium|large} [OPTIONS]

Required Arguments:
  --corpus=CORPUS        Corpus size to load
                         small  - Titles 1-2 (~100 sections)
                         medium - Titles 1-10 (~500-600 sections)
                         large  - All DC Code (~50 titles)

Optional Arguments:
  --tables=TABLES        Tables to load (default: all)
                         Examples: 'all', 'sections,structure,refs'
  --help                 Show this help message

Available Tables:
  sections               Section text and metadata
  structure              Hierarchical structure (titles, chapters, etc.)
  refs                   Cross-references between sections
  obligations            Deadlines and dollar amounts
  similarities           Similar section pairs
  reporting              Reporting requirements
  classifications        Similarity relationship classifications
  anachronisms           Anachronistic language detection
  pahlka_implementation  Implementation complexity analysis (Pahlka framework)

Examples:
  # Load all tables for small corpus
  $0 --corpus=small

  # Load specific tables for medium corpus
  $0 --corpus=medium --tables=sections,structure,refs

  # Load only sections
  $0 --corpus=large --tables=sections

Notes:
  - Requires DATABASE_URL in .env file
  - All loaders use UPSERT (ON CONFLICT DO UPDATE)
  - Safe to re-run; will update existing records
  - Loaders support checkpoint/resume

EOF
}

#===============================================================================
# PARSE ARGUMENTS
#===============================================================================

CORPUS=""
TABLES="all"

while [[ $# -gt 0 ]]; do
    case $1 in
        --corpus=*)
            CORPUS="${1#*=}"
            shift
            ;;
        --tables=*)
            TABLES="${1#*=}"
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR: Unknown option '$1'${NC}" >&2
            echo "Run with --help for usage" >&2
            exit 1
            ;;
    esac
done

#===============================================================================
# VALIDATE ARGUMENTS
#===============================================================================

if [[ -z "$CORPUS" ]]; then
    echo -e "${RED}ERROR: --corpus is required${NC}" >&2
    echo "" >&2
    show_help
    exit 1
fi

validate_corpus "$CORPUS"
validate_tables "$TABLES"

#===============================================================================
# VALIDATE ENVIRONMENT
#===============================================================================

validate_environment "db"

# Activate virtual environment
source .venv/bin/activate

#===============================================================================
# PARSE TABLE LIST
#===============================================================================

parse_tables() {
    local tables=$1

    if [[ "$tables" == "all" ]]; then
        echo "sections structure refs obligations similarities reporting classifications anachronisms"
        return
    fi

    echo "$tables" | tr ',' ' '
}

TABLE_LIST=$(parse_tables "$TABLES")

#===============================================================================
# DISPLAY PLAN
#===============================================================================

print_header "DATABASE LOADER: $(echo $CORPUS | tr '[:lower:]' '[:upper:]') CORPUS"

echo "Corpus: $corpus"
echo "Database: ${DATABASE_URL%%\?*}"  # Hide query params
echo "Tables to load: $TABLE_LIST"
echo ""

# Count tables
TOTAL_TABLES=$(echo $TABLE_LIST | wc -w | tr -d ' ')
echo "Total tables: $TOTAL_TABLES"
echo ""

#===============================================================================
# LOAD DATABASE
#===============================================================================

LOAD_START_TIME=$(date +%s)

echo "Starting database loading..."
echo ""

if [[ "$TABLES" == "all" ]]; then
    # Use optimized load_all_tables function
    load_all_tables "$CORPUS" || {
        log_error "Database loading failed"
        exit 1
    }
else
    # Load individual tables
    CURRENT=0
    FAILED=0

    for table in $TABLE_LIST; do
        CURRENT=$((CURRENT + 1))
        echo ""
        echo "[$CURRENT/$TOTAL_TABLES] Loading $table..."
        echo "---"

        if ! load_table "$table" "$CORPUS"; then
            FAILED=$((FAILED + 1))
            log_warning "Failed to load $table (continuing...)"
        fi
    done

    echo ""
    if [[ $FAILED -eq 0 ]]; then
        log_success "All tables loaded successfully"
    else
        log_warning "$FAILED/$TOTAL_TABLES tables failed to load"
        exit 1
    fi
fi

#===============================================================================
# FINAL SUMMARY
#===============================================================================

LOAD_DURATION=$(($(date +%s) - LOAD_START_TIME))

print_header "DATABASE LOADING COMPLETE"

echo "Corpus: $CORPUS"
echo "Tables loaded: $TOTAL_TABLES"
echo "Total time: $(format_duration $LOAD_DURATION)"
echo ""

log_success "Database is ready!"
echo ""
echo "Next step: Start the web app with:"
echo "  cd apps/web && pnpm dev"
echo ""
