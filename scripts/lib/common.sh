#!/bin/bash
# Common utilities and validation functions for pipeline scripts

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

#===============================================================================
# VALIDATION FUNCTIONS
#===============================================================================

validate_corpus() {
    local corpus=$1
    case "$corpus" in
        small|small_plus|medium|large) return 0 ;;
        *)
            echo -e "${RED}ERROR: Invalid corpus '$corpus'${NC}" >&2
            echo "Valid options: small, small_plus, medium, large" >&2
            echo "" >&2
            echo "Corpus definitions:" >&2
            echo "  small      - Titles 1-2 (~100 sections)" >&2
            echo "  small_plus - Titles 1-4 (~200 sections)" >&2
            echo "  medium     - Titles 1-7 (~350-400 sections)" >&2
            echo "  large      - All DC Code (~50 titles)" >&2
            echo "" >&2
            echo "Usage: $0 --corpus={small|small_plus|medium|large} [OPTIONS]" >&2
            exit 1
            ;;
    esac
}

validate_steps() {
    local steps=$1
    local max_steps=6

    # Parse step range/list (e.g., "1-3" or "1,3,5" or "all")
    if [[ "$steps" == "all" ]]; then
        return 0
    elif [[ "$steps" =~ ^[0-9]+-[0-9]+$ ]]; then
        # Range format
        local start=$(echo "$steps" | cut -d'-' -f1)
        local end=$(echo "$steps" | cut -d'-' -f2)
        if [[ $start -lt 1 || $end -gt $max_steps || $start -gt $end ]]; then
            echo -e "${RED}ERROR: Invalid step range '$steps'${NC}" >&2
            echo "Valid steps: 1-$max_steps" >&2
            list_available_steps
            exit 1
        fi
    elif [[ "$steps" =~ ^[0-9,]+$ ]]; then
        # Comma-separated format
        IFS=',' read -ra step_array <<< "$steps"
        for step in "${step_array[@]}"; do
            if [[ $step -lt 1 || $step -gt $max_steps ]]; then
                echo -e "${RED}ERROR: Invalid step number '$step'${NC}" >&2
                echo "Valid steps: 1-$max_steps" >&2
                list_available_steps
                exit 1
            fi
        done
    else
        echo -e "${RED}ERROR: Invalid step format '$steps'${NC}" >&2
        echo "Valid formats:" >&2
        echo "  'all'       - All steps (default)" >&2
        echo "  '1-3'       - Range of steps" >&2
        echo "  '1,3,5'     - Specific steps" >&2
        list_available_steps
        exit 1
    fi
}

validate_tables() {
    local tables=$1
    local valid_tables="sections structure refs obligations similarities reporting classifications anachronisms"

    if [[ "$tables" == "all" ]]; then
        return 0
    fi

    IFS=',' read -ra table_array <<< "$tables"
    for table in "${table_array[@]}"; do
        if [[ ! " $valid_tables " =~ " $table " ]]; then
            echo -e "${RED}ERROR: Invalid table name '$table'${NC}" >&2
            echo "Valid tables: $valid_tables" >&2
            echo "  or use: all" >&2
            exit 1
        fi
    done
}

validate_environment() {
    local mode=$1  # "pipeline" or "db"

    # Check if we're in project root
    if [[ ! -f "PROJECT_TODO.md" ]]; then
        echo -e "${RED}ERROR: Must run from project root directory${NC}" >&2
        echo "Current directory: $(pwd)" >&2
        exit 1
    fi

    # Check venv
    if [[ ! -d ".venv" ]]; then
        echo -e "${RED}ERROR: Python virtual environment not found at .venv/${NC}" >&2
        echo "Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r pipeline/requirements.txt" >&2
        exit 1
    fi

    # Check .env
    if [[ ! -f ".env" ]]; then
        echo -e "${RED}ERROR: .env file not found${NC}" >&2
        echo "Required environment variables: DATABASE_URL" >&2
        echo "Run: cp .env.example .env (then edit with your DATABASE_URL)" >&2
        exit 1
    fi

    # Source .env
    set -a
    source .env
    set +a

    # Validate DATABASE_URL if loading to DB
    if [[ "$mode" == "db" && -z "$DATABASE_URL" ]]; then
        echo -e "${RED}ERROR: DATABASE_URL not set in .env${NC}" >&2
        exit 1
    fi
}

validate_source_directory() {
    local corpus=$1
    local source_dir

    case "$corpus" in
        small) source_dir="data/subsets" ;;
        small_plus) source_dir="data/subsets_small_plus" ;;
        medium) source_dir="data/subsets_medium" ;;
        large) source_dir="data/raw/dc-law-xml/us/dc/council/code/titles" ;;
    esac

    if [[ ! -d "$source_dir" ]]; then
        echo -e "${RED}ERROR: Source directory not found: $source_dir${NC}" >&2
        case "$corpus" in
            small)
                echo "Run first: ./scripts/make_subset.sh" >&2
                ;;
            small_plus)
                echo "Run first: ./scripts/make_subset_small_plus.sh" >&2
                ;;
            medium)
                echo "Run first: ./scripts/make_subset_medium.sh" >&2
                ;;
            large)
                echo "Run first: git clone https://github.com/DCCouncil/law-xml.git data/raw/dc-law-xml" >&2
                ;;
        esac
        exit 1
    fi
}

