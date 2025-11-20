"""
Pydantic models for pipeline data validation.

This module defines jurisdiction-agnostic data models for all pipeline outputs.
All models support multi-jurisdiction (DC, California, New York, etc.) via the
`jurisdiction` field.

Models correspond to NDJSON output schemas defined in CONTRACTS.md.

Usage:
    from pipeline.models import Section, ReportingRequirement

    section = Section(
        id="dc-1-101",
        citation="§ 1-101",
        heading="Title and short title",
        text_plain="This title may be cited...",
        text_html="<p>This title may be cited...</p>",
        ancestors=[],
        title_label="Title 1",
        chapter_label="Chapter 1"
    )
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Hierarchical Structure Models
# =============================================================================


class Ancestor(BaseModel):
    """
    Represents a hierarchical ancestor (title, chapter, etc.) in the legal code.

    Used by Section model to maintain full hierarchical context.
    """

    type: str = Field(
        ..., description="Type of ancestor: title, subtitle, chapter, subchapter, etc."
    )
    label: str = Field(..., description="Human-readable label: 'Title 1', 'Chapter 3'")
    id: str = Field(..., description="Unique identifier: 'dc-title-1', 'dc-1-chapter-3'")

    model_config = {"str_strip_whitespace": True}


class StructureNode(BaseModel):
    """
    Hierarchical structure node (title, chapter, subchapter, part, subpart).

    Output of: pipeline/10_parse_xml.py (Pass 1 - index.xml parsing)
    Consumed by: dbtools/load_structure.py

    Represents one node in the legal code hierarchy tree. These nodes form
    the navigation structure for browsing the code by title/chapter/etc.
    """

    jurisdiction: str = Field(
        default="dc",
        description="Jurisdiction code",
        max_length=10,
    )
    id: str = Field(
        ...,
        description="Unique node identifier: 'dc-title-1', 'dc-1-2-subchapter-ii'",
    )
    parent_id: Optional[str] = Field(
        None,
        description="Parent node ID (null for top-level titles)",
    )
    level: str = Field(
        ...,
        description="Hierarchy level: title, chapter, subchapter, part, subpart",
    )
    label: str = Field(
        ...,
        description="Display label: 'Title 1', 'Chapter 3', 'Subchapter II'",
    )
    heading: str = Field(
        ...,
        description="Full heading text from index.xml",
    )
    ordinal: int = Field(
        ...,
        description="Sort order within parent (1-based index)",
        ge=1,
    )

    @field_validator("jurisdiction")
    @classmethod
    def lowercase_jurisdiction(cls, v: str) -> str:
        """Ensure jurisdiction is lowercase."""
        return v.lower()

    @field_validator("level")
    @classmethod
    def lowercase_level(cls, v: str) -> str:
        """Ensure level is lowercase for consistency."""
        return v.lower()

    model_config = {"str_strip_whitespace": True}


# =============================================================================
# Section Models
# =============================================================================


class Section(BaseModel):
    """
    Legal code section with full text and metadata.

    Output of: pipeline/10_parse_xml.py
    Consumed by: dbtools/load_sections.py
    """

    jurisdiction: str = Field(
        default="dc",
        description="Jurisdiction code: dc, ca, ny, etc.",
        max_length=10,
    )
    id: str = Field(..., description="Unique section identifier: 'dc-1-101'")
    citation: str = Field(..., description="Official citation: '§ 1-101'")
    heading: str = Field(..., description="Section heading/title")
    text_plain: str = Field(..., description="Plain text content (no HTML)")
    text_html: str = Field(..., description="HTML-formatted content")
    ancestors: List[Ancestor] = Field(
        ..., description="Hierarchical context (title, chapter, etc.)"
    )
    title_label: str = Field(..., description="Title label for filtering: 'Title 1'")
    chapter_label: str = Field(
        ..., description="Chapter label for filtering: 'Chapter 1'"
    )
    effective_date: Optional[str] = Field(
        None, description="Effective date in YYYY-MM-DD format (from <history> tag)"
    )

    @field_validator("jurisdiction")
    @classmethod
    def lowercase_jurisdiction(cls, v: str) -> str:
        """Ensure jurisdiction is lowercase."""
        return v.lower()

    @field_validator("effective_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date is in YYYY-MM-DD format."""
        if v is None:
            return v
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError(f"effective_date must be in YYYY-MM-DD format, got: {v}")

    model_config = {"str_strip_whitespace": True}


