#!/bin/bash
# Main pipeline orchestrator
# Runs DC Code processing pipeline with progress tracking and error handling

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/pipeline-steps.sh"

#===============================================================================
# HELP
#===============================================================================

show_help() {
    cat << EOF
DC Code Pipeline Runner

Usage: $0 --corpus={small|small_plus|medium|1000|large} [OPTIONS]

Required Arguments:
  --corpus=CORPUS        Corpus size to process
                         small      - Titles 1-2 (~100 sections, ~20-30 min)
                         small_plus - Titles 1-4 (~200 sections, ~30-45 min)
                         medium     - Titles 1-7 (~600 sections, ~5-6 hours)
                         1000       - Titles 1-5 (first 200 sections each, ~1000 sections)
                         large      - All DC Code (~50 titles, ~days)

Optional Arguments:
  --steps=STEPS          Steps to run (default: all)
                         Examples: 'all', '1-3', '1,3,5'
  --clean                Clean start (remove checkpoints)
  --workers=N            Process N sections concurrently (default: 1, recommended: 4-8)
  --cascade-strategy=S   LLM cascade strategy (default: auto-select based on workers)
                         error_driven  - Try until error, reactive failure handling
                         rate_limited  - Sequential with preemptive rate limiting
  --check-all-sections   Check all sections for reporting (bypass cross-encoder filter)
                         Default: use semantic pre-filter (40-60% fewer LLM calls)
  --help                 Show this help message

Pipeline Steps:
  1. Parse XML sections
  2. Extract cross-references
  3. Extract obligations (regex-based, fast & free)
  4. Compute similarities (embeddings)
  5. Detect reporting requirements (LLM)
  6. Classify similarity relationships (LLM)
  7. Detect anachronisms (LLM)
  8. Pahlka implementation analysis (LLM)

Examples:
  # Run full pipeline on small corpus
  $0 --corpus=small

  # Run with 8 concurrent workers (much faster)
  $0 --corpus=medium --workers=8

  # Clean start with 8 workers
  $0 --corpus=medium --workers=8 --clean

  # Run only LLM steps with 4 workers
  $0 --corpus=small --steps=5,6,7 --workers=4

  # Use error-driven cascade with 4 workers
  $0 --corpus=medium --workers=4 --cascade-strategy=error_driven

Notes:
  - Step 3 uses fast regex extraction (no LLM required)
  - Steps 5, 6, 7 require Ollama (LLM)
  - Step 4 requires embeddings (Ollama nomic-embed-text)
  - All steps support checkpoint/resume
  - Use --clean to start fresh and remove checkpoints

EOF
}

#===============================================================================
# PARSE ARGUMENTS
#===============================================================================

CORPUS=""
STEPS="all"
CLEAN=false
WORKERS=1
CASCADE_STRATEGY=""
CHECK_ALL_SECTIONS=false

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
        --clean)
            CLEAN=true
            shift
            ;;
        --workers=*)
            WORKERS="${1#*=}"
            shift
            ;;
        --cascade-strategy=*)
            CASCADE_STRATEGY="${1#*=}"
            shift
            ;;
        --check-all-sections)
            CHECK_ALL_SECTIONS=true
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
validate_steps "$STEPS"

#===============================================================================
# VALIDATE ENVIRONMENT
#===============================================================================

validate_environment "pipeline"
validate_source_directory "$CORPUS"

# Activate virtual environment
source .venv/bin/activate

# Validate and export worker count
if ! [[ "$WORKERS" =~ ^[0-9]+$ ]] || [[ "$WORKERS" -lt 1 ]]; then
    echo -e "${RED}ERROR: --workers must be a positive integer${NC}" >&2
    exit 1
fi

export PIPELINE_WORKERS=$WORKERS
if [[ "$WORKERS" -gt 1 ]]; then
    log_info "Data parallelization enabled: $WORKERS concurrent workers"
fi

# Validate and export cascade strategy
if [[ -n "$CASCADE_STRATEGY" ]]; then
    if [[ "$CASCADE_STRATEGY" != "error_driven" && "$CASCADE_STRATEGY" != "rate_limited" ]]; then
        echo -e "${RED}ERROR: --cascade-strategy must be 'error_driven' or 'rate_limited'${NC}" >&2
        exit 1
    fi
    export LLM_CASCADE_STRATEGY=$CASCADE_STRATEGY
    log_info "LLM cascade strategy: $CASCADE_STRATEGY"
fi

# Export check-all-sections flag
export CHECK_ALL_SECTIONS=$CHECK_ALL_SECTIONS
if [[ "$CHECK_ALL_SECTIONS" == "true" ]]; then
    log_info "Cross-encoder filter DISABLED - checking all sections for reporting"
