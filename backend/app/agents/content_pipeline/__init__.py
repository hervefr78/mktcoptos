"""
Content Pipeline Package
========================

Multi-agent content creation pipeline for marketers.
"""

from .content_agents import (
    TrendsKeywordsAgent,
    ToneOfVoiceAgent,
    StructureOutlineAgent,
    WriterAgent,
    SEOOptimizerAgent,
    OriginalityPlagiarismAgent,
    FinalReviewerAgent,
    get_content_agent,
    get_all_content_agents,
)

from .orchestrator import ContentPipelineOrchestrator

__all__ = [
    # Agent classes
    "TrendsKeywordsAgent",
    "ToneOfVoiceAgent",
    "StructureOutlineAgent",
    "WriterAgent",
    "SEOOptimizerAgent",
    "OriginalityPlagiarismAgent",
    "FinalReviewerAgent",
    # Factory functions
    "get_content_agent",
    "get_all_content_agents",
    # Orchestrator
    "ContentPipelineOrchestrator",
]