# =============================================================================
# Cross-Reference Models
# =============================================================================


class CrossReference(BaseModel):
    """
    Citation relationship between two sections.

    Output of: pipeline/20_crossrefs.py
    Consumed by: dbtools/load_refs.py
    """

    jurisdiction: str = Field(
        default="dc",
        description="Jurisdiction code",
        max_length=10,
    )
    from_id: str = Field(..., description="Source section ID")
    to_id: str = Field(..., description="Target section ID")
    raw_cite: str = Field(
        ..., description="Original citation text as it appears in source"
    )

    @field_validator("jurisdiction")
    @classmethod
    def lowercase_jurisdiction(cls, v: str) -> str:
        """Ensure jurisdiction is lowercase."""
        return v.lower()

    model_config = {"str_strip_whitespace": True}


# =============================================================================
# Obligation Models (Deadlines and Amounts)
# =============================================================================


class Deadline(BaseModel):
    """
    Temporal obligation extracted from legal text.

    Output of: pipeline/30_regex_obligations.py
    Consumed by: dbtools/load_deadlines_amounts.py
    """

    jurisdiction: str = Field(
        default="dc",
        description="Jurisdiction code",
        max_length=10,
    )
    section_id: str = Field(..., description="Section containing the deadline")
    phrase: str = Field(
        ...,
        description="Exact text phrase from section",
        min_length=5,
        max_length=500,
    )
    days: int = Field(..., description="Number of days for the deadline", gt=0)
    kind: str = Field(
        ...,
        description="Type of deadline: deadline, notice_period, waiting_period",
    )

    @field_validator("jurisdiction")
    @classmethod
    def lowercase_jurisdiction(cls, v: str) -> str:
        """Ensure jurisdiction is lowercase."""
        return v.lower()

    model_config = {"str_strip_whitespace": True}


class Amount(BaseModel):
    """
    Dollar amount extracted from legal text.

    Output of: pipeline/30_regex_obligations.py
    Consumed by: dbtools/load_deadlines_amounts.py
    """

    jurisdiction: str = Field(
        default="dc",
        description="Jurisdiction code",
        max_length=10,
    )
    section_id: str = Field(..., description="Section containing the amount")
    phrase: str = Field(
        ...,
        description="Exact text phrase from section",
        min_length=5,
        max_length=500,
    )
    amount_cents: int = Field(
        ...,
        description="Amount in cents (e.g., $10.50 = 1050). Can be negative for credits.",
    )

    @field_validator("jurisdiction")
    @classmethod
    def lowercase_jurisdiction(cls, v: str) -> str:
        """Ensure jurisdiction is lowercase."""
        return v.lower()

    model_config = {"str_strip_whitespace": True}


class Obligation(BaseModel):
    """
    Enhanced obligation with LLM classification (for future use).

    Replaces separate Deadline and Amount models with unified structure.
    Output of: pipeline/35_llm_obligations.py (future)
    """

    jurisdiction: str = Field(
        default="dc",
        description="Jurisdiction code",
        max_length=10,
    )
    section_id: str = Field(
        default="",
        description="Section containing the obligation (set by pipeline, not LLM)",
    )
    category: Literal["deadline", "constraint", "allocation", "penalty"] = Field(
        ..., description="Type of obligation"
    )
    phrase: str = Field(
        ...,
        description="Exact text phrase from section",
        min_length=5,
        max_length=500,
    )
    value: Optional[float] = Field(
        None,
        description="Numeric value (days for deadlines, dollars for amounts)",
    )
    unit: Optional[str] = Field(
        None,
        description="Unit of measurement: days, dollars, percent, etc.",
        max_length=50,
    )

    @field_validator("jurisdiction")
    @classmethod
    def lowercase_jurisdiction(cls, v: str) -> str:
        """Ensure jurisdiction is lowercase."""
        return v.lower()

    model_config = {"str_strip_whitespace": True}