fi

#===============================================================================
# PARSE STEP RANGE
#===============================================================================

parse_steps() {
    local steps=$1

    if [[ "$steps" == "all" ]]; then
        echo "1 2 3 4 5 6 7 8"
        return
    fi

    if [[ "$steps" =~ ^[0-9]+-[0-9]+$ ]]; then
        # Range format (e.g., "1-3")
        local start=$(echo "$steps" | cut -d'-' -f1)
        local end=$(echo "$steps" | cut -d'-' -f2)
        seq $start $end | tr '\n' ' '
        echo ""
    elif [[ "$steps" =~ ^[0-9,]+$ ]]; then
        # Comma-separated format (e.g., "1,3,5")
        echo "$steps" | tr ',' ' '
        echo ""
    fi
}

#===============================================================================
# HANDLE CHECKPOINTS
#===============================================================================

# Parse steps first to check if starting from step 1
STEP_LIST=$(parse_steps "$STEPS")
FIRST_STEP=$(echo $STEP_LIST | awk '{print $1}')

if [[ "$CLEAN" == true ]]; then
    # Warn if cleaning but not starting from step 1
    if [[ "$FIRST_STEP" != "1" ]]; then
        echo ""
        log_warning "Clean start requested, but not starting from step 1"
        echo "Step $FIRST_STEP requires output from previous steps that will be deleted."
        echo ""
        echo "Consider running: $0 --corpus=$CORPUS --steps=1-$FIRST_STEP --clean"
        echo ""
        # Only prompt if stdin is a terminal (not piped/redirected)
        if [[ -t 0 ]]; then
            read -p "Continue anyway? (y/N) " -r </dev/tty
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Aborted."
                exit 0
            fi
        else
            echo "Non-interactive mode - aborting for safety."
            exit 1
        fi
    fi
    clean_checkpoints "$CORPUS"
elif check_for_checkpoints "$CORPUS"; then
    set +e
    prompt_resume_or_clean
    RESUME_CHOICE=$?
    set -e
    
    case $RESUME_CHOICE in
        2)
            # Same warning for interactive clean
            if [[ "$FIRST_STEP" != "1" ]]; then
                echo ""
                log_warning "Clean start requested, but not starting from step 1"
                echo "Step $FIRST_STEP requires output from previous steps that will be deleted."
                echo ""
                echo "Consider running: $0 --corpus=$CORPUS --steps=1-$FIRST_STEP"
                echo ""
                # Read directly from terminal to avoid stdin buffering issues
                if [[ -t 0 ]]; then
                    read -p "Continue anyway? (y/N) " -r </dev/tty
                    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                        echo "Aborted."
                        exit 0
                    fi
                else
                    echo "Non-interactive mode - aborting for safety."
                    exit 1
                fi
            fi
            clean_checkpoints "$CORPUS"
            ;;
        1) log_info "Resuming from checkpoints..." ;;
    esac
fi

#===============================================================================
# DISPLAY PLAN
#===============================================================================

print_header "DC CODE PIPELINE: $(echo $CORPUS | tr '[:lower:]' '[:upper:]') CORPUS"

print_summary \
    "$CORPUS" \
    "$(get_source_dir "$CORPUS")" \
    "data/outputs/*$(get_output_suffix "$CORPUS").ndjson"

echo "Steps to run: $STEP_LIST"
echo ""

# Count steps
TOTAL_STEPS=$(echo $STEP_LIST | wc -w | tr -d ' ')
echo "Total steps: $TOTAL_STEPS"
echo ""

#===============================================================================
# RUN PIPELINE
#===============================================================================

PIPELINE_START_TIME=$(date +%s)

echo "Starting pipeline..."
echo ""

CURRENT_STEP=0
for step in $STEP_LIST; do
    CURRENT_STEP=$((CURRENT_STEP + 1))
    run_pipeline_step "$step" "$CORPUS"
    echo ""
done

#===============================================================================
# FINAL SUMMARY
#===============================================================================

PIPELINE_DURATION=$(($(date +%s) - PIPELINE_START_TIME))

print_header "PIPELINE COMPLETE"

echo "Corpus: $CORPUS"
echo "Steps completed: $TOTAL_STEPS"
echo "Total time: $(format_duration $PIPELINE_DURATION)"
echo ""

echo "Output files:"
ls -lh data/outputs/*$(get_output_suffix "$CORPUS").ndjson 2>/dev/null || echo "No output files found"
echo ""

echo "Next step: Load data to database with:"
echo "  ./scripts/load-database.sh --corpus=$CORPUS"
echo ""
