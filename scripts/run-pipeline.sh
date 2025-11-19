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

Usage: $0 --corpus={small|medium|large} [OPTIONS]

Required Arguments:
  --corpus=CORPUS        Corpus size to process
                         small  - Titles 1-2 (~100 sections, ~20-30 min)
                         medium - Titles 1-10 (~500-600 sections, ~5-6 hours)
                         large  - All DC Code (~50 titles, ~days)

Optional Arguments:
  --steps=STEPS          Steps to run (default: all)
                         Examples: 'all', '1-3', '1,3,5'
  --clean                Clean start (remove checkpoints)
  --parallel             Enable parallel LLM execution for faster processing
  --help                 Show this help message

Pipeline Steps:
  1. Parse XML sections
  2. Extract cross-references
  3. Extract obligations (LLM-based)
  4. Compute similarities (embeddings)
  5. Detect reporting requirements (LLM)
  6. Classify similarity relationships (LLM)
  7. Detect anachronisms (LLM)

Examples:
  # Run full pipeline on small corpus
  $0 --corpus=small

  # Run specific steps on medium corpus
  $0 --corpus=medium --steps=1-3

  # Clean start on large corpus with parallel execution
  $0 --corpus=large --clean --parallel

  # Run only LLM steps with parallel execution
  $0 --corpus=small --steps=3,5,6,7 --parallel

Notes:
  - Steps 3, 5, 6, 7 require Ollama (LLM)
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
PARALLEL=false

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
        --parallel)
            PARALLEL=true
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

# Export parallel execution flag if enabled
if [[ "$PARALLEL" == true ]]; then
    export LLM_PARALLEL_EXECUTION=true
    log_info "Parallel LLM execution enabled"
else
    export LLM_PARALLEL_EXECUTION=false
fi

#===============================================================================
# PARSE STEP RANGE
#===============================================================================

parse_steps() {
    local steps=$1

    if [[ "$steps" == "all" ]]; then
        echo "1 2 3 4 5 6 7"
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