class ObligationsList(BaseModel):
    """
    Wrapper for extracting multiple obligations from a single section.

    Used by LLM to return array of obligations found in text.
    Output of: pipeline/35_llm_obligations.py
    """

    obligations: List[Obligation] = Field(
        default_factory=list,
        description="List of all obligations found in the section (can be empty)"
    )
    potential_anachronism: bool = Field(
        default=False,
        description="True if section contains anachronistic language (obsolete technology, outdated terminology, discriminatory language)"
    )

    model_config = {"str_strip_whitespace": True}


# =============================================================================
# Similarity Models
# =============================================================================


class SimilarityPair(BaseModel):
    """
    Semantic similarity between two sections.

    Output of: pipeline/40_similarities.py
    Consumed by: dbtools/load_similarities.py
    """

    jurisdiction: str = Field(
        default="dc",
        description="Jurisdiction code",
        max_length=10,
    )
    section_a: str = Field(
        ..., description="First section ID (alphabetically earlier)"
    )
    section_b: str = Field(..., description="Second section ID (alphabetically later)")
    similarity: float = Field(
        ...,
        description="Cosine similarity score (0.0 to 1.0)",
        ge=0.0,
    )

    @field_validator("jurisdiction")
    @classmethod
    def lowercase_jurisdiction(cls, v: str) -> str:
        """Ensure jurisdiction is lowercase."""
        return v.lower()

    @field_validator("similarity")
    @classmethod
    def clamp_similarity(cls, v: float) -> float:
        """Clamp similarity to [0.0, 1.0] range to handle floating-point errors."""
        if v > 1.0:
            return 1.0
        elif v < 0.0:
            return 0.0
        return v

    @field_validator("section_b")
    @classmethod
    def validate_section_order(cls, v: str, info) -> str:
        """Ensure section_a < section_b alphabetically."""
        section_a = info.data.get("section_a")
        if section_a and v <= section_a:
            raise ValueError(
                f"section_b must be alphabetically greater than section_a. "
                f"Got section_a='{section_a}', section_b='{v}'"
            )
        return v

    model_config = {"str_strip_whitespace": True}


# =============================================================================
# Reporting Requirement Models
# =============================================================================


class ReportingRequirement(BaseModel):
    """
    LLM-detected reporting requirement from legal section.

    Output of: pipeline/50_llm_reporting.py
    Consumed by: dbtools/load_reporting.py
    """

    jurisdiction: str = Field(
        default="dc",
        description="Jurisdiction code",
        max_length=10,
    )
    id: str = Field(
        default="",
        description="Section ID (set by pipeline, not LLM)",
    )
    has_reporting: bool = Field(
        default=False,
        description="True if section mandates any reporting, filing, or notice requirement (default: False if LLM doesn't return)",
    )
    reporting_summary: str = Field(
        default="",
        description="Concise 1-2 sentence summary of reporting requirement",
        max_length=500,
    )
    reporting_text: Optional[str] = Field(
        None,
        description="Exact full text of the reporting requirement from the section",
        max_length=5000,
    )
    tags: List[str] = Field(
        default_factory=list,
        description="High-level categorization tags (lowercase, kebab-case)",
        max_length=20,
    )
    highlight_phrases: List[str] = Field(
        default_factory=list,
        description="Exact phrases from text to highlight in UI",
        max_length=50,
    )
    potential_anachronism: bool = Field(
        default=False,
        description="True if section contains anachronistic language (obsolete technology, outdated terminology, discriminatory language)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Pipeline metadata (model, version, timestamp)",
    )

    @field_validator("jurisdiction")
    @classmethod
    def lowercase_jurisdiction(cls, v: str) -> str:
        """Ensure jurisdiction is lowercase."""
        return v.lower()

    @field_validator("tags")
    @classmethod
    def lowercase_kebab_tags(cls, v: List[str]) -> List[str]:
        """Ensure tags are lowercase and kebab-case."""
        return [tag.lower().replace(" ", "-") for tag in v]

    model_config = {"str_strip_whitespace": True}


