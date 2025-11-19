#!/bin/bash
# Full pipeline orchestrator: subset → pipeline → database
# Handles the complete workflow from raw data to loaded database

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

show_help() {
    cat << EOF
Full Pipeline Orchestrator

Usage: $0 --corpus={small|medium|large} [OPTIONS]

Required Arguments:
  --corpus=CORPUS        Corpus size to process
                         small  - Titles 1-2 (~100 sections, ~5-10 min)
                         medium - Titles 1-10 (~500-600 sections, ~30-60 min)
                         large  - All DC Code (~50 titles, several hours)

Optional Arguments:
  --steps=STEPS          Pipeline steps to run (default: all)
                         Examples: '1-3', '5-6', 'all'
  --clean                Clean database and state before starting
  --skip-subset          Skip subset creation (assume already created)
  --skip-load            Skip database loading (only run pipeline)
  --cascade=STRATEGY     LLM cascade strategy: simple or extended (default: extended)
  --help                 Show this help message

Examples:
  # Full workflow for small corpus
  $0 --corpus=small

  # Full workflow for medium corpus with clean start
  $0 --corpus=medium --clean

  # Run only LLM steps for small corpus
  $0 --corpus=small --skip-subset --steps=5-6

  # Run pipeline but don't load to database
  $0 --corpus=large --skip-load

Workflow:
  1. Create subset (if needed)
  2. Run pipeline steps
  3. Load results to database

Notes:
  - Use --clean when switching between corpus sizes
  - Extended cascade uses Groq (faster but uses quota)
  - Simple cascade goes Gemini → Ollama (slower but preserves Groq)

EOF
}

#===============================================================================
# PARSE ARGUMENTS
#===============================================================================

CORPUS=""
STEPS="all"
CLEAN=false
SKIP_SUBSET=false
SKIP_LOAD=false
CASCADE="extended"

while [[ $# -gt 0 ]]; do
    case $1 in
        --corpus=*)
            CORPUS="${1#*=}"
            shift
            ;;
        --steps=*)
            STEPS="${1#*=}"
            shift
            ;;
        --cascade=*)
            CASCADE="${1#*=}"
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --skip-subset)
            SKIP_SUBSET=true
            shift
            ;;
        --skip-load)
            SKIP_LOAD=true
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

if [[ "$CASCADE" != "simple" && "$CASCADE" != "extended" ]]; then
    echo -e "${RED}ERROR: --cascade must be 'simple' or 'extended'${NC}" >&2
    exit 1
fi

#===============================================================================
# DISPLAY PLAN
#===============================================================================

print_header "FULL PIPELINE: $(echo $CORPUS | tr '[:lower:]' '[:upper:]') CORPUS"

echo "Configuration:"
echo "  Corpus: $CORPUS"
echo "  Steps: $STEPS"
echo "  Cascade: $CASCADE"
echo "  Clean before start: $CLEAN"
echo "  Skip subset creation: $SKIP_SUBSET"
echo "  Skip database load: $SKIP_LOAD"
echo ""

# Estimate time
case "$CORPUS" in
    small)
        echo "Estimated time: 5-10 minutes"
        ;;
    medium)
        echo "Estimated time: 30-60 minutes"
        ;;
    large)
        echo "Estimated time: Several hours"
        ;;
esac
echo ""

read -p "Continue? (Y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "Aborted."
    exit 0
fi

PIPELINE_START=$(date +%s)

#===============================================================================
# STEP 1: CLEAN (OPTIONAL)
#===============================================================================

if [[ "$CLEAN" == true ]]; then
    echo ""
    print_header "STEP 1: CLEANING"

    # Clean database
    if command -v python &> /dev/null; then
        log_info "Cleaning database..."
        source .venv/bin/activate
        python dbtools/clean_database.py << EOF
yes
EOF
    else
        log_warning "Python not found, skipping database clean"
    fi

    # Clean state
    log_info "Cleaning pipeline state..."
    ./scripts/clean-state.sh --force

    log_success "Cleanup complete"
fi

#===============================================================================
# STEP 2: CREATE SUBSET
#===============================================================================

if [[ "$SKIP_SUBSET" == false ]]; then
    echo ""
    print_header "STEP 2: CREATE SUBSET"

    case "$CORPUS" in
        small)
            log_info "Creating small subset (Titles 1-2)..."
            ./scripts/make_subset.sh
            ;;
        medium)
            log_info "Creating medium subset (Titles 1-10)..."
            ./scripts/make_subset_medium.sh
            ;;
        large)
            log_info "Using full DC Code (no subset needed)"
            ;;
    esac

    log_success "Subset ready"
else
    echo ""
    log_info "Skipping subset creation (--skip-subset)"
fi

#===============================================================================
# STEP 3: RUN PIPELINE
#===============================================================================

echo ""
print_header "STEP 3: RUN PIPELINE"

log_info "Running pipeline steps: $STEPS"
log_info "Using cascade strategy: $CASCADE"

# Set cascade strategy in environment
export LLM_CASCADE_STRATEGY="$CASCADE"

./scripts/run-pipeline.sh --corpus="$CORPUS" --steps="$STEPS"

log_success "Pipeline complete"

#===============================================================================
# STEP 4: LOAD DATABASE
#===============================================================================

if [[ "$SKIP_LOAD" == false ]]; then
    echo ""
    print_header "STEP 4: LOAD DATABASE"

    log_info "Loading results to database..."
    ./scripts/load-database.sh --corpus="$CORPUS"

    log_success "Database loaded"
else
    echo ""
    log_info "Skipping database load (--skip-load)"
fi

#===============================================================================
# FINAL SUMMARY
#===============================================================================

PIPELINE_DURATION=$(($(date +%s) - PIPELINE_START))

echo ""
print_header "PIPELINE COMPLETE!"

echo "Corpus: $CORPUS"
echo "Total time: $(format_duration $PIPELINE_DURATION)"
echo ""

if [[ "$SKIP_LOAD" == false ]]; then
    log_success "Data is ready in database!"
    echo ""
    echo "Next step: Start the web app with:"
    echo "  cd apps/web && pnpm dev"
else
    log_success "Pipeline output files are ready!"
    echo ""
    echo "Output files: data/outputs/*_${CORPUS}.ndjson"
    echo ""
    echo "To load to database, run:"
    echo "  ./scripts/load-database.sh --corpus=$CORPUS"
fi

echo ""
