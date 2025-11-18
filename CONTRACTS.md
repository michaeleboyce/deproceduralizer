# Data Contracts Between Tracks

This document defines the NDJSON schemas that each track produces and consumes. All files use newline-delimited JSON (one JSON object per line).

## Track A Output → Track B Input

### sections.ndjson

**Producer**: `pipeline/10_parse_xml.py`
**Consumer**: `dbtools/load_sections.py`
**Location**: `data/outputs/sections.ndjson` or `data/outputs/sections_subset.ndjson`

```json
{
  "id": "dc-1-101",
  "citation": "§ 1-101",
  "heading": "Title and short title",
  "text_plain": "This title may be cited as the 'District of Columbia Code'.",
  "text_html": "<p>This title may be cited as the 'District of Columbia Code'.</p>",
  "ancestors": [
    {"type": "title", "label": "Title 1", "id": "dc-title-1"},
    {"type": "chapter", "label": "Chapter 1", "id": "dc-1-chapter-1"}
  ],
  "title_label": "Title 1",
  "chapter_label": "Chapter 1"
}
```

**Field Specifications**:
- `id` (string, required): Unique section identifier (e.g., "dc-1-101")
- `citation` (string, required): Official citation (e.g., "§ 1-101")
- `heading` (string, required): Section heading/title
- `text_plain` (string, required): Plain text content (no HTML)
- `text_html` (string, required): HTML-formatted content
- `ancestors` (array, required): Hierarchical context (title, subtitle, chapter, etc.)
  - Each ancestor: `{type: string, label: string, id: string}`
- `title_label` (string, required): Title number/name for filtering
- `chapter_label` (string, required): Chapter number/name for filtering

---

### refs.ndjson

**Producer**: `pipeline/20_crossrefs.py`
**Consumer**: `dbtools/load_refs.py`
**Location**: `data/outputs/refs.ndjson` or `data/outputs/refs_subset.ndjson`

```json
{
  "from_id": "dc-1-101",
  "to_id": "dc-1-102",
  "raw_cite": "§ 1-102"
}
```

**Field Specifications**:
- `from_id` (string, required): Source section ID (references `dc_sections.id`)
- `to_id` (string, required): Target section ID (references `dc_sections.id`)
- `raw_cite` (string, required): Original citation text as it appears in source

**Notes**:
- May have multiple rows with same `from_id, to_id` if cited multiple times with different text
- Invalid `to_id` references should be logged but not fail the load

---

### deadlines.ndjson

**Producer**: `pipeline/30_regex_obligations.py`
**Consumer**: `dbtools/load_deadlines_amounts.py`
**Location**: `data/outputs/deadlines.ndjson` or `data/outputs/deadlines_subset.ndjson`

```json
{
  "section_id": "dc-1-101",
  "phrase": "within 30 days",
  "days": 30,
  "kind": "deadline"
}
```

**Field Specifications**:
- `section_id` (string, required): Section containing the deadline
- `phrase` (string, required): Exact text phrase from the section
- `days` (integer, required): Number of days for the deadline
- `kind` (string, required): Type of deadline (e.g., "deadline", "notice_period", "waiting_period")

---

### amounts.ndjson

**Producer**: `pipeline/30_regex_obligations.py`
**Consumer**: `dbtools/load_deadlines_amounts.py`
**Location**: `data/outputs/amounts.ndjson` or `data/outputs/amounts_subset.ndjson`

```json
{
  "section_id": "dc-1-101",
  "phrase": "$1,000 fine",
  "amount_cents": 100000
}
```

**Field Specifications**:
- `section_id` (string, required): Section containing the amount
- `phrase` (string, required): Exact text phrase from the section
- `amount_cents` (integer, required): Amount in cents (e.g., $10.50 = 1050)

**Notes**:
- All amounts stored in cents to avoid floating-point issues
- Negative amounts permitted for credits/refunds

---

### similarities.ndjson

**Producer**: `pipeline/40_similarities.py`
**Consumer**: `dbtools/load_similarities.py`
**Location**: `data/outputs/similarities.ndjson` or `data/outputs/similarities_subset.ndjson`

```json
{
  "section_a": "dc-1-101",
  "section_b": "dc-1-102",
  "similarity": 0.923
}
```

**Field Specifications**:
- `section_a` (string, required): First section ID (alphabetically earlier)
- `section_b` (string, required): Second section ID (alphabetically later)
- `similarity` (float, required): Cosine similarity score (0.0 to 1.0)

**Notes**:
- Only include pairs with similarity > 0.7 to save space
- Store only one direction: `section_a < section_b` (alphabetically)
- Do NOT include self-similarities (section_a == section_b)

---

### reporting.ndjson

**Producer**: `pipeline/50_llm_reporting.py`
**Consumer**: `dbtools/load_reporting.py`
**Location**: `data/outputs/reporting.ndjson` or `data/outputs/reporting_subset.ndjson`

```json
{
  "id": "dc-1-101",
  "has_reporting": true,
  "reporting_summary": "Requires annual report to the Mayor by January 31st.",
  "tags": ["reporting", "mayor", "annual"],
  "highlight_phrases": ["annual report", "submitted to the Mayor", "January 31"]
}
```

**Field Specifications**:
- `id` (string, required): Section ID
- `has_reporting` (boolean, required): Whether section has reporting requirements
- `reporting_summary` (string, optional): 1-2 sentence summary (empty string if none)
- `tags` (array of strings, required): High-level categorization tags
- `highlight_phrases` (array of strings, required): Exact phrases to highlight in UI

**Notes**:
- `highlight_phrases` must be exact substrings from `text_plain` for highlighting to work
- Tags should be lowercase, kebab-case (e.g., "public-hearing", "mayor-approval")

---

## Validation

Each track should validate its inputs/outputs against these schemas:

**Track A (Pipeline)**:
- Validate output NDJSON before writing (catch issues early)
- Log validation failures to `data/interim/{script}_errors.ndjson`

**Track B (Loaders)**:
- Validate input NDJSON before inserting to database
- Skip invalid records (log to errors table or file)
- Continue processing valid records

**Example validation check**:
```python
import json

def validate_section(record):
    required = ["id", "citation", "heading", "text_plain", "text_html",
                "ancestors", "title_label", "chapter_label"]
    for field in required:
        if field not in record:
            raise ValueError(f"Missing required field: {field}")
    return True

# Usage:
with open("sections.ndjson") as f:
    for line in f:
        record = json.loads(line)
        validate_section(record)  # Raises if invalid
```

---

## Versioning

If schema changes are needed:
1. Update this document
2. Increment version in `pipeline/common.py`
3. Add migration notes to `CHANGELOG.md`
4. Consider backward-compatible changes when possible