# =============================================================================
# Similarity Classification Models
# =============================================================================


class SimilarityClassification(BaseModel):
    """
    LLM classification of why two sections are similar.

    Output of: pipeline/55_similarity_classification.py
    Consumed by: dbtools/load_similarity_classifications.py
    """

    jurisdiction: str = Field(
        default="dc",
        description="Jurisdiction code",
        max_length=10,
    )
    section_a: str = Field(
        ..., description="First section ID (alphabetically earlier)"
    )
    section_b: str = Field(..., description="Second section ID (alphabetically later)")
    similarity: float = Field(
        ...,
        description="Cosine similarity score (0.0 to 1.0)",
        ge=0.0,
    )
    classification: Literal[
        "duplicate", "superseded", "related", "conflicting", "unrelated"
    ] = Field(
        ...,
        description="Type of relationship: duplicate, superseded, related, conflicting, unrelated",
    )
    potential_anachronism: bool = Field(
        default=False,
        description="True if either section shows potential anachronistic language (obsolete tech, discriminatory terms, defunct constructs)"
    )
    explanation: str = Field(
        ...,
        description="Brief explanation of classification",
        min_length=20,
        max_length=1000,
    )
    model_used: str = Field(
        ...,
        description="LLM model used: gemini-2.5-flash, phi4-mini, etc.",
        max_length=50,
    )
    analyzed_at: str = Field(..., description="ISO 8601 timestamp of analysis")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional pipeline metadata",
    )

    # Cross-encoder triage fields (for Model Cascading optimization)
    cross_encoder_label: Optional[str] = Field(
        None,
        description="NLI label from cross-encoder: entailment, contradiction, or neutral",
    )
    cross_encoder_score: Optional[float] = Field(
        None,
        description="Confidence score from cross-encoder (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )

    @field_validator("jurisdiction")
    @classmethod
    def lowercase_jurisdiction(cls, v: str) -> str:
        """Ensure jurisdiction is lowercase."""
        return v.lower()

    @field_validator("classification", mode="before")
    @classmethod
    def fix_classification_typos(cls, v: str) -> str:
        """Fix common typos in classification field."""
        typo_map = {
            "superseted": "superseded",
            "superceded": "superseded",
            "duplicated": "duplicate",
        }
        return typo_map.get(v, v)

    @field_validator("similarity")
    @classmethod
    def clamp_similarity(cls, v: float) -> float:
        """Clamp similarity to [0.0, 1.0] range to handle floating-point errors."""
        if v > 1.0:
            return 1.0
        elif v < 0.0:
            return 0.0
        return v

    @field_validator("analyzed_at")
    @classmethod
    def validate_iso8601(cls, v: str) -> str:
        """Validate timestamp is valid ISO 8601 format."""
        # Allow empty string (may be set by pipeline later)
        if v == "":
            return v
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError(f"analyzed_at must be ISO 8601 format, got: {v}")

    model_config = {"str_strip_whitespace": True}


# =============================================================================
# Anachronism Detection Models
# =============================================================================


class AnachronismIndicator(BaseModel):
    """
    Individual anachronistic indicator found in a legal section.

    Output of: pipeline/60_llm_anachronisms.py
    Consumed by: dbtools/load_anachronisms.py
    """

    category: Literal[
        "jim_crow",
        "obsolete_technology",
        "defunct_agency",
        "gendered_titles",
        "archaic_measurements",
        "outdated_professions",
        "obsolete_legal_terms",
        "outdated_medical_terms",
        "obsolete_transportation",
        "obsolete_military",
        "prohibition_era",
        "outdated_education",
        "obsolete_religious",
        "age_based",
        "environmental_agricultural",
        "commercial_business",
        "outdated_social_structures",
        "obsolete_economic",
    ] = Field(..., description="Category of anachronism detected")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(
        ..., description="Severity level of the anachronism"
    )
    matched_phrases: List[str] = Field(
        ...,
        description="Exact phrases from the section that are anachronistic",
        min_length=1,
        max_length=20,
    )
    modern_equivalent: Optional[str] = Field(
        None,
        description="Suggested modern replacement language",
        max_length=500,
    )
    recommendation: Literal["REPEAL", "UPDATE", "REVIEW", "PRESERVE"] = Field(
        ...,
        description="Recommended action: REPEAL (unconstitutional/harmful), UPDATE (replace terms), REVIEW (needs legal analysis), PRESERVE (historical context)",
    )
    explanation: str = Field(
        ...,
        description="Explanation of why this is anachronistic and what it means",
        min_length=20,
        max_length=1000,
    )

    model_config = {"str_strip_whitespace": True}


class AnachronismAnalysis(BaseModel):
    """
    Complete anachronism analysis for a legal section.

    Output of: pipeline/60_llm_anachronisms.py
    Consumed by: dbtools/load_anachronisms.py
    """

    jurisdiction: str = Field(
        default="dc",
        description="Jurisdiction code",
        max_length=10,
    )
    section_id: str = Field(
        default="",
        description="Section ID being analyzed (set by pipeline, not LLM)",
    )
    has_anachronism: bool = Field(
        ...,
        description="True if section contains any anachronistic language",
    )
    overall_severity: Optional[Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]] = Field(
        None,
        description="Highest severity level among all indicators (null if no anachronisms)",
    )
    indicators: List[AnachronismIndicator] = Field(
        default_factory=list,
        description="List of all anachronistic indicators found (empty if none)",
    )
    summary: str = Field(
        default="",
        description="Overall summary of anachronistic content (empty if none found)",
        max_length=1000,
    )
    requires_immediate_review: bool = Field(
        default=False,
        description="True if section contains CRITICAL severity issues requiring immediate legal review",
    )
    model_used: str = Field(
        ...,
        description="LLM model used for analysis",
        max_length=50,
    )
    analyzed_at: str = Field(..., description="ISO 8601 timestamp of analysis")

    @field_validator("jurisdiction")
    @classmethod
    def lowercase_jurisdiction(cls, v: str) -> str:
        """Ensure jurisdiction is lowercase."""
        return v.lower()

    @field_validator("analyzed_at")
    @classmethod
    def validate_iso8601(cls, v: str) -> str:
        """Validate timestamp is valid ISO 8601 format."""
        # Allow empty string (may be set by pipeline later)
        if v == "":
            return v
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError(f"analyzed_at must be ISO 8601 format, got: {v}")

    model_config = {"str_strip_whitespace": True}


