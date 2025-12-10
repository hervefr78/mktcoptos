"""
Agent Prompts Package
=====================

Contains prompt templates for all agents.
"""

from .content_pipeline_prompts import (
    ORCHESTRATOR_AGENT_PROMPT,
    TRENDS_KEYWORDS_AGENT_PROMPT,
    TONE_OF_VOICE_RAG_AGENT_PROMPT,
    STRUCTURE_OUTLINE_AGENT_PROMPT,
    WRITER_AGENT_PROMPT,
    SEO_OPTIMIZER_AGENT_PROMPT,
    ORIGINALITY_PLAGIARISM_AGENT_PROMPT,
    FINAL_REVIEWER_AGENT_PROMPT,
    CONTENT_PIPELINE_AGENTS,
    get_agent_prompt,
    get_agent_config,
    get_all_agent_configs,
    get_pipeline_order,
    format_prompt_with_variables,
)

__all__ = [
    # Prompts
    "ORCHESTRATOR_AGENT_PROMPT",
    "TRENDS_KEYWORDS_AGENT_PROMPT",
    "TONE_OF_VOICE_RAG_AGENT_PROMPT",
    "STRUCTURE_OUTLINE_AGENT_PROMPT",
    "WRITER_AGENT_PROMPT",
    "SEO_OPTIMIZER_AGENT_PROMPT",
    "ORIGINALITY_PLAGIARISM_AGENT_PROMPT",
    "FINAL_REVIEWER_AGENT_PROMPT",
    # Config
    "CONTENT_PIPELINE_AGENTS",
    # Functions
    "get_agent_prompt",
    "get_agent_config",
    "get_all_agent_configs",
    "get_pipeline_order",
    "format_prompt_with_variables",
]
