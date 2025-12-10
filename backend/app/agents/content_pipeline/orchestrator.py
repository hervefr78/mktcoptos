"""
Content Pipeline Orchestrator
==============================

Coordinates the multi-agent content creation workflow.
"""

from __future__ import annotations

import json
import logging
import time
import os
from datetime import datetime
from typing import Any, Optional, Dict, Callable, List
from dataclasses import dataclass, field
from enum import Enum

from .content_agents import (
    TrendsKeywordsAgent,
    ToneOfVoiceAgent,
    StructureOutlineAgent,
    WriterAgent,
    SEOOptimizerAgent,
    OriginalityPlagiarismAgent,
    FinalReviewerAgent,
)
from .rag_similarity import RAGSimilarityAnalyzer
from ...agent_logger import AgentLogger
from ...agent_activity_tracker import AgentActivityTracker

logger = logging.getLogger(__name__)


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass


class AgentValidationError(PipelineError):
    """Raised when agent output validation fails."""
    def __init__(self, agent_name: str, message: str):
        self.agent_name = agent_name
        super().__init__(f"{agent_name}: {message}")


class ContentLengthError(PipelineError):
    """Raised when content is too short or truncated."""
    def __init__(self, agent_name: str, word_count: int, min_words: int):
        self.agent_name = agent_name
        self.word_count = word_count
        self.min_words = min_words
        super().__init__(
            f"{agent_name} content too short: {word_count} words (minimum {min_words} words). "
            f"Content may have been truncated by the LLM."
        )


class RAGRetrievalError(PipelineError):
    """Raised when RAG retrieval fails or returns no content."""
    def __init__(self, message: str, document_ids: Optional[List[int]] = None):
        self.document_ids = document_ids
        super().__init__(message)