# =============================================================================
# PAHLKA IMPLEMENTATION ANALYSIS MODELS
# =============================================================================

class PahlkaImplementationIndicator(BaseModel):
    """
    Individual implementation issue indicator following Jennifer Pahlka's framework.

    Identifies specific patterns that create implementation complexity, administrative
    burden, or separation between policy and delivery.

    Categories align with "Recoding America" principles:
    - complexity_policy_debt: Cross-reference spaghetti, accreted conditions
    - options_become_requirements: Suggestion lists become checklists
    - policy_implementation_separation: Waterfall, vendor lock-in
    - overwrought_legalese: Dense definitions that make forms impossible
    - cascade_of_rigidity: Conflicting absolute goals
    - mandated_steps_not_outcomes: Procedure-heavy vs outcome-focused
    - administrative_burdens: Notaries, wet signatures, in-person requirements
    - no_feedback_loops: One-shot design, no pilots or learning
    - process_worship_oversight: Compliance-only audits
    - zero_risk_language: Impossible absolutes ("ensure no X ever occurs")
    - frozen_technology: Hard-coded architectures, formats, platforms
    - implementation_opportunity: POSITIVE patterns (outcome focus, iteration)
    """
    category: Literal[
        "complexity_policy_debt",
        "options_become_requirements",
        "policy_implementation_separation",
        "overwrought_legalese",
        "cascade_of_rigidity",
        "mandated_steps_not_outcomes",
        "administrative_burdens",
        "no_feedback_loops",
        "process_worship_oversight",
        "zero_risk_language",
        "frozen_technology",
        "implementation_opportunity"
    ]
    complexity: Literal["HIGH", "MEDIUM", "LOW"]
    matched_phrases: List[str] = Field(
        min_length=1,
        max_length=20,
        description="Specific text from section that triggered this indicator"
    )
    implementation_approach: str = Field(
        min_length=10,
        max_length=1000,
        description="Suggested approach for implementation or improvement"
    )
    effort_estimate: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Estimated implementation difficulty/timeline"
    )
    explanation: str = Field(
        min_length=20,
        max_length=1000,
        description="Why this creates implementation burden or opportunity"
    )

    @field_validator('matched_phrases')
    @classmethod
    def validate_phrases_not_empty(cls, v):
        """Ensure no empty phrases in list."""
        if not v:
            raise ValueError("matched_phrases must contain at least one phrase")
        for phrase in v:
            if not phrase or not phrase.strip():
                raise ValueError("matched_phrases cannot contain empty strings")
        return v

    model_config = {"str_strip_whitespace": True}