check_ollama() {
    local warn_only=$1  # If set, only warn, don't fail

    if ! command -v ollama &> /dev/null; then
        echo -e "${YELLOW}WARNING: Ollama not found (required for LLM steps 5-6)${NC}" >&2
        echo "Install from: https://ollama.ai" >&2
        if [[ -z "$warn_only" ]]; then
            exit 1
        fi
        return 1
    fi

    if ! ollama list &> /dev/null 2>&1; then
        echo -e "${YELLOW}WARNING: Ollama not running (required for LLM steps 5-6)${NC}" >&2
        echo "Start with: ollama serve" >&2
        if [[ -z "$warn_only" ]]; then
            exit 1
        fi
        return 1
    fi

    return 0
}

validate_output_file() {
    local file=$1
    local description=$2

    if [[ ! -f "$file" ]]; then
        echo -e "${RED}ERROR: Output file not created: $file${NC}" >&2
        echo "Step failed: $description" >&2
        exit 1
    fi

    if [[ ! -s "$file" ]]; then
        echo -e "${RED}ERROR: Output file is empty: $file${NC}" >&2
        echo "Step failed: $description" >&2
        exit 1
    fi
}

#===============================================================================
# DISPLAY FUNCTIONS
#===============================================================================

list_available_steps() {
    echo "" >&2
    echo "Available steps:" >&2
    echo "  1: Parse XML sections" >&2
    echo "  2: Extract cross-references" >&2
    echo "  3: Extract obligations (LLM-based)" >&2
    echo "  4: Compute similarities" >&2
    echo "  5: Detect reporting requirements (LLM)" >&2
    echo "  6: Classify similarity relationships (LLM)" >&2
}

progress_bar() {
    local current=$1
    local total=$2
    local width=50

    if [[ $total -eq 0 ]]; then
        return
    fi

    local percent=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))

    printf "\r["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "] %3d%% (%d/%d)" "$percent" "$current" "$total"
}

log_step() {
    local step_num=$1
    local total_steps=$2
    local description=$3
    local status=$4  # DONE, IN_PROGRESS, PENDING, SKIP

    local symbol color
    case "$status" in
        DONE)
            symbol="✓"
            color="$GREEN"
            ;;
        IN_PROGRESS)
            symbol="⏳"
            color="$BLUE"
            ;;
        PENDING)
            symbol=" "
            color="$NC"
            ;;
        SKIP)
            symbol="⊘"
            color="$YELLOW"
            ;;
    esac

    printf "${color}%s Step %d/%d: %-45s${NC}" "$symbol" "$step_num" "$total_steps" "$description"
}

log_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    local title=$1
    echo ""
    echo "========================================"
    echo "$title"
    echo "========================================"
    echo ""
}

print_summary() {
    local corpus=$1
    local source_dir=$2
    local output_pattern=$3

    echo "Corpus: $corpus"
    echo "Source: $source_dir"
    echo "Output: $output_pattern"
    echo ""
}

#===============================================================================
# STATE MANAGEMENT
#===============================================================================

check_for_checkpoints() {
    local corpus=$1
    local pattern="data/outputs/*_${corpus}.ndjson"

    # Check for existing output files
    local existing_files=$(ls $pattern 2>/dev/null | wc -l)

    if [[ $existing_files -gt 0 ]]; then
        return 0  # Checkpoints found
    else
        return 1  # No checkpoints
    fi
}

prompt_resume_or_clean() {
    echo ""
    echo "========================================"
    echo "RESUMABLE CHECKPOINTS DETECTED"
    echo "========================================"
    echo ""
    echo "Found existing output files from previous run."
    echo ""
    echo "Options:"
    echo "  [r] Resume from last checkpoint (default)"
    echo "  [c] Clean start (delete all checkpoints)"
    echo "  [q] Quit"
    echo ""
    read -p "Choice (r/c/q): " -n 1 -r
    echo ""

    case "$REPLY" in
        c|C)
            return 2  # Clean
            ;;
        q|Q)
            echo "Aborted."
            exit 0
            ;;
        r|R|"")
            return 1  # Resume
            ;;
        *)
            echo "Invalid choice. Defaulting to resume."
            return 1  # Resume
            ;;
    esac
}

clean_checkpoints() {
    local corpus=$1

    log_info "Cleaning checkpoints for $corpus corpus..."

    # Clean corpus-specific output files
    rm -f data/outputs/*_${corpus}.ndjson
    rm -f data/outputs/*_${corpus}.ndjson.state
    rm -f data/interim/*_${corpus}.state
    rm -f data/interim/*_${corpus}.ckpt

    # Clean ALL pipeline state/checkpoint files (they're not corpus-specific)
    rm -f data/interim/*.state
    rm -f data/interim/*.ckpt

    log_success "Checkpoints cleaned"
}

#===============================================================================
# TIME TRACKING
#===============================================================================

format_duration() {
    local seconds=$1

    if [[ $seconds -lt 60 ]]; then
        echo "${seconds}s"
    elif [[ $seconds -lt 3600 ]]; then
        local mins=$((seconds / 60))
        local secs=$((seconds % 60))
        echo "${mins}m ${secs}s"
    else
        local hours=$((seconds / 3600))
        local mins=$(((seconds % 3600) / 60))
        echo "${hours}h ${mins}m"
    fi
}

#===============================================================================
# CORPUS CONFIGURATION
#===============================================================================

get_source_dir() {
    local corpus=$1
    case "$corpus" in
        small) echo "data/subsets" ;;
        small_plus) echo "data/subsets_small_plus" ;;
        medium) echo "data/subsets_medium" ;;
        large) echo "data/raw/dc-law-xml/us/dc/council/code/titles" ;;
    esac
}

get_output_suffix() {
    local corpus=$1
    echo "_${corpus}"
}
