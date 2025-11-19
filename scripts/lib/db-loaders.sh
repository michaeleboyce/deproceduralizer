#!/bin/bash
# Database loader definitions

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

#===============================================================================
# LOADER: Sections
#===============================================================================

load_sections() {
    local corpus=$1
    local start_time=$(date +%s)

    echo "Loading sections..."

    local suffix=$(get_output_suffix "$corpus")
    local input_file="data/outputs/sections${suffix}.ndjson"

    if [[ ! -f "$input_file" ]]; then
        log_error "Input file not found: $input_file"
        echo "Run pipeline step 1 first"
        return 1
    fi

    PYTHONPATH=. python dbtools/load_sections.py \
        --input "$input_file" \
        --jurisdiction dc || {
        log_error "Failed to load sections"
        return 1
    }

    local duration=$(($(date +%s) - start_time))
    log_success "Sections loaded [$(format_duration $duration)]"
    return 0
}

#===============================================================================
# LOADER: Structure
#===============================================================================

load_structure() {
    local corpus=$1
    local start_time=$(date +%s)

    echo "Loading structure..."

    local suffix=$(get_output_suffix "$corpus")
    local input_file="data/outputs/structure${suffix}.ndjson"

    if [[ ! -f "$input_file" ]]; then
        log_error "Input file not found: $input_file"
        echo "Run pipeline step 1 first"
        return 1
    fi

    PYTHONPATH=. python dbtools/load_structure.py \
        --input "$input_file" \
        --jurisdiction dc || {
        log_error "Failed to load structure"
        return 1
    }

    local duration=$(($(date +%s) - start_time))
    log_success "Structure loaded [$(format_duration $duration)]"
    return 0
}

#===============================================================================
# LOADER: Cross-References
#===============================================================================

load_refs() {
    local corpus=$1
    local start_time=$(date +%s)

    echo "Loading cross-references..."

    local suffix=$(get_output_suffix "$corpus")
    local input_file="data/outputs/refs${suffix}.ndjson"

    if [[ ! -f "$input_file" ]]; then
        log_error "Input file not found: $input_file"
        echo "Run pipeline step 2 first"
        return 1
    fi

    PYTHONPATH=. python dbtools/load_refs.py \
        --input "$input_file" || {
        log_error "Failed to load cross-references"
        return 1
    }

    local duration=$(($(date +%s) - start_time))
    log_success "Cross-references loaded [$(format_duration $duration)]"
    return 0
}

#===============================================================================
# LOADER: Obligations
#===============================================================================

load_obligations() {
    local corpus=$1
    local start_time=$(date +%s)

    echo "Loading obligations..."

    local suffix=$(get_output_suffix "$corpus")

    # Check for enhanced obligations first
    local enhanced_file="data/outputs/obligations_enhanced${suffix}.ndjson"
    if [[ -f "$enhanced_file" ]]; then
        log_info "Loading enhanced obligations (LLM-based)"
        PYTHONPATH=. python dbtools/load_obligations_enhanced.py \
            --input "$enhanced_file" || {
            log_error "Failed to load enhanced obligations"
            return 1
        }

        local duration=$(($(date +%s) - start_time))
        log_success "Enhanced obligations loaded [$(format_duration $duration)]"
        return 0
    fi

    # Fall back to regex-based obligations
    local deadlines_file="data/outputs/deadlines${suffix}.ndjson"
    local amounts_file="data/outputs/amounts${suffix}.ndjson"

    if [[ ! -f "$deadlines_file" ]] && [[ ! -f "$amounts_file" ]]; then
        log_error "No obligation files found"
        echo "Run pipeline step 3 first"
        return 1
    fi

    if [[ -f "$deadlines_file" ]] && [[ -f "$amounts_file" ]]; then
        PYTHONPATH=. python dbtools/load_deadlines_amounts.py \
            --deadlines "$deadlines_file" \
            --amounts "$amounts_file" || {
            log_error "Failed to load obligations"
            return 1
        }
    elif [[ -f "$deadlines_file" ]]; then
        PYTHONPATH=. python dbtools/load_deadlines_amounts.py \
            --deadlines "$deadlines_file" || {
            log_error "Failed to load deadlines"
            return 1
        }
    elif [[ -f "$amounts_file" ]]; then
        PYTHONPATH=. python dbtools/load_deadlines_amounts.py \
            --amounts "$amounts_file" || {
            log_error "Failed to load amounts"
            return 1
        }
    fi

    local duration=$(($(date +%s) - start_time))
    log_success "Obligations loaded [$(format_duration $duration)]"
    return 0
}

