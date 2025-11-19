#!/bin/bash
# Pipeline step definitions

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

#===============================================================================
# STEP 1: Parse XML Sections
#===============================================================================

run_step_1_parse_xml() {
    local corpus=$1
    local start_time=$(date +%s)

    log_step 1 7 "Parse XML sections" "IN_PROGRESS"
    echo ""

    local source_dir=$(get_source_dir "$corpus")
    local suffix=$(get_output_suffix "$corpus")
    local output_file="data/outputs/sections${suffix}.ndjson"
    local structure_file="data/outputs/structure${suffix}.ndjson"

    python pipeline/10_parse_xml.py \
        --jurisdiction dc \
        --src "$source_dir" \
        --out "$output_file" || {
        log_error "XML parsing failed"
        exit 1
    }

    # Validate outputs
    validate_output_file "$output_file" "Parse XML sections"
    validate_output_file "$structure_file" "Parse XML structure"

    local section_count=$(wc -l < "$output_file" | tr -d ' ')
    local structure_count=$(wc -l < "$structure_file" | tr -d ' ')
    local duration=$(($(date +%s) - start_time))

    log_step 1 7 "Parse XML sections" "DONE"
    echo " [$(format_duration $duration) - $section_count sections, $structure_count structure nodes]"
}

#===============================================================================
# STEP 2: Extract Cross-References
#===============================================================================

run_step_2_extract_refs() {
    local corpus=$1
    local start_time=$(date +%s)

    log_step 2 7 "Extract cross-references" "IN_PROGRESS"
    echo ""

    local suffix=$(get_output_suffix "$corpus")
    local input_file="data/outputs/sections${suffix}.ndjson"
    local output_file="data/outputs/refs${suffix}.ndjson"

    # Validate input exists
    if [[ ! -f "$input_file" ]]; then
        log_error "Input file not found: $input_file"
        echo "Run step 1 first: Parse XML sections"
        exit 1
    fi

    python pipeline/20_crossrefs.py \
        --in "$input_file" \
        --out "$output_file" || {
        log_error "Cross-reference extraction failed"
        exit 1
    }

    validate_output_file "$output_file" "Extract cross-references"

    local ref_count=$(wc -l < "$output_file" | tr -d ' ')
    local duration=$(($(date +%s) - start_time))

    log_step 2 7 "Extract cross-references" "DONE"
    echo " [$(format_duration $duration) - $ref_count references]"
}

#===============================================================================
# STEP 3: Extract Obligations (LLM-based)
#===============================================================================

run_step_3_extract_obligations() {
    local corpus=$1
    local start_time=$(date +%s)

    log_step 3 7 "Extract obligations (LLM)" "IN_PROGRESS"
    echo ""

    # Check Ollama
    if ! check_ollama "warn"; then
        log_warning "Ollama not available. Falling back to regex-based extraction..."

        local suffix=$(get_output_suffix "$corpus")
        local input_file="data/outputs/sections${suffix}.ndjson"
        local deadlines_file="data/outputs/deadlines${suffix}.ndjson"
        local amounts_file="data/outputs/amounts${suffix}.ndjson"

        python pipeline/30_regex_obligations.py \
            --in "$input_file" \
            --deadlines "$deadlines_file" \
            --amounts "$amounts_file" || {
            log_error "Regex obligation extraction failed"
            exit 1
        }

        validate_output_file "$deadlines_file" "Extract deadlines"
        validate_output_file "$amounts_file" "Extract amounts"

        local deadline_count=$(wc -l < "$deadlines_file" | tr -d ' ')
        local amount_count=$(wc -l < "$amounts_file" | tr -d ' ')
        local duration=$(($(date +%s) - start_time))

        log_step 3 7 "Extract obligations (regex)" "DONE"
        echo " [$(format_duration $duration) - $deadline_count deadlines, $amount_count amounts]"
        return 0
    fi

    # LLM-based extraction
    local suffix=$(get_output_suffix "$corpus")
    local input_file="data/outputs/sections${suffix}.ndjson"
    local output_file="data/outputs/obligations_enhanced${suffix}.ndjson"

    python pipeline/35_llm_obligations.py \
        --in "$input_file" \
        --out "$output_file" || {
        log_error "LLM obligation extraction failed"
        exit 1
    }

    validate_output_file "$output_file" "Extract obligations"

    local obligation_count=$(wc -l < "$output_file" | tr -d ' ')
    local duration=$(($(date +%s) - start_time))

    log_step 3 7 "Extract obligations (LLM)" "DONE"
    echo " [$(format_duration $duration) - $obligation_count obligations]"
}

