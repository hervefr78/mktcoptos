"""
Pydantic schemas for content pipeline agent outputs.

These schemas provide type safety and validation for agent responses.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# AGENT 1: TRENDS & KEYWORDS AGENT
# =============================================================================

class TrendsKeywordsOutput(BaseModel):
    """Output schema for Trends & Keywords Agent."""

    trend_summary: str = Field(..., min_length=10, description="Summary of key trends")
    primary_keywords: List[str] = Field(..., min_length=1, description="Primary keywords (1-5 items)")
    secondary_keywords: List[str] = Field(..., description="Secondary/long-tail keywords")
    search_intent_insights: str = Field(..., min_length=10, description="Search intent analysis")
    angle_ideas: List[str] = Field(..., min_length=1, description="Content angle ideas")


# =============================================================================
# AGENT 2: TONE OF VOICE AGENT
# =============================================================================

class StyleProfile(BaseModel):
    """Style profile nested in Tone of Voice output."""

    summary: str = Field(..., min_length=10)
    formality_level: str = Field(...)
    person_preference: str = Field(...)
    sentence_rhythm: str = Field(..., min_length=10)
    structural_preferences: List[str] = Field(...)
    rhetorical_devices: List[str] = Field(...)
    lexical_fields_and_signature_phrases: Dict[str, List[str]] = Field(...)
    do_and_dont: Dict[str, List[str]] = Field(...)
    geo_friendly_structures: Optional[List[str]] = Field(default=None, description="GEO-friendly structural patterns")
    rewrite_examples: List[Dict[str, str]] = Field(...)
    support_confidence: Optional[Dict[str, List[str]]] = Field(default=None, description="Confidence levels for style rules")

    @field_validator('formality_level')
    def validate_formality(cls, v):
        valid_levels = ['very informal', 'informal', 'neutral', 'formal', 'very formal']
        if v not in valid_levels:
            raise ValueError(f"formality_level must be one of {valid_levels}")
        return v


class ToneOfVoiceOutput(BaseModel):
    """Output schema for Tone of Voice Agent."""

    style_profile: StyleProfile = Field(...)


# =============================================================================
# AGENT 3: STRUCTURE & OUTLINE AGENT
# =============================================================================

class Section(BaseModel):
    """Section in content outline."""

    id: str = Field(..., pattern=r'^S\d+$', description="Section ID like S1, S2, etc.")
    title: str = Field(..., min_length=3)
    objective: str = Field(..., min_length=10)
    key_points: List[str] = Field(..., min_length=1)


class StructureOutlineOutput(BaseModel):
    """Output schema for Structure & Outline Agent."""

    content_promise: str = Field(..., min_length=10)
    hook_ideas: List[str] = Field(..., min_length=1)
    sections: List[Section] = Field(..., min_length=1)


# =============================================================================
# AGENT 4: WRITER AGENT
# =============================================================================

class WriterOutput(BaseModel):
    """Output schema for Writer Agent."""

    full_text: str = Field(..., min_length=100, description="Complete draft content in Markdown")

    @field_validator('full_text')
    def validate_content_length(cls, v):
        word_count = len(v.split())
        if word_count < 50:
            raise ValueError(f"Content too short: {word_count} words (minimum 50)")
        return v


# =============================================================================
# AGENT 5: SEO OPTIMIZER AGENT
# =============================================================================

class OnPageSEO(BaseModel):
    """On-page SEO metadata."""

    focus_keyword: str = Field(..., min_length=1)
    title_tag: str = Field(..., min_length=10, max_length=70, description="SEO title (50-60 chars optimal)")
    meta_description: str = Field(..., min_length=50, max_length=165, description="Meta description (150-160 chars optimal)")
    h1: str = Field(..., min_length=5)
    slug: str = Field(..., min_length=3)
    suggested_internal_links: List[str] = Field(default_factory=list)
    suggested_external_links: List[str] = Field(default_factory=list)
    seo_score: Optional[int] = Field(default=None, ge=0, le=100)

    @field_validator('title_tag')
    def validate_title_length(cls, v):
        if len(v) > 70:
            raise ValueError(f"Title tag too long: {len(v)} chars (max 70, optimal 50-60)")
        return v

    @field_validator('meta_description')
    def validate_meta_length(cls, v):
        if len(v) > 165:
            raise ValueError(f"Meta description too long: {len(v)} chars (max 165, optimal 150-160)")
        return v


class SEOOptimizerOutput(BaseModel):
    """Output schema for SEO Optimizer Agent."""

    optimized_text: str = Field(..., min_length=100, description="SEO-optimized content")
    on_page_seo: OnPageSEO = Field(...)

    @field_validator('optimized_text')
    def validate_content_length(cls, v):
        word_count = len(v.split())
        if word_count < 50:
            raise ValueError(f"Content too short: {word_count} words (minimum 50)")
        return v


# =============================================================================
# AGENT 6: ORIGINALITY & PLAGIARISM AGENT
# =============================================================================

class FlaggedPassage(BaseModel):
    """A passage flagged for originality concerns."""

    original_excerpt: Optional[str] = Field(default=None, alias='original_text')
    reason: str = Field(..., min_length=5)
    rewritten_excerpt: Optional[str] = Field(default=None, alias='rewritten_text')

    class Config:
        populate_by_name = True  # Allow both original_excerpt and original_text


class OriginalityOutput(BaseModel):
    """Output schema for Originality & Plagiarism Agent."""

    originality_score: str = Field(..., pattern=r'^(high|medium|low)$')
    risk_summary: str = Field(..., min_length=10)
    rewritten_text: str = Field(..., min_length=100, description="Complete rewritten text with fixes applied")
    flagged_passages: List[FlaggedPassage] = Field(default_factory=list)

    @field_validator('rewritten_text')
    def validate_content_length(cls, v):
        word_count = len(v.split())
        if word_count < 50:
            raise ValueError(f"Rewritten text too short: {word_count} words (minimum 50)")
        return v


# =============================================================================
# AGENT 7: FINAL REVIEWER AGENT
# =============================================================================

class SuggestedVariant(BaseModel):
    """A suggested content variant."""

    use_case: str = Field(..., min_length=5)
    variant_text: str = Field(..., min_length=10)


class FinalReviewerOutput(BaseModel):
    """Output schema for Final Reviewer Agent."""

    final_text: str = Field(..., min_length=100, description="Final polished content ready for publication")
    change_log: List[str] = Field(..., description="List of changes made")
    editor_notes_for_user: List[str] = Field(default_factory=list)
    suggested_variants: List[SuggestedVariant] = Field(default_factory=list)

    @field_validator('final_text')
    def validate_content_length(cls, v):
        word_count = len(v.split())
        if word_count < 50:
            raise ValueError(f"Final text too short: {word_count} words (minimum 50)")
        return v


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def validate_agent_output_with_schema(agent_name: str, result: Dict[str, Any], schema_class: type[BaseModel]) -> BaseModel:
    """
    Validate agent output using Pydantic schema.

    Args:
        agent_name: Name of the agent for error messages
        result: Raw agent output dictionary
        schema_class: Pydantic model class to validate against

    Returns:
        Validated Pydantic model instance

    Raises:
        ValueError: If validation fails
    """
    try:
        validated = schema_class(**result)
        return validated
    except Exception as e:
        error_msg = f"{agent_name} output validation failed: {str(e)}"
        raise ValueError(error_msg)


# Map agent names to their schemas
AGENT_SCHEMAS = {
    "trends_keywords": TrendsKeywordsOutput,
    "tone_of_voice": ToneOfVoiceOutput,
    "structure_outline": StructureOutlineOutput,
    "writer": WriterOutput,
    "seo_optimizer": SEOOptimizerOutput,
    "originality_plagiarism": OriginalityOutput,
    "final_reviewer": FinalReviewerOutput,
}