class SEOValidationError(AgentValidationError):
    """Raised when SEO metadata validation fails."""
    def __init__(self, missing_fields: List[str]):
        self.missing_fields = missing_fields
        super().__init__(
            "SEO Optimizer Agent",
            f"Missing required on_page_seo fields: {missing_fields}"
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def safe_dict(value: Any) -> Dict:
    """
    Safely convert a value to a dictionary.

    Args:
        value: Can be a dict, JSON string, or None

    Returns:
        dict: The value as a dictionary, or empty dict if None or conversion fails
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Failed to parse JSON string: {value[:100]}...")
            return {}
    return {}


def calculate_content_diff(before: str, after: str, agent_name: str) -> Dict[str, Any]:
    """
    Calculate meaningful diff metrics between before and after content.

    Args:
        before: Content before transformation
        after: Content after transformation
        agent_name: Name of the agent for logging

    Returns:
        Dictionary with diff metrics
    """
    if not before or not after:
        return {
            "chars_changed": 0,
            "change_percentage": 0.0,
            "word_count_before": 0,
            "word_count_after": 0,
            "word_count_delta": 0
        }

    # Basic metrics
    before_len = len(before)
    after_len = len(after)
    before_words = len(before.split())
    after_words = len(after.split())

    # Simple edit distance approximation (char-level difference)
    chars_changed = abs(after_len - before_len)
    change_percentage = (chars_changed / before_len * 100) if before_len > 0 else 0

    # Count paragraph changes (rough approximation)
    before_paras = len([p for p in before.split('\n\n') if p.strip()])
    after_paras = len([p for p in after.split('\n\n') if p.strip()])
    paragraphs_changed = abs(after_paras - before_paras)

    metrics = {
        "chars_before": before_len,
        "chars_after": after_len,
        "chars_changed": chars_changed,
        "change_percentage": round(change_percentage, 2),
        "word_count_before": before_words,
        "word_count_after": after_words,
        "word_count_delta": after_words - before_words,
        "paragraphs_before": before_paras,
        "paragraphs_after": after_paras,
        "paragraphs_changed": paragraphs_changed
    }

    # Log warnings if agent made minimal changes
    if change_percentage < 1.0 and before_len > 100:
        logger.warning(f"⚠️ {agent_name} made minimal changes: {change_percentage:.2f}% change")
        logger.warning(f"   This agent may not be transforming content properly")
    elif change_percentage > 50:
        logger.info(f"📝 {agent_name} made substantial changes: {change_percentage:.2f}% change")
    else:
        logger.info(f"📝 {agent_name} changes: {change_percentage:.2f}% ({chars_changed} chars, {metrics['word_count_delta']:+d} words)")

    return metrics


def validate_agent_output(agent_name: str, result: Dict[str, Any], required_fields: List[str]) -> None:
    """
    Validate that an agent returned all required fields.

    Args:
        agent_name: Name of the agent for error messages
        result: The agent's output dictionary
        required_fields: List of field names that must be present and non-empty

    Raises:
        AgentValidationError: If any required field is missing or empty
    """
    missing_fields = []
    empty_fields = []

    for field in required_fields:
        if field not in result:
            missing_fields.append(field)
        elif not result[field]:
            # Check if field is empty (empty string, empty list, empty dict, None, etc.)
            empty_fields.append(field)

    if missing_fields or empty_fields:
        error_parts = []
        if missing_fields:
            error_parts.append(f"missing fields: {', '.join(missing_fields)}")
        if empty_fields:
            error_parts.append(f"empty fields: {', '.join(empty_fields)}")

        error_msg = f"validation failed - {'; '.join(error_parts)}"
        logger.error(f"❌ {agent_name} {error_msg}")
        logger.error(f"   Result keys: {list(result.keys())}")
        raise AgentValidationError(agent_name, error_msg)

    logger.info(f"✅ {agent_name} validation passed - all required fields present")


def apply_originality_rewrites(original_text: str, flagged_passages: List[Dict[str, Any]]) -> str:
    """
    Apply originality rewrites programmatically if the agent didn't return complete rewritten_text.

    Args:
        original_text: The original SEO-optimized text
        flagged_passages: List of flagged passages with original and rewritten excerpts

    Returns:
        Text with all rewrites applied
    """
    if not flagged_passages:
        return original_text

    rewritten_text = original_text

    # Sort by length of original excerpt (longest first) to avoid substring replacement issues
    sorted_passages = sorted(
        flagged_passages,
        key=lambda p: len(p.get("original_excerpt", "") or p.get("original_text", "")),
        reverse=True
    )

    replacements_made = 0
    for passage in sorted_passages:
        original_excerpt = passage.get("original_excerpt", "") or passage.get("original_text", "")
        rewritten_excerpt = passage.get("rewritten_excerpt", "") or passage.get("rewritten_text", "")

        if original_excerpt and rewritten_excerpt and original_excerpt in rewritten_text:
            rewritten_text = rewritten_text.replace(original_excerpt, rewritten_excerpt, 1)
            replacements_made += 1
            logger.info(f"Applied originality rewrite {replacements_made}/{len(flagged_passages)}: {original_excerpt[:50]}... → {rewritten_excerpt[:50]}...")
        elif original_excerpt:
            logger.warning(f"Could not find original excerpt in text: {original_excerpt[:100]}...")

    if replacements_made > 0:
        logger.info(f"Applied {replacements_made} originality rewrites programmatically")
    else:
        logger.warning("No originality rewrites could be applied - original excerpts not found in text")

    return rewritten_text


def validate_content_length(agent_name: str, content: str, min_words: int = 100) -> None:
    """
    Validate content length to prevent truncation.

    Args:
        agent_name: Name of the agent for error messages
        content: The content text to validate
        min_words: Minimum acceptable word count

    Raises:
        ContentLengthError: If content is too short or empty
    """
    if not content:
        raise ContentLengthError(agent_name, 0, min_words)

    word_count = len(content.split())

    if word_count < min_words:
        raise ContentLengthError(agent_name, word_count, min_words)

    logger.info(f"✅ {agent_name} content length validation passed: {word_count} words")


def setup_pipeline_file_logger(pipeline_id: str) -> logging.FileHandler:
    """
    Create a dedicated file logger for this pipeline execution.

    Returns the file handler so it can be removed later.
    """
    log_dir = "/app/logs"

    # Ensure log directory exists
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception as e:
        # Fall back to /app if /app/logs fails
        log_dir = "/app"

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/pipeline_{pipeline_id}_{timestamp}.log"

    try:
        # Write header DIRECTLY to file first to ensure it works
        with open(log_file, 'w') as f:
            f.write("=" * 100 + "\n")
            f.write(f"PIPELINE EXECUTION LOG - {pipeline_id}\n")
            f.write(f"Log file: {log_file}\n")
            f.write(f"Started at: {datetime.utcnow().isoformat()}\n")
            f.write("=" * 100 + "\n\n")
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Now create logging file handler
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')  # Append mode
        file_handler.setLevel(logging.DEBUG)

        # Create detailed formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        # Add to root logger so all modules write to this file
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

        # Ensure root logger level allows all messages
        if root_logger.level > logging.DEBUG:
            root_logger.setLevel(logging.DEBUG)

        # Test that logging works
        logger.info(f"[PIPELINE] File logger initialized successfully")
        file_handler.flush()

        return file_handler

    except Exception as e:
        # Write error directly to a debug file
        try:
            error_file = f"{log_dir}/pipeline_error_{timestamp}.txt"
            with open(error_file, 'w') as f:
                f.write(f"Failed to setup file logging: {e}\n")
                import traceback
                f.write(traceback.format_exc())
                f.flush()
        except:
            pass
        return None


class PipelineStage(str, Enum):
    """Enumeration of pipeline stages."""
    TRENDS_KEYWORDS = "trends_keywords"
    TONE_OF_VOICE = "tone_of_voice"
    STRUCTURE_OUTLINE = "structure_outline"
    WRITER = "writer"
    SEO_OPTIMIZER = "seo_optimizer"
    ORIGINALITY_CHECK = "originality_check"
    FINAL_REVIEW = "final_review"


@dataclass
class PipelineState:
    """State container for the content pipeline."""

    # User input
    topic: str = ""
    content_type: str = "blog post"
    language: str = "English"
    audience: str = "general"
    goal: str = "awareness"
    brand_voice: str = "professional"
    length_constraints: str = "1000-1500 words"
    context_summary: str = ""
    user_id: int = 1

    # Document IDs for RAG retrieval
    style_document_ids: List[int] = field(default_factory=list)
    knowledge_document_ids: List[int] = field(default_factory=list)

    # API keys
    brave_search_api_key: Optional[str] = None

    # Agent outputs
    trends_and_keywords: Dict[str, Any] = field(default_factory=dict)
    tone_of_voice: Dict[str, Any] = field(default_factory=dict)
    outline: Dict[str, Any] = field(default_factory=dict)
    draft: Dict[str, Any] = field(default_factory=dict)
    seo_version: Dict[str, Any] = field(default_factory=dict)
    originality_check: Dict[str, Any] = field(default_factory=dict)
    final_review: Dict[str, Any] = field(default_factory=dict)

    # Pipeline metadata
    current_stage: str = ""
    completed_stages: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    # RAG tracking
    rag_chunks_used: List[Dict[str, Any]] = field(default_factory=list)
    rag_documents_used: List[Dict[str, Any]] = field(default_factory=list)

    # Brave Search tracking
    brave_requests_made: int = 0
    brave_results_received: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for JSON output."""
        return {
            "topic": self.topic,
            "content_type": self.content_type,
            "language": self.language,
            "audience": self.audience,
            "goal": self.goal,
            "brand_voice": self.brand_voice,
            "length_constraints": self.length_constraints,
            "context_summary": self.context_summary,
            "trends_and_keywords": self.trends_and_keywords,
            "tone_of_voice": self.tone_of_voice,
            "outline": self.outline,
            "draft": self.draft,
            "seo_version": self.seo_version,
            "originality_check": self.originality_check,
            "final_review": self.final_review,
            "rag_insights": self._build_rag_insights(),
            "brave_metrics": {
                "requests_made": self.brave_requests_made,
                "results_received": self.brave_results_received,
            },
        }

    def _build_rag_insights(self) -> Dict[str, Any]:
        """Build RAG insights from tracked chunks and documents."""
        if not self.rag_chunks_used:
            return {
                "enabled": False,
                "message": "No RAG documents were used for this content generation"
            }

        # Group chunks by document
        chunks_by_doc = {}
        for chunk in self.rag_chunks_used:
            doc_id = chunk.get("document_id")
            if doc_id not in chunks_by_doc:
                chunks_by_doc[doc_id] = []
            chunks_by_doc[doc_id].append(chunk)

        # Calculate statistics
        total_chunks = len(self.rag_chunks_used)
        avg_score = sum(c.get("score", 0) for c in self.rag_chunks_used) / total_chunks if total_chunks > 0 else 0

        # Build document summary
        documents_summary = []
        for doc in self.rag_documents_used:
            doc_id = doc.get("id")
            doc_chunks = chunks_by_doc.get(doc_id, [])
            documents_summary.append({
                "id": doc_id,
                "name": doc.get("name", "Unknown"),
                "filename": doc.get("filename", ""),
                "chunks_used": len(doc_chunks),
                "avg_relevance": sum(c.get("score", 0) for c in doc_chunks) / len(doc_chunks) if doc_chunks else 0,
                "influence_percentage": (len(doc_chunks) / total_chunks * 100) if total_chunks > 0 else 0
            })

        # Sort by influence
        documents_summary.sort(key=lambda x: x["influence_percentage"], reverse=True)

        # Calculate style similarity if we have generated content
        style_similarity = None
        sentence_attribution = None
        generated_text = self._get_generated_text()

        if generated_text:
            try:
                similarity_analyzer = RAGSimilarityAnalyzer()

                # Calculate document-level similarity
                style_similarity = similarity_analyzer.calculate_document_similarity(
                    generated_text,
                    self.rag_chunks_used
                )

                # Calculate sentence-level attribution (limit to first 20 sentences for performance)
                sentence_attribution = similarity_analyzer.calculate_sentence_attribution(
                    generated_text,
                    self.rag_chunks_used[:20],  # Use top 20 chunks for attribution
                    threshold=0.6
                )

                logger.info(f"Style similarity calculated: {style_similarity.get('overall_similarity', 0):.3f}")
                logger.info(f"Attributed {sum(1 for s in sentence_attribution if s.get('attributed'))} / {len(sentence_attribution)} sentences")

            except Exception as e:
                logger.warning(f"Failed to calculate style similarity: {e}")

        insights = {
            "enabled": True,
            "total_chunks_retrieved": total_chunks,
            "total_documents_used": len(self.rag_documents_used),
            "average_relevance_score": round(avg_score, 3),
            "documents": documents_summary,
            "chunks_by_stage": self._group_chunks_by_stage(),
            "detailed_chunks": self.rag_chunks_used[:50],  # Limit to 50 for response size
        }

        # Add advanced analytics if available
        if style_similarity:
            insights["style_similarity"] = style_similarity

        if sentence_attribution:
            # Only include attribution summary (not full list for response size)
            total_sentences = len(sentence_attribution)
            attributed_count = sum(1 for s in sentence_attribution if s.get("attributed"))
            insights["sentence_attribution"] = {
                "total_sentences": total_sentences,
                "attributed_sentences": attributed_count,
                "attribution_percentage": round((attributed_count / total_sentences * 100) if total_sentences > 0 else 0, 1),
                "details": sentence_attribution[:30]  # First 30 for details view
            }

        return insights

    def _get_generated_text(self) -> str:
        """Extract the final generated text from pipeline state."""
        # Try to get the final text from various stages
        if self.final_review and "final_text" in self.final_review:
            return self.final_review["final_text"]
        elif self.seo_version and "optimized_text" in self.seo_version:
            return self.seo_version["optimized_text"]
        elif self.draft and "full_text" in self.draft:
            return self.draft["full_text"]
        return ""

    def _group_chunks_by_stage(self) -> Dict[str, int]:
        """Group chunks by which pipeline stage used them."""
        stages = {}
        for chunk in self.rag_chunks_used:
            stage = chunk.get("used_in_stage", "unknown")
            stages[stage] = stages.get(stage, 0) + 1
        return stages

    def _format_chunks_for_context(self, chunks: List[Dict[str, Any]], max_chunks: int = 5) -> str:
        """Format retrieved chunks into a brief context string."""
        formatted = []
        for chunk in chunks[:max_chunks]:
            snippet = (chunk.get("text", "") or "")[:400].replace("\n", " ")
            formatted.append(
                f"{chunk.get('document_name', 'Document')} (score: {chunk.get('score', 0):.2f}): {snippet}"
            )

        return "\n".join(formatted)

    def _parse_chunk_json(self, chunk_blob: str, stage_name: str) -> List[Dict[str, Any]]:
        """Parse a JSON string of chunks into metadata dictionaries for tracking.

        Some retrievers return JSON strings instead of structured metadata. This helper
        attempts to parse those strings and normalizes the output so we can still track
        document usage and surface RAG insights.
        """
        if not chunk_blob:
            return []

        try:
            data = json.loads(chunk_blob)
            if not isinstance(data, list):
                return []

            parsed_chunks = []
            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    continue

                parsed_chunks.append({
                    "text": item.get("text", ""),
                    "document_id": item.get("document_id") or item.get("doc_id"),
                    "document_name": item.get("document_name", "Unknown"),
                    "score": item.get("score", 0.0),
                    "chunk_id": item.get("chunk_id", f"parsed_{stage_name}_{idx}"),
                    "position": item.get("position", idx),
                })

            return parsed_chunks
        except (json.JSONDecodeError, TypeError):
            return []

    def _build_fallback_chunks(
        self,
        state: PipelineState,
        document_ids: List[int],
        text_blob: Any,
        stage_name: str,
    ) -> List[Dict[str, Any]]:
        """Create minimal chunk metadata when retrievers omit it.

        This ensures we still mark selected RAG documents as used when the
        retriever returns only raw text (or nothing parseable) by attributing the
        provided content to the chosen documents. The caller is responsible for
        passing already-tracked document IDs so we can label names accurately.
        """

        if not document_ids or not text_blob:
            return []

        snippet = str(text_blob)[:500]
        fallback_chunks: List[Dict[str, Any]] = []

        for idx, doc_id in enumerate(document_ids):
            doc_meta = next((d for d in state.rag_documents_used if d.get("id") == doc_id), {})
            fallback_chunks.append(
                {
                    "text": snippet,
                    "document_id": doc_id,
                    "document_name": doc_meta.get("name", "Unknown"),
                    "score": 0.0,
                    "chunk_id": f"fallback_{stage_name}_{doc_id}_{idx}",
                    "position": idx,
                }
            )

        return fallback_chunks


class ContentPipelineOrchestrator:
    """
    Orchestrates the multi-agent content creation pipeline.

    Coordinates 7 agents in sequence:
    1. Trends & Keywords Agent
    2. Tone-of-Voice RAG Agent
    3. Structure & Outline Agent
    4. Writer Agent
    5. SEO Optimizer Agent
    6. Originality & Plagiarism Agent
    7. Final Reviewer Agent
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        rag_retriever: Optional[Callable] = None,
        on_stage_complete: Optional[Callable] = None,
        on_stage_start: Optional[Callable] = None,
        on_checkpoint_reached: Optional[Callable] = None,
        agent_logger: Optional[AgentLogger] = None,
        project_name: Optional[str] = None,
    ) -> None:
        """
        Initialize the orchestrator.

        Args:
            llm_client: LLM client for agent generation
            rag_retriever: Optional function to retrieve style examples from RAG
            on_stage_complete: Callback when a stage completes (for streaming updates)
            on_stage_start: Callback when a stage starts
            on_checkpoint_reached: Callback when checkpoint is reached (for manual approval)
            agent_logger: Optional logger for capturing agent communication
            project_name: Optional project name for RAG filtering
        """
        self.llm_client = llm_client
        self.rag_retriever = rag_retriever
        self.on_stage_complete = on_stage_complete
        self.on_stage_start = on_stage_start
        self.on_checkpoint_reached = on_checkpoint_reached
        self.agent_logger = agent_logger
        self.project_name = project_name

        # Initialize agents
        self.trends_agent = TrendsKeywordsAgent(llm_client=llm_client)
        self.tone_agent = ToneOfVoiceAgent(llm_client=llm_client)
        self.structure_agent = StructureOutlineAgent(llm_client=llm_client)
        self.writer_agent = WriterAgent(llm_client=llm_client)
        self.seo_agent = SEOOptimizerAgent(llm_client=llm_client)
        self.originality_agent = OriginalityPlagiarismAgent(llm_client=llm_client)
        self.reviewer_agent = FinalReviewerAgent(llm_client=llm_client)

        # Circuit breaker state: tracks consecutive failures per agent
        self.agent_failure_counts = {}
        self.circuit_breaker_threshold = 2  # Skip agent after 2 consecutive failures

    async def _retry_agent_with_fallback(
        self,
        agent_callable: Callable,
        agent_name: str,
        max_retries: int = 2,
        **agent_kwargs
    ) -> Dict[str, Any]:
        """
        Retry agent execution with increasingly aggressive error recovery.

        Strategy:
        - Attempt 1: Normal execution
        - Attempt 2: Truncate large text inputs, add JSON reminder to prompt
        - Attempt 3 (final): Minimal input, explicit JSON format reminder

        Args:
            agent_callable: The agent's run() method
            agent_name: Name of the agent for logging
            max_retries: Maximum number of retry attempts (default 2, total 3 attempts)
            **agent_kwargs: Arguments to pass to the agent

        Returns:
            Agent result dict

        Raises:
            Exception: If all retries fail
        """
        import asyncio

        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                if attempt == 0:
                    # First attempt: normal execution
                    logger.info(f"🔄 {agent_name}: Attempt {attempt + 1}/{max_retries + 1} (normal)")
                    result = await agent_callable(**agent_kwargs)

                    # Reset failure count on success
                    self.agent_failure_counts[agent_name] = 0
                    return result

                elif attempt == 1:
                    # Second attempt: truncate large inputs and add JSON reminder
                    logger.warning(f"🔄 {agent_name}: Attempt {attempt + 1}/{max_retries + 1} (truncated input)")
                    truncated_kwargs = self._truncate_large_inputs(agent_kwargs.copy(), max_chars=5000)

                    # Add explicit JSON reminder if agent has a text input field
                    if 'context_summary' in truncated_kwargs:
                        truncated_kwargs['context_summary'] = (
                            truncated_kwargs.get('context_summary', '') +
                            "\n\n**CRITICAL REMINDER**: You MUST respond with ONLY valid JSON. "
                            "Ensure ALL properties have commas between them. Double-check before responding."
                        )

                    result = await agent_callable(**truncated_kwargs)

                    # Reset failure count on success
                    self.agent_failure_counts[agent_name] = 0
                    logger.info(f"✅ {agent_name}: Succeeded on retry with truncated input")
                    return result

                else:
                    # Final attempt: minimal input, explicit JSON format
                    logger.warning(f"🔄 {agent_name}: Attempt {attempt + 1}/{max_retries + 1} (minimal input, last try)")
                    minimal_kwargs = self._minimize_inputs(agent_kwargs.copy())

                    result = await agent_callable(**minimal_kwargs)

                    # Reset failure count on success
                    self.agent_failure_counts[agent_name] = 0
                    logger.info(f"✅ {agent_name}: Succeeded on final retry with minimal input")
                    return result

            except Exception as e:
                last_exception = e
                error_msg = str(e)
                logger.error(f"❌ {agent_name}: Attempt {attempt + 1}/{max_retries + 1} failed: {error_msg[:200]}")

                # Track failure count
                self.agent_failure_counts[agent_name] = self.agent_failure_counts.get(agent_name, 0) + 1

                # If this was the last attempt, raise
                if attempt == max_retries:
                    logger.error(f"💥 {agent_name}: All {max_retries + 1} attempts failed")
                    raise last_exception

                # Wait before retry (exponential backoff)
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.info(f"⏳ Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)

        # Should never reach here, but just in case
        raise last_exception

    def _truncate_large_inputs(self, kwargs: Dict[str, Any], max_chars: int = 5000) -> Dict[str, Any]:
        """
        Truncate large text inputs to prevent LLM overload.

        Targets fields that commonly contain large amounts of text.
        """
        text_fields = ['context_summary', 'seo_version', 'outline', 'full_text', 'optimized_text']

        for field in text_fields:
            if field in kwargs:
                value = kwargs[field]

                # Handle dict with text fields
                if isinstance(value, dict):
                    if 'optimized_text' in value and isinstance(value['optimized_text'], str):
                        original_len = len(value['optimized_text'])
                        if original_len > max_chars:
                            value['optimized_text'] = value['optimized_text'][:max_chars] + "\n\n[...truncated for retry...]"
                            logger.info(f"  Truncated {field}.optimized_text: {original_len} → {len(value['optimized_text'])} chars")
                    if 'full_text' in value and isinstance(value['full_text'], str):
                        original_len = len(value['full_text'])
                        if original_len > max_chars:
                            value['full_text'] = value['full_text'][:max_chars] + "\n\n[...truncated for retry...]"
                            logger.info(f"  Truncated {field}.full_text: {original_len} → {len(value['full_text'])} chars")

                # Handle plain strings
                elif isinstance(value, str):
                    original_len = len(value)
                    if original_len > max_chars:
                        kwargs[field] = value[:max_chars] + "\n\n[...truncated for retry...]"
                        logger.info(f"  Truncated {field}: {original_len} → {len(kwargs[field])} chars")

        return kwargs

    def _minimize_inputs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Minimize inputs to bare essentials for final retry attempt.

        Keeps only required fields and heavily truncates optional content.
        """
        # Further reduce text fields to 2000 chars max
        truncated = self._truncate_large_inputs(kwargs, max_chars=2000)

        # Remove optional fields that might be causing issues
        optional_fields = ['context_summary', 'trends_keywords', 'knowledge_chunks']
        for field in optional_fields:
            if field in truncated and truncated[field]:
                truncated[field] = ""
                logger.info(f"  Removed optional field: {field}")

        return truncated

    def _check_circuit_breaker(self, agent_name: str) -> bool:
        """
        Check if circuit breaker is open for an agent.

        Returns:
            True if agent should be skipped (circuit open)
            False if agent should run (circuit closed)
        """
        failure_count = self.agent_failure_counts.get(agent_name, 0)

        if failure_count >= self.circuit_breaker_threshold:
            logger.warning(
                f"⚡ Circuit breaker OPEN for {agent_name}: "
                f"{failure_count} consecutive failures >= threshold {self.circuit_breaker_threshold}"
            )
            return True

        return False

    def _create_fallback_result(self, agent_name: str, previous_output: Any, reason: str) -> Dict[str, Any]:
        """
        Create a fallback result when an agent is skipped or fails.

        Args:
            agent_name: Name of the skipped agent
            previous_output: Output from previous stage to pass through
            reason: Reason for fallback

        Returns:
            Fallback result dict
        """
        logger.info(f"🔄 Creating fallback result for {agent_name}: {reason}")

        # For originality agent, create a minimal valid response
        if "originality" in agent_name.lower():
            return {
                "originality_score": "unknown",
                "risk_summary": f"Agent skipped ({reason}). Using previous version.",
                "rewritten_text": previous_output.get("optimized_text", "") if isinstance(previous_output, dict) else str(previous_output),
                "flagged_passages": [],
                "_skipped": True,
                "_skip_reason": reason
            }

        # For final reviewer agent
        elif "reviewer" in agent_name.lower() or "final" in agent_name.lower():
            return {
                "final_text": previous_output.get("rewritten_text", previous_output.get("optimized_text", "")) if isinstance(previous_output, dict) else str(previous_output),
                "change_log": [f"Agent skipped ({reason})"],
                "editor_notes_for_user": ["Content may not have been fully reviewed due to processing issues"],
                "suggested_variants": [],
                "_skipped": True,
                "_skip_reason": reason
            }

        # Generic fallback for other agents
        else:
            return {
                "_skipped": True,
                "_skip_reason": reason,
                "_previous_output": previous_output
            }

    async def run(
        self,
        topic: str,
        content_type: str = "blog post",
        audience: str = "general",
        goal: str = "awareness",
        brand_voice: str = "professional",
        language: str = "English",
        length_constraints: str = "1000-1500 words",
        context_summary: str = "",
        user_id: int = 1,
        style_document_ids: List[int] = None,
        knowledge_document_ids: List[int] = None,
        checkpoint_mode: str = "automatic",
        checkpoint_session_id: Optional[str] = None,
        pipeline_id: Optional[str] = None,
        db: Optional[Any] = None,
        execution_id: Optional[int] = None,
        brave_search_api_key: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run the complete content pipeline.

        Args:
            topic: The subject/topic for content creation
            content_type: Type of content (blog post, LinkedIn post, etc.)
            audience: Target audience description
            goal: Content goal (awareness, lead gen, etc.)
            brand_voice: Brand voice guidelines
            language: Output language
            length_constraints: Length requirements
            context_summary: Additional context from user
            style_document_ids: RAG document IDs for tone/voice/style analysis
            knowledge_document_ids: RAG document IDs for content/knowledge retrieval
            checkpoint_mode: Pipeline execution mode ("automatic" or "checkpoint")
            checkpoint_session_id: Session ID for checkpoint mode (if resuming)
            pipeline_id: Unique ID for this pipeline execution (for logging)
            db: Database session for activity tracking
            execution_id: Pipeline execution ID for activity tracking
            brave_search_api_key: Brave Search API key for web search capabilities

        Returns:
            Complete pipeline output as dictionary
        """
        # Setup file logging for this pipeline execution
        file_handler = None
        if pipeline_id:
            file_handler = setup_pipeline_file_logger(pipeline_id)

        # Initialize state
        state = PipelineState(
            topic=topic,
            content_type=content_type,
            language=language,
            audience=audience,
            goal=goal,
            brand_voice=brand_voice,
            length_constraints=length_constraints,
            context_summary=context_summary,
            user_id=user_id,
            style_document_ids=style_document_ids or [],
            knowledge_document_ids=knowledge_document_ids or [],
            brave_search_api_key=brave_search_api_key,
        )

        # Initialize activity tracker if database session is available
        self.activity_tracker = None
        if db and execution_id:
            self.activity_tracker = AgentActivityTracker(db, execution_id)
            logger.info(f"Activity tracking enabled for execution {execution_id}")

        # Store checkpoint mode info
        is_checkpoint_mode = (checkpoint_mode == "checkpoint")
        session_id = checkpoint_session_id or ""

        try:
            # Stage 1: Trends & Keywords
            logger.info("=== Starting Stage 1: Trends & Keywords ===")
            state = await self._run_trends_keywords(state)
            logger.info("=== Completed Stage 1: Trends & Keywords ===")
            if is_checkpoint_mode:
                action = await self._notify_checkpoint_reached(
                    PipelineStage.TRENDS_KEYWORDS,
                    state.trends_and_keywords,
                    state,
                    session_id
                )
                if action.get("action") == "cancel":
                    return state.to_dict()
                # Handle other actions (edit, restart, skip) if needed

            # Stage 2: Tone of Voice
            logger.info("=== Starting Stage 2: Tone of Voice ===")
            state = await self._run_tone_of_voice(state)
            logger.info("=== Completed Stage 2: Tone of Voice ===")
            if is_checkpoint_mode:
                action = await self._notify_checkpoint_reached(
                    PipelineStage.TONE_OF_VOICE,
                    state.tone_of_voice,
                    state,
                    session_id
                )
                if action.get("action") == "cancel":
                    return state.to_dict()

            # Stage 3: Structure & Outline
            logger.info("=== Starting Stage 3: Structure & Outline ===")
            state = await self._run_structure_outline(state)
            logger.info("=== Completed Stage 3: Structure & Outline ===")
            if is_checkpoint_mode:
                action = await self._notify_checkpoint_reached(
                    PipelineStage.STRUCTURE_OUTLINE,
                    state.outline,
                    state,
                    session_id
                )
                if action.get("action") == "cancel":
                    return state.to_dict()

            # Stage 4: Writer
            logger.info("=== Starting Stage 4: Writer ===")
            state = await self._run_writer(state)
            logger.info("=== Completed Stage 4: Writer ===")
            if is_checkpoint_mode:
                action = await self._notify_checkpoint_reached(
                    PipelineStage.WRITER,
                    state.draft,
                    state,
                    session_id
                )
                if action.get("action") == "cancel":
                    return state.to_dict()

            # Stage 5: SEO Optimizer
            logger.info("=== Starting Stage 5: SEO Optimizer ===")
            state = await self._run_seo_optimizer(state)
            logger.info("=== Completed Stage 5: SEO Optimizer ===")
            if is_checkpoint_mode:
                action = await self._notify_checkpoint_reached(
                    PipelineStage.SEO_OPTIMIZER,
                    state.seo_version,
                    state,
                    session_id
                )
                if action.get("action") == "cancel":
                    return state.to_dict()

            # Stage 6: Originality Check
            logger.info("=== Starting Stage 6: Originality Check ===")
            state = await self._run_originality_check(state)
            logger.info("=== Completed Stage 6: Originality Check ===")
            if is_checkpoint_mode:
                action = await self._notify_checkpoint_reached(
                    PipelineStage.ORIGINALITY_CHECK,
                    state.originality_check,
                    state,
                    session_id
                )
                if action.get("action") == "cancel":
                    return state.to_dict()

            # Stage 7: Final Review
            logger.info("=== Starting Stage 7: Final Review ===")
            state = await self._run_final_review(state)
            logger.info("=== Completed Stage 7: Final Review ===")
            if is_checkpoint_mode:
                action = await self._notify_checkpoint_reached(
                    PipelineStage.FINAL_REVIEW,
                    state.final_review,
                    state,
                    session_id
                )
                if action.get("action") == "cancel":
                    return state.to_dict()

        except Exception as e:
            error_msg = f"Pipeline error at stage {state.current_stage}: {e}"
            logger.error(error_msg)
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception details: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

            state.errors.append({
                "stage": state.current_stage,
                "error": str(e),
                "error_type": type(e).__name__
            })

            # Cleanup file handler before re-raising
            if file_handler:
                logger.info(f"=" * 100)
                logger.info(f"PIPELINE FAILED - Check logs above for details")
                logger.info(f"=" * 100)
                logging.getLogger().removeHandler(file_handler)
                file_handler.close()

            # Re-raise the exception so it can be caught by the stream handler
            # This will allow the frontend to see the actual error
            raise
        finally:
            # Always cleanup file handler
            if file_handler:
                logger.info(f"=" * 100)
                logger.info(f"PIPELINE COMPLETED")
                logger.info(f"Finished at: {datetime.utcnow().isoformat()}")
                logger.info(f"=" * 100)
                logging.getLogger().removeHandler(file_handler)
                file_handler.close()

        return state.to_dict()

    async def _run_trends_keywords(self, state: PipelineState) -> PipelineState:
        """Run the Trends & Keywords agent."""
        stage = PipelineStage.TRENDS_KEYWORDS
        state.current_stage = stage.value
        start_time = time.time()

        if self.on_stage_start:
            await self._notify_stage_start(stage, "Researching trends and keywords...")

        logger.info(f"Running {stage.value} agent")

        # Input context for logging
        input_context = {
            "topic": state.topic,
            "content_type": state.content_type,
            "audience": state.audience,
            "goal": state.goal,
            "brand_voice": state.brand_voice,
            "language": state.language,
            "length_constraints": state.length_constraints,
        }

        # Start activity tracking
        if self.activity_tracker:
            self.activity_tracker.start_agent(
                "Trends & Keywords Researcher",
                stage.value,
                input_summary=input_context
            )
            self.activity_tracker.log_decision(f"Analyzing trends for: {state.topic}")

        try:
            result = await self.trends_agent.run(
                topic=state.topic,
                content_type=state.content_type,
                audience=state.audience,
                goal=state.goal,
                brand_voice=state.brand_voice,
                language=state.language,
                length_constraints=state.length_constraints,
                context_summary=state.context_summary,
                brave_search_api_key=state.brave_search_api_key,
            )

            # Log the agent call
            await self._log_agent_call(stage, self.trends_agent, result, start_time, input_context)

            # Validate output
            validate_agent_output("Trends & Keywords Agent", result, ["primary_keywords", "angle_ideas"])

            # Track Brave metrics if present
            if '_brave_metrics' in result:
                brave_metrics = result.pop('_brave_metrics')  # Remove from result to not pollute state
                state.brave_requests_made += brave_metrics.get('requests_made', 0)
                state.brave_results_received += brave_metrics.get('results_received', 0)
                logger.info(f"📊 Brave Search: {brave_metrics.get('requests_made', 0)} requests, {brave_metrics.get('results_received', 0)} results")

            state.trends_and_keywords = result
            state.completed_stages.append(stage.value)

            # Complete activity tracking
            if self.activity_tracker:
                primary_kw = result.get('primary_keywords', [])
                self.activity_tracker.log_decision(f"Identified {len(primary_kw)} primary keywords")
                self.activity_tracker.complete_agent(
                    output_summary={
                        "primary_keywords_count": len(primary_kw),
                        "angle_ideas_count": len(result.get('angle_ideas', [])),
                        "keywords": primary_kw[:5]  # Top 5 for summary
                    }
                )

            if self.on_stage_complete:
                await self._notify_stage_complete(stage, result)

            logger.info(f"Completed {stage.value}: found {len(result.get('primary_keywords', []))} primary keywords")

        except Exception as e:
            if self.activity_tracker:
                self.activity_tracker.fail_agent(str(e))
            await self._log_stage_failure(
                stage,
                str(e),
                start_time,
                agent=self.trends_agent,
                input_context=input_context
            )
            raise

        return state

    async def _run_tone_of_voice(self, state: PipelineState) -> PipelineState:
        """Run the Tone-of-Voice RAG agent."""
        stage = PipelineStage.TONE_OF_VOICE
        state.current_stage = stage.value
        start_time = time.time()

        if self.on_stage_start:
            await self._notify_stage_start(stage, "Analyzing brand voice and style...")

        logger.info(f"Running {stage.value} agent")

        # Retrieve style examples from RAG if available
        retrieved_style_chunks = ""
        rag_chunks_metadata = []

        if self.rag_retriever:
            tracked_style_chunks = False
            try:
                # Pass full context for enhanced RAG with query expansion
                # Include document IDs to filter by specific documents (if provided)
                retriever_kwargs = {
                    "query": f"brand voice style examples for {state.topic}",
                    "collection": "brand_voice",
                    "k": 10,
                    "topic": state.topic,
                    "content_type": state.content_type,
                    "audience": state.audience,
                    "brand_voice": state.brand_voice,
                    "goal": state.goal,
                    "user_id": state.user_id,
                    "project_name": self.project_name,  # Filter by project
                    "return_metadata": True,  # Request full metadata
                }

                # Only add document_ids filter if specific documents were selected
                if state.style_document_ids:
                    retriever_kwargs["document_ids"] = state.style_document_ids
                    logger.info(f"Retrieving style from {len(state.style_document_ids)} selected documents")

                    # Fetch document details for tracking
                    await self._track_rag_documents(state, state.style_document_ids)
                else:
                    logger.info("Retrieving style from default RAG vector store")

                rag_result = await self.rag_retriever(**retriever_kwargs)

                # Handle different response formats
                if isinstance(rag_result, dict) and "chunks" in rag_result:
                    # Enhanced RAG returns dict with chunks and metadata
                    retrieved_style_chunks = rag_result.get("chunks", "")
                    rag_chunks_metadata = rag_result.get("metadata", [])
                elif isinstance(rag_result, tuple):
                    # Tuple format: (text, metadata)
                    retrieved_style_chunks, rag_chunks_metadata = rag_result
                else:
                    # Simple string format
                    retrieved_style_chunks = rag_result

                # Track retrieved chunks (parse JSON blobs when metadata is missing)
                if not rag_chunks_metadata and isinstance(retrieved_style_chunks, str):
                    rag_chunks_metadata = self._parse_chunk_json(retrieved_style_chunks, "tone_of_voice")

                if rag_chunks_metadata:
                    await self._track_rag_chunks(state, rag_chunks_metadata, "tone_of_voice")
                    tracked_style_chunks = True

                # If the retriever returned unstructured text, still attribute it to the selected docs
                if (
                    not tracked_style_chunks
                    and state.style_document_ids
                    and retrieved_style_chunks
                ):
                    fallback_chunks = self._build_fallback_chunks(
                        state,
                        state.style_document_ids,
                        retrieved_style_chunks,
                        "tone_of_voice",
                    )
                    await self._track_rag_chunks(state, fallback_chunks, "tone_of_voice")
                    tracked_style_chunks = True

            except TypeError:
                # Fallback for simple retrievers that don't accept extra params
                try:
                    retrieved_style_chunks = await self.rag_retriever(
                        query=f"brand voice style examples for {state.topic}",
                        collection="brand_voice"
                    )

                    # Attempt to parse simple JSON string responses
                    if retrieved_style_chunks and not rag_chunks_metadata and isinstance(retrieved_style_chunks, str):
                        rag_chunks_metadata = self._parse_chunk_json(retrieved_style_chunks, "tone_of_voice")
                except Exception as e:
                    logger.warning(f"RAG retrieval failed: {e}")
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")

            if not tracked_style_chunks and rag_chunks_metadata:
                await self._track_rag_chunks(state, rag_chunks_metadata, "tone_of_voice")

            # Validation: If user selected specific style documents, ensure we retrieved content
            if state.style_document_ids and not retrieved_style_chunks:
                warning_msg = f"⚠️ User selected {len(state.style_document_ids)} style documents but RAG retrieval returned no content. Style analysis may be generic."
                logger.warning(warning_msg)
                if self.activity_tracker:
                    self.activity_tracker.add_warning(warning_msg)

        # Input context for logging
        input_context = {
            "topic": state.topic,
            "content_type": state.content_type,
            "audience": state.audience,
            "goal": state.goal,
            "brand_voice": state.brand_voice,
            "language": state.language,
            "has_rag_chunks": bool(retrieved_style_chunks),
        }

        # Start activity tracking
        if self.activity_tracker:
            self.activity_tracker.start_agent(
                "Tone of Voice Analyzer",
                stage.value,
                input_summary=input_context
            )
            if state.style_document_ids:
                self.activity_tracker.log_decision(f"Analyzing style from {len(state.style_document_ids)} brand documents")

            # Log RAG usage
            if rag_chunks_metadata:
                for chunk in rag_chunks_metadata[:10]:  # Log top 10 chunks
                    self.activity_tracker.log_rag_usage(
                        doc_id=chunk.get("document_id", 0),
                        doc_name=chunk.get("document_name", "Brand Voice Document"),
                        chunks_used=1,
                        influence_score=chunk.get("similarity", 0.0),
                        purpose="Brand voice analysis"
                    )

        try:
            result = await self.tone_agent.run(
                topic=state.topic,
                content_type=state.content_type,
                audience=state.audience,
                goal=state.goal,
                brand_voice=state.brand_voice,
                language=state.language,
                retrieved_style_chunks=retrieved_style_chunks,
                context_summary=state.context_summary,
            )

            # Log the agent call
            await self._log_agent_call(stage, self.tone_agent, result, start_time, input_context)

            state.tone_of_voice = result
            state.completed_stages.append(stage.value)

            # Complete activity tracking
            if self.activity_tracker:
                profile = result.get("style_profile", {})
                self.activity_tracker.log_decision(f"Defined style profile with {profile.get('formality_level', 'N/A')} formality")
                self.activity_tracker.complete_agent(
                    output_summary={
                        "formality_level": profile.get("formality_level"),
                        "person_preference": profile.get("person_preference"),
                        "style_docs_used": len(rag_chunks_metadata)
                    }
                )

            if self.on_stage_complete:
                await self._notify_stage_complete(stage, result)

            logger.info(f"Completed {stage.value}: style profile created")

        except Exception as e:
            if self.activity_tracker:
                self.activity_tracker.fail_agent(str(e))
            await self._log_stage_failure(
                stage,
                str(e),
                start_time,
                agent=self.tone_agent,
                input_context=input_context
            )
            raise

        return state

    async def _run_structure_outline(self, state: PipelineState) -> PipelineState:
        """Run the Structure & Outline agent."""
        stage = PipelineStage.STRUCTURE_OUTLINE
        state.current_stage = stage.value
        start_time = time.time()

        if self.on_stage_start:
            await self._notify_stage_start(stage, "Creating content structure...")

        logger.info(f"Running {stage.value} agent")

        # Safely convert state fields to dicts
        tone_of_voice = safe_dict(state.tone_of_voice)
        trends_and_keywords = safe_dict(state.trends_and_keywords)

        # Extract style profile from tone_of_voice result
        style_profile = tone_of_voice.get("style_profile", {})

        # Input context for logging
        input_context = {
            "topic": state.topic,
            "content_type": state.content_type,
            "audience": state.audience,
            "goal": state.goal,
            "length_constraints": state.length_constraints,
            "keywords_count": len(trends_and_keywords.get("primary_keywords", [])),
        }

        # Start activity tracking
        if self.activity_tracker:
            self.activity_tracker.start_agent(
                "Structure & Outline Architect",
                stage.value,
                input_summary=input_context
            )
            self.activity_tracker.log_decision(f"Building outline structure for {state.content_type}")

        try:
            result = await self.structure_agent.run(
                topic=state.topic,
                content_type=state.content_type,
                audience=state.audience,
                goal=state.goal,
                brand_voice=state.brand_voice,
                language=state.language,
                length_constraints=state.length_constraints,
                context_summary=state.context_summary,
                trends_keywords=state.trends_and_keywords,
                style_profile=style_profile,
            )

            # Log the agent call
            await self._log_agent_call(stage, self.structure_agent, result, start_time, input_context)

            # Validate output
            validate_agent_output("Structure & Outline Agent", result, ["sections"])

            state.outline = result
            state.completed_stages.append(stage.value)

            # Complete activity tracking
            if self.activity_tracker:
                sections = result.get('sections', [])
                self.activity_tracker.log_decision(f"Created {len(sections)} main sections")
                self.activity_tracker.complete_agent(
                    output_summary={
                        "sections_count": len(sections),
                        "content_promise": result.get("content_promise", "")[:100]
                    }
                )

            if self.on_stage_complete:
                await self._notify_stage_complete(stage, result)

            logger.info(f"Completed {stage.value}: {len(result.get('sections', []))} sections created")

        except Exception as e:
            if self.activity_tracker:
                self.activity_tracker.fail_agent(str(e))
            await self._log_stage_failure(
                stage,
                str(e),
                start_time,
                agent=self.structure_agent,
                input_context=input_context
            )
            raise

        return state

    async def _run_writer(self, state: PipelineState) -> PipelineState:
        """Run the Writer agent."""
        stage = PipelineStage.WRITER
        state.current_stage = stage.value
        start_time = time.time()

        if self.on_stage_start:
            await self._notify_stage_start(stage, "Writing content...")

        logger.info(f"Running {stage.value} agent")

        # Safely convert state fields to dicts
        tone_of_voice = safe_dict(state.tone_of_voice)

        style_profile = tone_of_voice.get("style_profile", {})
        knowledge_context = ""
        knowledge_chunks_metadata: List[Dict[str, Any]] = []

        if self.rag_retriever and state.knowledge_document_ids:
            try:
                logger.info(f"📚 WRITER AGENT: Retrieving knowledge from {len(state.knowledge_document_ids)} documents: {state.knowledge_document_ids}")
                await self._track_rag_documents(state, state.knowledge_document_ids)

                rag_result = await self.rag_retriever(
                    query=f"supporting facts for {state.topic}",
                    collection="knowledge_base",
                    k=12,
                    topic=state.topic,
                    content_type=state.content_type,
                    audience=state.audience,
                    brand_voice=state.brand_voice,
                    goal=state.goal,
                    user_id=state.user_id,
                    document_ids=state.knowledge_document_ids,
                    project_name=self.project_name,  # Filter by project
                    return_metadata=True,
                )

                if isinstance(rag_result, dict):
                    knowledge_context = rag_result.get("chunks", "") or ""
                    knowledge_chunks_metadata = rag_result.get("metadata", []) or []
                    logger.info(f"📚 WRITER AGENT: Retrieved {len(knowledge_chunks_metadata)} chunks from RAG")
                elif isinstance(rag_result, tuple):
                    knowledge_context, knowledge_chunks_metadata = rag_result
                    logger.info(f"📚 WRITER AGENT: Retrieved {len(knowledge_chunks_metadata)} chunks from RAG (tuple format)")
                elif isinstance(rag_result, str):
                    knowledge_context = rag_result
                    logger.info(f"📚 WRITER AGENT: Retrieved RAG content as string ({len(knowledge_context)} chars)")

                if not knowledge_chunks_metadata and isinstance(knowledge_context, str):
                    knowledge_chunks_metadata = self._parse_chunk_json(knowledge_context, "writer")

                if knowledge_chunks_metadata:
                    await self._track_rag_chunks(state, knowledge_chunks_metadata, "writer")
                    knowledge_context = self._format_chunks_for_context(knowledge_chunks_metadata)
                    logger.info(f"✅ WRITER AGENT: Using {len(knowledge_chunks_metadata)} knowledge chunks in content generation")

                if not knowledge_chunks_metadata and knowledge_context:
                    fallback_chunks = self._build_fallback_chunks(
                        state,
                        state.knowledge_document_ids,
                        knowledge_context,
                        "writer",
                    )
                    if fallback_chunks:
                        await self._track_rag_chunks(state, fallback_chunks, "writer")
                        logger.info(f"✅ WRITER AGENT: Using {len(fallback_chunks)} fallback chunks")

                # Validation: Ensure we retrieved content when documents were selected
                if not knowledge_context:
                    error_msg = f"❌ WRITER AGENT: No knowledge context retrieved despite selecting {len(state.knowledge_document_ids)} documents! Content may lack factual grounding."
                    logger.error(error_msg)
                    if self.activity_tracker:
                        self.activity_tracker.add_warning(error_msg)

            except Exception as e:
                error_msg = f"❌ WRITER AGENT: Knowledge RAG retrieval failed: {e}"
                logger.error(error_msg, exc_info=True)
                if self.activity_tracker:
                    self.activity_tracker.add_warning(error_msg)

        # Input context for logging
        input_context = {
            "topic": state.topic,
            "content_type": state.content_type,
            "audience": state.audience,
            "goal": state.goal,
            "length_constraints": state.length_constraints,
            "sections_count": len(state.outline.get("sections", [])),
            "knowledge_chunks": len(knowledge_chunks_metadata),
        }

        context_summary_text = state.context_summary
        if knowledge_context:
            context_summary_text = f"{state.context_summary}\n\nKnowledge references:\n{knowledge_context}".strip()

        # Start activity tracking
        if self.activity_tracker:
            self.activity_tracker.start_agent(
                "Content Writer",
                stage.value,
                input_summary=input_context
            )
            self.activity_tracker.log_decision(f"Writing {state.content_type} with {len(state.outline.get('sections', []))} sections")

            # Log RAG usage for knowledge documents
            if knowledge_chunks_metadata:
                for chunk in knowledge_chunks_metadata[:15]:  # Log top 15 chunks
                    self.activity_tracker.log_rag_usage(
                        doc_id=chunk.get("document_id", 0),
                        doc_name=chunk.get("document_name", "Knowledge Document"),
                        chunks_used=1,
                        influence_score=chunk.get("similarity", 0.0),
                        purpose="Content writing support"
                    )

        try:
            result = await self.writer_agent.run(
                topic=state.topic,
                content_type=state.content_type,
                audience=state.audience,
                goal=state.goal,
                brand_voice=state.brand_voice,
                language=state.language,
                length_constraints=state.length_constraints,
                context_summary=context_summary_text,
                trends_keywords=state.trends_and_keywords,
                outline=state.outline,
                style_profile=style_profile,
            )

            # Log the agent call
            await self._log_agent_call(stage, self.writer_agent, result, start_time, input_context)

            # Validate output
            validate_agent_output("Writer Agent", result, ["full_text"])

            # Validate content length
            validate_content_length("Writer Agent", result.get("full_text", ""), min_words=100)

            state.draft = result
            state.completed_stages.append(stage.value)

            # Calculate word count
            full_text = result.get("full_text", "")
            word_count = len(full_text.split())

            # Complete activity tracking
            if self.activity_tracker:
                self.activity_tracker.log_decision(f"Generated {word_count} words of content")
                self.activity_tracker.complete_agent(
                    output_summary={
                        "word_count": word_count,
                        "sections_written": len(result.get("sections", [])),
                        "knowledge_refs_used": len(knowledge_chunks_metadata)
                    }
                )

            if self.on_stage_complete:
                await self._notify_stage_complete(stage, result)

            logger.info(f"Completed {stage.value}: {word_count} words written")

        except Exception as e:
            if self.activity_tracker:
                self.activity_tracker.fail_agent(str(e))
            await self._log_stage_failure(
                stage,
                str(e),
                start_time,
                agent=self.writer_agent,
                input_context=input_context
            )
            raise

        return state

    async def _run_seo_optimizer(self, state: PipelineState) -> PipelineState:
        """Run the SEO Optimizer agent."""
        stage = PipelineStage.SEO_OPTIMIZER
        state.current_stage = stage.value
        start_time = time.time()

        if self.on_stage_start:
            await self._notify_stage_start(stage, "Optimizing for SEO...")

        logger.info(f"Running {stage.value} agent")

        # Safely convert state fields to dicts
        tone_of_voice = safe_dict(state.tone_of_voice)
        trends_and_keywords = safe_dict(state.trends_and_keywords)
        draft = safe_dict(state.draft)

        style_profile = tone_of_voice.get("style_profile", {})

        # Input context for logging
        input_context = {
            "topic": state.topic,
            "content_type": state.content_type,
            "primary_keywords": trends_and_keywords.get("primary_keywords", []),
            "draft_word_count": len(draft.get("full_text", "").split()),
        }

        # Start activity tracking
        draft_text = draft.get("full_text", "")
        if self.activity_tracker:
            self.activity_tracker.start_agent(
                "SEO Optimizer",
                stage.value,
                input_summary=input_context
            )
            self.activity_tracker.log_decision(f"Optimizing content for {len(trends_and_keywords.get('primary_keywords', []))} keywords")
            # Store content before optimization
            self.activity_tracker.set_content_before_after(draft_text, "")  # Will update after

        # Check circuit breaker
        agent_name = "SEO Optimizer Agent"
        if self._check_circuit_breaker(agent_name):
            logger.warning(f"⚡ Circuit breaker OPEN - skipping {agent_name}")
            # For SEO agent, use draft as fallback
            result = {
                "optimized_text": draft.get("full_text", ""),
                "on_page_seo": {
                    "focus_keyword": trends_and_keywords.get("primary_keywords", [""])[0] if trends_and_keywords.get("primary_keywords") else "",
                    "title_tag": "Content Title",
                    "meta_description": "Content description",
                    "h1": state.topic,
                    "slug": state.topic.lower().replace(" ", "-")[:50],
                    "suggested_internal_links": [],
                    "suggested_external_links": [],
                    "seo_score": 0
                },
                "_skipped": True,
                "_skip_reason": "circuit breaker open"
            }

            if self.activity_tracker:
                self.activity_tracker.add_warning(f"Agent skipped due to circuit breaker")
                self.activity_tracker.complete_agent(
                    output_summary={"skipped": True, "reason": "circuit breaker"},
                    quality_metrics={}
                )

            state.seo_version = result
            state.completed_stages.append(stage.value)

            if self.on_stage_complete:
                await self._notify_stage_complete(stage, result)

            logger.warning(f"Skipped {stage.value} (circuit breaker) - using draft as-is")
            return state

        try:
            # Use retry logic with circuit breaker
            result = await self._retry_agent_with_fallback(
                agent_callable=self.seo_agent.run,
                agent_name=agent_name,
                max_retries=2,
                topic=state.topic,
                content_type=state.content_type,
                audience=state.audience,
                goal=state.goal,
                brand_voice=state.brand_voice,
                language=state.language,
                length_constraints=state.length_constraints,
                context_summary=state.context_summary,
                trends_keywords=state.trends_and_keywords,
                outline=state.outline,
                draft=state.draft,
                style_profile=style_profile,
            )

            # Log the agent call
            await self._log_agent_call(stage, self.seo_agent, result, start_time, input_context)

            # Validate output
            validate_agent_output("SEO Optimizer Agent", result, ["optimized_text", "on_page_seo"])

            # Validate on-page SEO structure
            on_page_seo = result.get("on_page_seo", {})
            required_seo_fields = ["focus_keyword", "title_tag", "meta_description", "h1", "slug"]
            missing_seo_fields = [field for field in required_seo_fields if not on_page_seo.get(field)]
            if missing_seo_fields:
                raise SEOValidationError(missing_seo_fields)

            # Validate content length
            validate_content_length("SEO Optimizer Agent", result.get("optimized_text", ""), min_words=100)

            state.seo_version = result
            state.completed_stages.append(stage.value)

            focus_keyword = on_page_seo.get("focus_keyword", "N/A")
            seo_score = on_page_seo.get("seo_score", 0)

            optimized_text = result.get("optimized_text", "") or result.get("full_text", "")

            # Complete activity tracking
            if self.activity_tracker:
                self.activity_tracker.set_content_before_after(draft_text, optimized_text)
                self.activity_tracker.log_decision(f"SEO score achieved: {seo_score}")
                self.activity_tracker.log_content_change(
                    change_type="seo_optimization",
                    reason=f"Optimized for focus keyword: {focus_keyword}"
                )
                self.activity_tracker.add_badge("SEO_OPTIMIZED", {"score": seo_score, "keyword": focus_keyword})
                self.activity_tracker.complete_agent(
                    output_summary={
                        "seo_score": seo_score,
                        "focus_keyword": focus_keyword,
                        "word_count": len(optimized_text.split())
                    },
                    quality_metrics={"seo_score": seo_score}
                )

            if self.on_stage_complete:
                await self._notify_stage_complete(stage, result)

            logger.info(f"Completed {stage.value}: optimized for '{focus_keyword}'")

        except Exception as e:
            logger.error(f"💥 {stage.value} failed after all retries: {str(e)[:200]}")

            if self.activity_tracker:
                self.activity_tracker.fail_agent(str(e))

            await self._log_stage_failure(
                stage,
                str(e),
                start_time,
                agent=self.seo_agent,
                input_context=input_context
            )

            # Use fallback instead of crashing - pass through draft
            logger.warning(f"⚠️ Using draft as fallback for SEO optimization")
            result = {
                "optimized_text": draft.get("full_text", ""),
                "on_page_seo": {
                    "focus_keyword": trends_and_keywords.get("primary_keywords", [""])[0] if trends_and_keywords.get("primary_keywords") else "",
                    "title_tag": "Content Title",
                    "meta_description": "Content description",
                    "h1": state.topic,
                    "slug": state.topic.lower().replace(" ", "-")[:50],
                    "suggested_internal_links": [],
                    "suggested_external_links": [],
                    "seo_score": 0
                },
                "_fallback_used": True,
                "_fallback_reason": f"agent failed: {str(e)[:100]}"
            }

            state.seo_version = result
            state.errors.append({
                "stage": stage.value,
                "error": str(e),
                "error_type": "AgentFailure",
                "fallback_used": True
            })

            if self.on_stage_complete:
                await self._notify_stage_complete(stage, result)

            logger.info(f"⚠️ {stage.value} completed with fallback - pipeline continuing")

        return state

    async def _run_originality_check(self, state: PipelineState) -> PipelineState:
        """Run the Originality & Plagiarism agent."""
        stage = PipelineStage.ORIGINALITY_CHECK
        state.current_stage = stage.value
        start_time = time.time()

        if self.on_stage_start:
            await self._notify_stage_start(stage, "Checking originality...")

        logger.info(f"Running {stage.value} agent")

        # Safely convert state fields to dicts
        tone_of_voice = safe_dict(state.tone_of_voice)
        seo_version = safe_dict(state.seo_version)

        style_profile = tone_of_voice.get("style_profile", {})

        # Input context for logging
        input_context = {
            "topic": state.topic,
            "audience": state.audience,
            "goal": state.goal,
            "seo_word_count": len(seo_version.get("optimized_text", "").split()),
        }

        # Start activity tracking
        if self.activity_tracker:
            self.activity_tracker.start_agent(
                "Originality Checker",
                stage.value,
                input_summary=input_context
            )
            self.activity_tracker.log_decision("Analyzing content for originality and plagiarism")

        # Check circuit breaker
        agent_name = "Originality & Plagiarism Agent"
        if self._check_circuit_breaker(agent_name):
            logger.warning(f"⚡ Circuit breaker OPEN - skipping {agent_name}")
            result = self._create_fallback_result(agent_name, seo_version, "circuit breaker open")

            if self.activity_tracker:
                self.activity_tracker.add_warning(f"Agent skipped due to circuit breaker")
                self.activity_tracker.complete_agent(
                    output_summary={"skipped": True, "reason": "circuit breaker"},
                    quality_metrics={}
                )

            state.originality_check = result
            state.completed_stages.append(stage.value)

            if self.on_stage_complete:
                await self._notify_stage_complete(stage, result)

            logger.warning(f"Skipped {stage.value} (circuit breaker) - using SEO output as-is")
            return state

        try:
            # Use retry logic with circuit breaker
            result = await self._retry_agent_with_fallback(
                agent_callable=self.originality_agent.run,
                agent_name=agent_name,
                max_retries=2,
                topic=state.topic,
                audience=state.audience,
                goal=state.goal,
                brand_voice=state.brand_voice,
                language=state.language,
                context_summary=state.context_summary,
                seo_version=state.seo_version,
                style_profile=style_profile,
                brave_search_api_key=state.brave_search_api_key,
            )

            # If parsing failed upstream, record the issue and continue with the fallback payload
            parse_error = result.get("parse_error") if isinstance(result, dict) else None
            if parse_error:
                logger.error(f"{stage.value} returned unparseable JSON: {parse_error}")
                state.errors.append(
                    {
                        "stage": stage.value,
                        "error": parse_error,
                        "error_type": "JSONDecodeError",
                    }
                )

                if self.activity_tracker:
                    self.activity_tracker.fail_agent(parse_error)

                await self._log_stage_failure(
                    stage,
                    parse_error,
                    start_time,
                    agent=self.originality_agent,
                    input_context=input_context,
                )

                state.originality_check = result

                if self.on_stage_complete:
                    await self._notify_stage_complete(stage, result)

                return state

            # Log the agent call
            await self._log_agent_call(stage, self.originality_agent, result, start_time, input_context)

            # Track Brave metrics if present
            if '_brave_metrics' in result:
                brave_metrics = result.pop('_brave_metrics')  # Remove from result to not pollute state
                state.brave_requests_made += brave_metrics.get('requests_made', 0)
                state.brave_results_received += brave_metrics.get('results_received', 0)
                logger.info(f"📊 Brave Search: {brave_metrics.get('requests_made', 0)} requests, {brave_metrics.get('results_received', 0)} results")

            state.originality_check = result
            state.completed_stages.append(stage.value)

            score = result.get("originality_score", "unknown")
            flagged_passages = result.get("flagged_passages", [])
            flagged = len(flagged_passages)

            # CRITICAL: Validate that rewritten_text was returned
            # If not, apply rewrites programmatically from flagged_passages
            if "rewritten_text" not in result or not result.get("rewritten_text"):
                logger.warning("⚠️ Originality agent did not return 'rewritten_text' - applying rewrites programmatically")
                original_text = seo_version.get("optimized_text", "")
                if flagged_passages:
                    rewritten_text = apply_originality_rewrites(original_text, flagged_passages)
                    state.originality_check["rewritten_text"] = rewritten_text
                    logger.info(f"✅ Successfully built rewritten_text programmatically ({len(rewritten_text)} chars)")
                else:
                    # No flagged passages means content is original - use SEO version as-is
                    state.originality_check["rewritten_text"] = original_text
                    logger.info("✅ No originality issues - using SEO optimized text as rewritten_text")
            else:
                logger.info(f"✅ Originality agent returned complete rewritten_text ({len(result.get('rewritten_text', ''))} chars)")

            # Track content diff
            original_seo_text = seo_version.get("optimized_text", "")
            final_rewritten_text = state.originality_check.get("rewritten_text", "")
            diff_metrics = calculate_content_diff(original_seo_text, final_rewritten_text, "Originality Agent")

            # Validate content length
            validate_content_length("Originality Agent", final_rewritten_text, min_words=100)

            # Complete activity tracking
            if self.activity_tracker:
                self.activity_tracker.log_decision(f"Originality score: {score}")
                if flagged > 0:
                    self.activity_tracker.add_warning(f"{flagged} passages flagged for review")
                else:
                    self.activity_tracker.add_badge("HIGH_ORIGINALITY", {"score": score})
                self.activity_tracker.complete_agent(
                    output_summary={
                        "originality_score": score,
                        "flagged_passages": flagged
                    },
                    quality_metrics={"originality_score": score}
                )

            if self.on_stage_complete:
                await self._notify_stage_complete(stage, result)

            logger.info(f"Completed {stage.value}: score={score}, {flagged} passages flagged")

        except Exception as e:
            logger.error(f"💥 {stage.value} failed after all retries: {str(e)[:200]}")

            if self.activity_tracker:
                self.activity_tracker.fail_agent(str(e))

            await self._log_stage_failure(
                stage,
                str(e),
                start_time,
                agent=self.originality_agent,
                input_context=input_context
            )

            # Use circuit breaker fallback instead of crashing the pipeline
            logger.warning(f"⚠️ Using fallback result to continue pipeline")
            result = self._create_fallback_result(agent_name, seo_version, f"all retries failed: {str(e)[:100]}")

            state.originality_check = result
            state.errors.append({
                "stage": stage.value,
                "error": str(e),
                "error_type": "AgentFailure",
                "fallback_used": True
            })

            if self.on_stage_complete:
                await self._notify_stage_complete(stage, result)

            logger.info(f"⚠️ {stage.value} completed with fallback - pipeline continuing")

        return state

    async def _run_final_review(self, state: PipelineState) -> PipelineState:
        """Run the Final Reviewer agent."""
        stage = PipelineStage.FINAL_REVIEW
        state.current_stage = stage.value
        start_time = time.time()

        if self.on_stage_start:
            await self._notify_stage_start(stage, "Final review and polish...")

        logger.info(f"Running {stage.value} agent")

        # Safely convert state fields to dicts
        tone_of_voice = safe_dict(state.tone_of_voice)
        originality_check = safe_dict(state.originality_check)
        seo_version = safe_dict(state.seo_version)

        style_profile = tone_of_voice.get("style_profile", {})

        # Get rewritten text from originality check (guaranteed to exist from previous stage)
        rewritten_text = originality_check.get("rewritten_text", "")

        # Create modified seo_version with rewritten text for final review
        seo_version_with_rewrites = seo_version.copy()
        seo_version_with_rewrites["optimized_text"] = rewritten_text

        # Input context for logging
        input_context = {
            "topic": state.topic,
            "audience": state.audience,
            "goal": state.goal,
            "originality_score": originality_check.get("originality_score", "unknown"),
            "flagged_passages_count": len(originality_check.get("flagged_passages", [])),
            "has_rewritten_text": bool(originality_check.get("rewritten_text")),
        }

        # Start activity tracking
        if self.activity_tracker:
            self.activity_tracker.start_agent(
                "Final Reviewer",
                stage.value,
                input_summary=input_context
            )
            self.activity_tracker.log_decision("Performing final review and polish")
            # Store content before final review
            self.activity_tracker.set_content_before_after(rewritten_text, "")  # Will update after

        try:
            result = await self.reviewer_agent.run(
                topic=state.topic,
                audience=state.audience,
                goal=state.goal,
                brand_voice=state.brand_voice,
                language=state.language,
                context_summary=state.context_summary,
                seo_version=seo_version_with_rewrites,
                originality_check=originality_check,
                style_profile=style_profile,
            )

            # Log the agent call
            await self._log_agent_call(stage, self.reviewer_agent, result, start_time, input_context)

            # Validate output
            validate_agent_output("Final Reviewer Agent", result, ["final_text"])

            # Validate content length
            validate_content_length("Final Reviewer Agent", result.get("final_text", ""), min_words=100)

            state.final_review = result
            state.completed_stages.append(stage.value)

            # Safely access result fields
            result_dict = safe_dict(result)
            changes = len(result_dict.get("change_log", []))
            variants = len(result_dict.get("suggested_variants", []))
            final_text = result_dict.get("final_text", "") or result_dict.get("polished_text", "")

            # Complete activity tracking
            if self.activity_tracker:
                self.activity_tracker.set_content_before_after(rewritten_text, final_text)
                self.activity_tracker.log_decision(f"Made {changes} refinements")

                # Log each change as a content change
                for change in result_dict.get("change_log", [])[:10]:  # Log top 10 changes
                    change_dict = safe_dict(change) if isinstance(change, (str, dict)) else {}
                    self.activity_tracker.log_content_change(
                        change_type="final_polish",
                        reason=change_dict.get("reason", "Quality improvement") if isinstance(change_dict, dict) else "Quality improvement"
                    )

                self.activity_tracker.add_badge("FINAL_REVIEW_COMPLETE", {"changes": changes, "variants": variants})
                self.activity_tracker.complete_agent(
                    output_summary={
                        "changes_made": changes,
                        "variants_suggested": variants,
                        "final_word_count": len(final_text.split())
                    }
                )

            if self.on_stage_complete:
                await self._notify_stage_complete(stage, result)

            logger.info(f"Completed {stage.value}: {changes} changes, {variants} variants")

        except Exception as e:
            if self.activity_tracker:
                self.activity_tracker.fail_agent(str(e))
            await self._log_stage_failure(
                stage,
                str(e),
                start_time,
                agent=self.reviewer_agent,
                input_context=input_context
            )
            raise

        return state

    async def _notify_stage_start(self, stage: PipelineStage, message: str) -> None:
        """Notify callback of stage start."""
        if self.on_stage_start:
            try:
                if callable(self.on_stage_start):
                    result = self.on_stage_start(stage.value, message)
                    if hasattr(result, '__await__'):
                        await result
            except Exception as e:
                logger.error(f"Stage start callback error: {e}")

    async def _notify_stage_complete(self, stage: PipelineStage, result: Dict[str, Any]) -> None:
        """Notify callback of stage completion."""
        if self.on_stage_complete:
            try:
                if callable(self.on_stage_complete):
                    callback_result = self.on_stage_complete(stage.value, result)
                    if hasattr(callback_result, '__await__'):
                        await callback_result
            except Exception as e:
                logger.error(f"Stage complete callback error: {e}")

    async def _notify_checkpoint_reached(
        self,
        stage: PipelineStage,
        result: Dict[str, Any],
        state: PipelineState,
        checkpoint_session_id: str
    ) -> Dict[str, str]:
        """
        Notify that a checkpoint has been reached and wait for user action.

        Returns:
            Dict with action ("approve", "edit", "restart", "skip", "cancel") and any edited output
        """
        if self.on_checkpoint_reached:
            try:
                if callable(self.on_checkpoint_reached):
                    # Call checkpoint callback with stage info
                    callback_result = self.on_checkpoint_reached(
                        stage.value,
                        result,
                        state,
                        checkpoint_session_id
                    )
                    if hasattr(callback_result, '__await__'):
                        return await callback_result
                    return callback_result
            except Exception as e:
                logger.error(f"Checkpoint callback error: {e}")
                # Default to approve on error
                return {"action": "approve"}

        # If no checkpoint callback, default to approve (automatic mode)
        return {"action": "approve"}

    def get_pipeline_stages(self) -> list:
        """Get the list of pipeline stages in order."""
        return [stage.value for stage in PipelineStage]

    def get_agent_for_stage(self, stage: str):
        """Get the agent instance for a specific stage."""
        agents = {
            PipelineStage.TRENDS_KEYWORDS.value: self.trends_agent,
            PipelineStage.TONE_OF_VOICE.value: self.tone_agent,
            PipelineStage.STRUCTURE_OUTLINE.value: self.structure_agent,
            PipelineStage.WRITER.value: self.writer_agent,
            PipelineStage.SEO_OPTIMIZER.value: self.seo_agent,
            PipelineStage.ORIGINALITY_CHECK.value: self.originality_agent,
            PipelineStage.FINAL_REVIEW.value: self.reviewer_agent,
        }
        return agents.get(stage)

    async def _log_agent_call(self, stage: PipelineStage, agent, result: Dict[str, Any],
                              start_time: float, input_context: Dict[str, Any]) -> None:
        """Log agent call details if logger is available."""
        if not self.agent_logger:
            return

        try:
            # Get the call details from the agent
            call_details = agent.get_last_call_details()

            # Calculate duration
            duration = time.time() - start_time

            # Start the stage in the logger
            self.agent_logger.start_stage(
                stage=stage.value,
                stage_order=list(PipelineStage).index(stage) + 1
            )

            # Log prompts
            self.agent_logger.log_prompt(
                system_prompt=call_details.get("system_prompt", ""),
                user_prompt=call_details.get("user_prompt", ""),
                input_context=input_context
            )

            # Log response
            self.agent_logger.log_response(
                raw_response=call_details.get("raw_response", ""),
                parsed_result=result,
                model=getattr(self.llm_client, 'model_name', 'unknown') if self.llm_client else 'unknown',
                temperature=call_details.get("temperature", 0.5)
            )

            # Complete the stage
            self.agent_logger.complete_stage(duration_seconds=duration)

        except Exception as e:
            logger.error(f"Failed to log agent call for {stage.value}: {e}")

    async def _log_stage_failure(
        self,
        stage: PipelineStage,
        error: str,
        start_time: float,
        agent: Any = None,
        input_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a stage failure if logger is available."""
        if not self.agent_logger:
            return

        try:
            duration = time.time() - start_time

            # If stage wasn't started yet, start it now
            self.agent_logger.start_stage(
                stage=stage.value,
                stage_order=list(PipelineStage).index(stage) + 1
            )

            # Attempt to capture prompts/responses for debugging
            call_details = agent.get_last_call_details() if agent else {}
            system_prompt = call_details.get("system_prompt", "")
            user_prompt = call_details.get("user_prompt", "")
            raw_response = call_details.get("raw_response", "")
            temperature = call_details.get("temperature", 0.5)

            # Only log prompt/response if we have something meaningful
            if system_prompt or user_prompt or raw_response:
                self.agent_logger.log_prompt(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    input_context=input_context,
                )
                self.agent_logger.log_response(
                    raw_response=raw_response,
                    parsed_result={"error": error},
                    model=getattr(self.llm_client, 'model_name', 'unknown') if self.llm_client else 'unknown',
                    temperature=temperature,
                )

            # Mark as failed
            self.agent_logger.fail_stage(error_message=error, duration_seconds=duration)

        except Exception as e:
            logger.error(f"Failed to log stage failure for {stage.value}: {e}")

    def _safe_activity_tracker_call(self, operation_name: str, operation_callable, *args, **kwargs):
        """
        Safely call an activity_tracker operation with defensive error handling.
        If activity tracking fails, log the error but don't break the pipeline.
        """
        if not self.activity_tracker:
            return None

        try:
            return operation_callable(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Activity tracker operation '{operation_name}' failed: {e}")
            return None

    async def _track_rag_documents(self, state: PipelineState, document_ids: List[int]) -> None:
        """Track which RAG documents are being used."""
        try:
            from ..database import SessionLocal
            from ..models import RagDocument

            db = SessionLocal()
            try:
                docs = db.query(RagDocument).filter(RagDocument.id.in_(document_ids)).all()

                # Validate that all requested document IDs were found
                found_ids = {doc.id for doc in docs}
                requested_ids = set(document_ids)
                missing_ids = requested_ids - found_ids

                if missing_ids:
                    warning_msg = f"⚠️ RAG document validation: {len(missing_ids)} document IDs not found in database: {sorted(missing_ids)}"
                    logger.warning(warning_msg)
                    if self.activity_tracker:
                        self.activity_tracker.add_warning(warning_msg)
                else:
                    logger.info(f"✅ All {len(document_ids)} RAG document IDs validated successfully")

                for doc in docs:
                    doc_info = {
                        "id": doc.id,
                        "name": doc.original_filename or doc.filename,
                        "filename": doc.filename,
                        "file_type": doc.file_type,
                        "project": doc.project_name,
                    }
                    # Add only if not already tracked
                    if not any(d.get("id") == doc.id for d in state.rag_documents_used):
                        state.rag_documents_used.append(doc_info)
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Failed to track RAG documents: {e}")

    async def _track_rag_chunks(self, state: PipelineState, chunks_metadata: List[Dict], stage_name: str) -> None:
        """Track retrieved RAG chunks with their metadata."""
        if not chunks_metadata:
            return

        for chunk_meta in chunks_metadata:
            chunk_info = {
                "text": chunk_meta.get("text", "")[:500],  # Truncate for response size
                "full_text": chunk_meta.get("text", ""),
                "document_id": chunk_meta.get("document_id") or chunk_meta.get("doc_id"),
                "document_name": chunk_meta.get("document_name", "Unknown"),
                "score": round(chunk_meta.get("score", 0.0), 3),
                "chunk_id": chunk_meta.get("chunk_id", str(len(state.rag_chunks_used))),
                "chunk_position": chunk_meta.get("position", 0),
                "used_in_stage": stage_name,
                "timestamp": time.time(),
            }
            state.rag_chunks_used.append(chunk_info)