#===============================================================================
# STEP 4: Compute Similarities
#===============================================================================

run_step_4_compute_similarities() {
    local corpus=$1
    local start_time=$(date +%s)

    log_step 4 7 "Compute similarities" "IN_PROGRESS"
    echo ""
    log_info "This step computes embeddings and may take several minutes..."

    local suffix=$(get_output_suffix "$corpus")
    local input_file="data/outputs/sections${suffix}.ndjson"
    local output_file="data/outputs/similarities${suffix}.ndjson"

    # Validate input exists
    if [[ ! -f "$input_file" ]]; then
        log_error "Input file not found: $input_file"
        echo "Run step 1 first: Parse XML sections"
        exit 1
    fi

    python pipeline/40_similarities.py \
        --in "$input_file" \
        --out "$output_file" \
        --top-k 10 \
        --min-similarity 0.7 || {
        log_error "Similarity computation failed"
        exit 1
    }

    validate_output_file "$output_file" "Compute similarities"

    local similarity_count=$(wc -l < "$output_file" | tr -d ' ')
    local duration=$(($(date +%s) - start_time))

    log_step 4 7 "Compute similarities" "DONE"
    echo " [$(format_duration $duration) - $similarity_count pairs]"
}

#===============================================================================
# STEP 5: Detect Reporting Requirements (LLM)
#===============================================================================

run_step_5_detect_reporting() {
    local corpus=$1
    local start_time=$(date +%s)

    log_step 5 7 "Detect reporting (LLM)" "IN_PROGRESS"
    echo ""
    log_info "This step uses LLM and may take 10-20 minutes..."

    # Check Ollama
    check_ollama || {
        log_error "Ollama is required for reporting detection"
        exit 1
    }

    local suffix=$(get_output_suffix "$corpus")
    local input_file="data/outputs/sections${suffix}.ndjson"
    local output_file="data/outputs/reporting${suffix}.ndjson"

    # Validate input exists
    if [[ ! -f "$input_file" ]]; then
        log_error "Input file not found: $input_file"
        echo "Run step 1 first: Parse XML sections"
        exit 1
    fi

    python pipeline/50_llm_reporting.py \
        --in "$input_file" \
        --out "$output_file" || {
        log_error "Reporting detection failed"
        exit 1
    }

    validate_output_file "$output_file" "Detect reporting"

    local reporting_count=$(wc -l < "$output_file" | tr -d ' ')
    local duration=$(($(date +%s) - start_time))

    log_step 5 7 "Detect reporting (LLM)" "DONE"
    echo " [$(format_duration $duration) - $reporting_count sections analyzed]"
}

#===============================================================================
# STEP 6: Classify Similarity Relationships (LLM)
#===============================================================================