class PahlkaImplementationAnalysis(BaseModel):
    """
    Complete Pahlka implementation analysis for a DC Code section.

    Analyzes implementation complexity and alignment with Jennifer Pahlka's
    "recoding government" principles from "Recoding America".

    Output of: pipeline/70_llm_pahlka_implementation.py
    Consumed by: dbtools/load_pahlka_implementation.py
    """

    jurisdiction: str = Field(
        default="dc",
        description="Jurisdiction code",
        max_length=10,
    )
    section_id: str = Field(
        default="",
        description="Section ID being analyzed (set by pipeline, not LLM)"
    )
    has_implementation_issues: bool = Field(
        ...,
        description="Whether section has implementation complexity or burdens"
    )
    overall_complexity: Optional[Literal["HIGH", "MEDIUM", "LOW"]] = Field(
        default=None,
        description="Overall implementation complexity level (null if no issues)"
    )
    indicators: List[PahlkaImplementationIndicator] = Field(
        default_factory=list,
        description="List of specific implementation issues found (empty if none)"
    )
    summary: str = Field(
        default="",
        min_length=0,
        max_length=2000,
        description="2-3 sentence summary of implementation concerns"
    )
    requires_technical_review: bool = Field(
        default=False,
        description="Whether section needs technical/architecture review"
    )
    model_used: str = Field(
        default="",
        description="Name of LLM model that performed the analysis (set by pipeline, not LLM)",
        max_length=50,
    )
    analyzed_at: str = Field(
        default="",
        description="ISO 8601 timestamp of when analysis was performed (set by pipeline, not LLM)"
    )

    @field_validator("jurisdiction")
    @classmethod
    def lowercase_jurisdiction(cls, v: str) -> str:
        """Ensure jurisdiction is lowercase."""
        return v.lower()

    @field_validator('analyzed_at')
    @classmethod
    def validate_iso8601(cls, v):
        """Validate that analyzed_at is a valid ISO 8601 timestamp."""
        # Allow empty string (default value when LLM doesn't provide it)
        if v == "":
            return v
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(f"analyzed_at must be ISO 8601 format, got: {v}")

    @field_validator('overall_complexity')
    @classmethod
    def validate_complexity_with_issues(cls, v, info):
        """If has_implementation_issues is True, overall_complexity should be set."""
        if 'has_implementation_issues' in info.data:
            if info.data['has_implementation_issues'] and v is None:
                raise ValueError("overall_complexity should be set when has_implementation_issues is True")
        return v

    model_config = {"str_strip_whitespace": True}