#===============================================================================
# LOADER: Similarities
#===============================================================================

load_similarities() {
    local corpus=$1
    local start_time=$(date +%s)

    echo "Loading similarities..."

    local suffix=$(get_output_suffix "$corpus")
    local input_file="data/outputs/similarities${suffix}.ndjson"

    if [[ ! -f "$input_file" ]]; then
        log_error "Input file not found: $input_file"
        echo "Run pipeline step 4 first"
        return 1
    fi

    PYTHONPATH=. python dbtools/load_similarities.py \
        --input "$input_file" || {
        log_error "Failed to load similarities"
        return 1
    }

    local duration=$(($(date +%s) - start_time))
    log_success "Similarities loaded [$(format_duration $duration)]"
    return 0
}

#===============================================================================
# LOADER: Reporting
#===============================================================================

load_reporting() {
    local corpus=$1
    local start_time=$(date +%s)

    echo "Loading reporting requirements..."

    local suffix=$(get_output_suffix "$corpus")
    local input_file="data/outputs/reporting${suffix}.ndjson"

    if [[ ! -f "$input_file" ]]; then
        log_error "Input file not found: $input_file"
        echo "Run pipeline step 5 first"
        return 1
    fi

    PYTHONPATH=. python dbtools/load_reporting.py \
        --input "$input_file" || {
        log_error "Failed to load reporting requirements"
        return 1
    }

    local duration=$(($(date +%s) - start_time))
    log_success "Reporting requirements loaded [$(format_duration $duration)]"
    return 0
}

#===============================================================================
# LOADER: Similarity Classifications
#===============================================================================

load_classifications() {
    local corpus=$1
    local start_time=$(date +%s)

    echo "Loading similarity classifications..."

    local suffix=$(get_output_suffix "$corpus")
    local input_file="data/outputs/similarity_classifications${suffix}.ndjson"

    if [[ ! -f "$input_file" ]]; then
        log_error "Input file not found: $input_file"
        echo "Run pipeline step 6 first"
        return 1
    fi

    PYTHONPATH=. python dbtools/load_similarity_classifications.py \
        --input "$input_file" || {
        log_error "Failed to load similarity classifications"
        return 1
    }

    local duration=$(($(date +%s) - start_time))
    log_success "Similarity classifications loaded [$(format_duration $duration)]"
    return 0
}

#===============================================================================
# LOADER: Anachronisms
#===============================================================================

load_anachronisms() {
    local corpus=$1
    local start_time=$(date +%s)

    echo "Loading anachronisms..."

    local suffix=$(get_output_suffix "$corpus")
    local input_file="data/outputs/anachronisms${suffix}.ndjson"

    if [[ ! -f "$input_file" ]]; then
        log_error "Input file not found: $input_file"
        echo "Run pipeline step 7 first"
        return 1
    fi

    PYTHONPATH=. python dbtools/load_anachronisms.py \
        --input "$input_file" || {
        log_error "Failed to load anachronisms"
        return 1
    }

    local duration=$(($(date +%s) - start_time))
    log_success "Anachronisms loaded [$(format_duration $duration)]"
    return 0
}

#===============================================================================
# LOADER DISPATCHER
#===============================================================================

load_table() {
    local table=$1
    local corpus=$2

    case "$table" in
        sections) load_sections "$corpus" ;;
        structure) load_structure "$corpus" ;;
        refs) load_refs "$corpus" ;;
        obligations) load_obligations "$corpus" ;;
        similarities) load_similarities "$corpus" ;;
        reporting) load_reporting "$corpus" ;;
        classifications) load_classifications "$corpus" ;;
        anachronisms) load_anachronisms "$corpus" ;;
        *)
            log_error "Invalid table name: $table"
            return 1
            ;;
    esac
}

#===============================================================================
# LOAD ALL TABLES
#===============================================================================

load_all_tables() {
    local corpus=$1
    local tables="sections structure refs obligations similarities reporting classifications anachronisms"

    local total=8
    local current=0
    local failed=0

    for table in $tables; do
        current=$((current + 1))
        echo ""
        echo "[$current/$total] Loading $table..."
        echo "---"

        if ! load_table "$table" "$corpus"; then
            failed=$((failed + 1))
            log_warning "Failed to load $table (continuing...)"
        fi
    done

    echo ""
    if [[ $failed -eq 0 ]]; then
        log_success "All tables loaded successfully"
        return 0
    else
        log_warning "$failed/$total tables failed to load"
        return 1
    fi
}