run_step_6_classify_similarities() {
    local corpus=$1
    local start_time=$(date +%s)

    log_step 6 7 "Classify similarities (LLM)" "IN_PROGRESS"
    echo ""
    log_info "This step uses LLM and may take 15-30 minutes..."

    # Check Ollama
    check_ollama || {
        log_error "Ollama is required for similarity classification"
        exit 1
    }

    local suffix=$(get_output_suffix "$corpus")
    local similarities_file="data/outputs/similarities${suffix}.ndjson"
    local sections_file="data/outputs/sections${suffix}.ndjson"
    local output_file="data/outputs/similarity_classifications${suffix}.ndjson"

    # Validate inputs exist
    if [[ ! -f "$similarities_file" ]]; then
        log_error "Input file not found: $similarities_file"
        echo "Run step 4 first: Compute similarities"
        exit 1
    fi

    if [[ ! -f "$sections_file" ]]; then
        log_error "Input file not found: $sections_file"
        echo "Run step 1 first: Parse XML sections"
        exit 1
    fi

    python pipeline/55_similarity_classification.py \
        --similarities "$similarities_file" \
        --sections "$sections_file" \
        --out "$output_file" || {
        log_error "Similarity classification failed"
        exit 1
    }

    validate_output_file "$output_file" "Classify similarities"

    local classification_count=$(wc -l < "$output_file" | tr -d ' ')
    local duration=$(($(date +%s) - start_time))

    log_step 6 7 "Classify similarities (LLM)" "DONE"
    echo " [$(format_duration $duration) - $classification_count classifications]"
}

#===============================================================================
# STEP 7: Detect Anachronisms (LLM)
#===============================================================================

run_step_7_detect_anachronisms() {
    local corpus=$1
    local start_time=$(date +%s)

    log_step 7 7 "Detect anachronisms (LLM)" "IN_PROGRESS"
    echo ""
    log_info "This step analyzes flagged sections for anachronistic language..."

    # Check Ollama
    check_ollama || {
        log_error "Ollama is required for anachronism detection"
        exit 1
    }

    local suffix=$(get_output_suffix "$corpus")
    local sections_file="data/outputs/sections${suffix}.ndjson"
    local obligations_file="data/outputs/obligations_enhanced${suffix}.ndjson"
    local reporting_file="data/outputs/reporting${suffix}.ndjson"
    local output_file="data/outputs/anachronisms${suffix}.ndjson"

    # Validate inputs exist
    if [[ ! -f "$sections_file" ]]; then
        log_error "Input file not found: $sections_file"
        echo "Run step 1 first: Parse XML sections"
        exit 1
    fi

    if [[ ! -f "$obligations_file" ]]; then
        log_warning "Obligations file not found: $obligations_file"
        log_warning "Anachronism detection works best with obligations data from step 3"
    fi

    if [[ ! -f "$reporting_file" ]]; then
        log_warning "Reporting file not found: $reporting_file"
        log_warning "Anachronism detection works best with reporting data from step 5"
    fi

    python pipeline/60_llm_anachronisms.py \
        --sections "$sections_file" \
        --obligations "$obligations_file" \
        --reporting "$reporting_file" \
        --out "$output_file" || {
        log_error "Anachronism detection failed"
        exit 1
    }

    validate_output_file "$output_file" "Detect anachronisms"

    local anachronism_count=$(wc -l < "$output_file" | tr -d ' ')
    local duration=$(($(date +%s) - start_time))

    log_step 7 7 "Detect anachronisms (LLM)" "DONE"
    echo " [$(format_duration $duration) - $anachronism_count sections analyzed]"
}

#===============================================================================
# STEP DISPATCHER
#===============================================================================

run_pipeline_step() {
    local step_num=$1
    local corpus=$2

    case "$step_num" in
        1) run_step_1_parse_xml "$corpus" ;;
        2) run_step_2_extract_refs "$corpus" ;;
        3) run_step_3_extract_obligations "$corpus" ;;
        4) run_step_4_compute_similarities "$corpus" ;;
        5) run_step_5_detect_reporting "$corpus" ;;
        6) run_step_6_classify_similarities "$corpus" ;;
        7) run_step_7_detect_anachronisms "$corpus" ;;
        *)
            log_error "Invalid step number: $step_num"
            exit 1
            ;;
    esac
}
