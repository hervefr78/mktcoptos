"""
Content Pipeline API Routes
============================

FastAPI routes for the multi-agent content creation pipeline.
"""

import json
import logging
import hashlib
import importlib.util
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.orm import Session

from .llm_service import LLMService
from .rag.vector_store import VectorStore
from .rag.storage import RAGStorage
from .database import get_db, SessionLocal
from .models import PipelineExecution, PipelineStepResult, CheckpointSession, Project, Campaign, User, OrganizationMember, OrganizationSettings
from utils.cache import get_cached_response, set_cached_response
from .rag.enhanced_rag import (
    EnhancedVectorStore,
    ChunkEnrichmentService,
    QueryExpansionService,
    context_aware_chunk,
    EnrichedChunk
)
from .agents.content_pipeline import ContentPipelineOrchestrator
from .agent_logger import AgentLogger
from .report_generator import ReportGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/content-pipeline", tags=["content-pipeline"])

# Initialize vector stores
vector_store = VectorStore()  # Legacy store
enhanced_vector_store = EnhancedVectorStore()  # New enhanced store
rag_storage = RAGStorage()  # New RAG storage for knowledge base

# Initialize services (LLM will be set per-request)
chunk_enrichment_service = ChunkEnrichmentService()
query_expansion_service = QueryExpansionService()


def _extract_document_text(path: Path, file_type: Optional[str]) -> str:
    """Extract text content from a stored RAG document."""
    resolved_type = (file_type or "").lower()

    if resolved_type in {"txt", "md"}:
        return path.read_text(encoding="utf-8", errors="ignore")

    if resolved_type == "pdf" and importlib.util.find_spec("PyPDF2"):
        from PyPDF2 import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if resolved_type == "docx" and importlib.util.find_spec("docx"):
        from docx import Document

        document = Document(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    # Fallback: best-effort read as text
    return path.read_text(encoding="utf-8", errors="ignore")


def _get_brave_api_key(db: Session, user_id: int) -> Optional[str]:
    """
    Get Brave Search API key for a user from their organization settings.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Brave API key or None if not configured
    """
    try:
        # Get user's organization through organization membership
        member = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == user_id
        ).first()

        if not member:
            logger.warning(f"No organization found for user {user_id}")
            return None

        # Get organization settings
        org_settings = db.query(OrganizationSettings).filter(
            OrganizationSettings.organization_id == member.organization_id
        ).first()

        if org_settings and org_settings.brave_search_api_key:
            logger.info(f"✅ Brave Search API key found for organization {member.organization_id}")
            return org_settings.brave_search_api_key

        logger.info(f"ℹ️ No Brave Search API key configured for organization {member.organization_id}")
        return None

    except Exception as e:
        logger.error(f"Error fetching Brave API key: {e}")
        return None


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ContentPipelineRequest(BaseModel):
    """Request model for content pipeline."""
    topic: str = Field(..., description="The subject/topic for content creation")
    content_type: str = Field(default="blog post", description="Type of content")
    audience: str = Field(default="general", description="Target audience")
    goal: str = Field(default="awareness", description="Content goal")
    brand_voice: str = Field(default="professional", description="Brand voice guidelines")
    language: str = Field(default="English", description="Output language")
    length_constraints: str = Field(default="1000-1500 words", description="Length requirements")
    context_summary: str = Field(default="", description="Additional context")
    user_id: int = Field(default=1, description="User ID for settings")
    project_id: Optional[int] = Field(default=None, description="Project ID for content organization")
    campaign_id: Optional[int] = Field(default=None, description="Campaign ID for RAG filtering (sub-projects)")
    parent_content: Optional[str] = Field(default=None, description="Parent project content for adaptation (sub-projects)")
    style_document_ids: List[int] = Field(default=[], description="RAG document IDs for tone/voice/style analysis")
    knowledge_document_ids: List[int] = Field(default=[], description="RAG document IDs for content/knowledge retrieval")
    checkpoint_mode: str = Field(default="automatic", description="Pipeline mode: 'automatic' or 'checkpoint'")


class PipelineStageUpdate(BaseModel):
    """Model for pipeline stage updates."""
    stage: str
    status: str
    message: str
    timestamp: str
    data: Optional[Dict[str, Any]] = None


class ContentPipelineResponse(BaseModel):
    """Response model for content pipeline."""
    success: bool
    pipeline_id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CheckpointActionRequest(BaseModel):
    """Request model for checkpoint actions."""
    session_id: str = Field(..., description="Checkpoint session ID")
    action: str = Field(..., description="Action: approve, edit, restart, skip, approve_all, cancel")
    edited_output: Optional[Dict[str, Any]] = Field(default=None, description="Edited stage output (for action=edit)")
    next_agent_instructions: Optional[str] = Field(default=None, description="Instructions for next stage")
    restart_instructions: Optional[str] = Field(default=None, description="Instructions for restarting current stage")


class CheckpointSaveRequest(BaseModel):
    """Request model for saving checkpoint state."""
    session_id: str = Field(..., description="Checkpoint session ID")


class CheckpointStatusResponse(BaseModel):
    """Response model for checkpoint status."""
    session_id: str
    status: str
    current_stage: Optional[str]
    stages_completed: List[str]
    stage_results: Dict[str, Any]
    checkpoint_history: List[Dict[str, Any]]
    waiting_for_approval: bool


# =============================================================================
# LLM CLIENT WRAPPER
# =============================================================================

class LLMClientWrapper:
    """
    Wrapper around LLMService to provide the interface expected by agents.
    """

    def __init__(self, user_id: int = 1):
        self.user_id = user_id
        # Get model name from settings
        db = SessionLocal()
        try:
            from .settings_service import SettingsService
            settings = SettingsService.get_combined_settings(user_id, db)
            self.model_name = settings.llmModel or "gpt-4o-mini"
        finally:
            db.close()

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> str:
        """Generate text using LLMService."""
        return await LLMService.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            user_id=self.user_id
        )


# =============================================================================
# RAG RETRIEVER (Enhanced with Query Expansion)
# =============================================================================

async def retrieve_brand_voice_examples(
    query: str,
    collection: str = "brand_voice",
    k: int = 10,
    topic: str = "",
    content_type: str = "blog post",
    audience: str = "general",
    brand_voice: str = "professional",
    goal: str = "awareness",
    user_id: int = 1,
    document_ids: List[int] = None,
    project_name: str = None,
    campaign_id: int = None,
    return_metadata: bool = False
):
    """
    Retrieve brand voice examples using enhanced RAG with query expansion.

    Args:
        query: Base search query
        collection: Collection name
        k: Number of results to return
        topic: Content topic for query expansion
        content_type: Type of content for filtering
        audience: Target audience for filtering
        brand_voice: Brand voice description
        goal: Content goal
        user_id: User ID for LLM service
        document_ids: Specific RAG document IDs to retrieve content from
        project_name: Project name to filter chunks by (optional)
        return_metadata: If True, return dict with chunks and metadata

    Returns:
        str: JSON string of enriched chunks (if return_metadata=False)
        dict: {"chunks": str, "metadata": list} (if return_metadata=True)
    """
    try:
        # If specific document IDs are provided, retrieve content from those documents
        # Use RAG storage for both knowledge_base and brand_voice collections
        if document_ids:
            logger.info(f"🔍 RAG RETRIEVAL: Retrieving chunks from {collection} for documents: {document_ids}")
            logger.info(f"🔍 RAG RETRIEVAL: Query: '{query[:100]}...'")

            # Use RAG storage to get semantically relevant chunks
            chunks = rag_storage.retrieve_chunks(
                query=query,
                collection=collection,  # Use the specified collection
                k=k,
                document_ids=document_ids,
                project_name=project_name,  # Filter by project if provided
                campaign_id=campaign_id  # Filter by campaign for sub-projects
            )

            if chunks:
                logger.info(f"✅ RAG RETRIEVAL: Found {len(chunks)} chunks from vector store")
                chunks_str = json.dumps(chunks, indent=2)
                if return_metadata:
                    return {
                        "chunks": chunks_str,
                        "metadata": chunks
                    }
                return chunks_str

            # Fallback to direct document reading if no chunks found
            logger.warning(f"⚠️  RAG RETRIEVAL: No chunks found in storage for documents {document_ids}, attempting direct read")
            from .models import RagDocument
            from .database import SessionLocal

            db = SessionLocal()
            try:
                # Get the documents
                docs = db.query(RagDocument).filter(RagDocument.id.in_(document_ids)).all()

                if docs:
                    chunks_data = []
                    for doc in docs:
                        try:
                            content = _extract_document_text(Path(doc.file_path), doc.file_type)
                            if not content:
                                logger.warning(
                                    "No readable content extracted from document %s", doc.id
                                )
                                continue

                            # Create a chunk for this document
                            chunk_dict = {
                                "chunk_id": f"doc_{doc.id}",
                                "doc_id": str(doc.id),
                                "document_id": doc.id,  # Add numeric ID for tracking
                                "document_name": doc.original_filename or doc.filename,
                                "text": content[:5000],  # Limit content length
                                "full_text": content[:5000],
                                "context_summary": f"Reference from {doc.original_filename}",
                                "source_type": doc.file_type or "other",
                                "style_tags": [],
                                "content_tags": [],
                                "audience_tags": [],
                                "created_at": doc.created_at.isoformat() if doc.created_at else "",
                                "score": 0.7,
                            }
                            chunks_data.append(chunk_dict)
                            logger.info(
                                "Retrieved content from document: %s", doc.original_filename
                            )
                        except Exception as e:
                            logger.warning(f"Failed to read document {doc.id}: {e}")

                    if chunks_data:
                        logger.info(f"✅ RAG RETRIEVAL: Fallback succeeded - extracted content from {len(chunks_data)} documents")
                        chunks_str = json.dumps(chunks_data, indent=2)
                        if return_metadata:
                            # Return both chunks and metadata for tracking
                            return {
                                "chunks": chunks_str,
                                "metadata": chunks_data  # Full metadata for tracking
                            }
                        return chunks_str
                    else:
                        logger.error(f"❌ RAG RETRIEVAL: Fallback failed - no content extracted from documents")
            finally:
                db.close()

            logger.error(f"❌ RAG RETRIEVAL: No content found for document IDs: {document_ids}")
            return ""

        # Check if enhanced store has data
        enhanced_chunks = enhanced_vector_store.get_all_chunks()

        if enhanced_chunks:
            # Use enhanced retrieval with query expansion
            llm_client = LLMClientWrapper(user_id=user_id)
            query_expansion_service.llm_service = llm_client

            # Generate query variants
            queries = await query_expansion_service.expand_query(
                topic=topic or query,
                content_type=content_type,
                audience=audience,
                brand_voice=brand_voice,
                goal=goal
            )

            logger.info(f"Query expansion generated {len(queries)} variants")

            # Search with expanded queries and Phase 2 reranking
            results = enhanced_vector_store.search_with_expansion(
                queries=queries,
                k=k,
                use_reranking=True,  # Phase 2: Use cross-encoder reranking
                source_type_filter=None,  # Don't filter too strictly
            )

            if results:
                # Return as JSON array of enriched chunks
                chunks_data = [chunk.to_dict() for chunk in results]
                chunks_str = json.dumps(chunks_data, indent=2)
                if return_metadata:
                    return {
                        "chunks": chunks_str,
                        "metadata": chunks_data
                    }
                return chunks_str

        # Fallback to legacy vector store
        legacy_results = vector_store.similarity_search(query, k=k)
        if legacy_results:
            # Convert to enriched chunk format for compatibility
            chunks_data = [
                {
                    "chunk_id": f"legacy_{i}",
                    "doc_id": "legacy",
                    "document_id": None,
                    "document_name": "Legacy Store",
                    "text": text,
                    "context_summary": "",
                    "source_type": "other",
                    "style_tags": [],
                    "content_tags": [],
                    "audience_tags": [],
                    "created_at": datetime.utcnow().isoformat(),
                    "score": 0.7  # Default score
                }
                for i, text in enumerate(legacy_results)
            ]
            chunks_str = json.dumps(chunks_data, indent=2)
            if return_metadata:
                return {
                    "chunks": chunks_str,
                    "metadata": chunks_data
                }
            return chunks_str

        return ""

    except Exception as e:
        logger.error(f"RAG retrieval error: {e}")
        return ""


async def retrieve_brand_voice_for_pipeline(
    topic: str,
    content_type: str,
    audience: str,
    brand_voice: str,
    goal: str,
    user_id: int = 1,
    k: int = 10
) -> str:
    """
    Convenience function for pipeline RAG retrieval.
    """
    base_query = f"brand voice examples for {content_type} targeting {audience} with {brand_voice} tone"

    return await retrieve_brand_voice_examples(
        query=base_query,
        k=k,
        topic=topic,
        content_type=content_type,
        audience=audience,
        brand_voice=brand_voice,
        goal=goal,
        user_id=user_id
    )


# =============================================================================
# PIPELINE EXECUTION STATE
# =============================================================================

# In-memory store for pipeline execution state (use Redis in production)
pipeline_executions: Dict[str, Dict[str, Any]] = {}

# Stage order mapping
STAGE_ORDER = {
    "trends_keywords": 1,
    "tone_of_voice": 2,
    "structure_outline": 3,
    "writer": 4,
    "seo_optimizer": 5,
    "originality_check": 6,
    "final_review": 7,
}


def generate_pipeline_id() -> str:
    """Generate a unique pipeline execution ID."""
    import uuid
    return f"pipeline_{uuid.uuid4().hex[:12]}"


# =============================================================================
# PIPELINE PERSISTENCE SERVICE
# =============================================================================

def create_pipeline_execution(
    db: Session,
    pipeline_id: str,
    request: "ContentPipelineRequest"
) -> PipelineExecution:
    """Create a new pipeline execution record."""
    execution = PipelineExecution(
        pipeline_id=pipeline_id,
        user_id=request.user_id,
        project_id=request.project_id,
        topic=request.topic,
        content_type=request.content_type,
        audience=request.audience,
        goal=request.goal,
        brand_voice=request.brand_voice,
        language=request.language,
        length_constraints=request.length_constraints,
        context_summary=request.context_summary,
        status="running",
        started_at=datetime.utcnow()
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def save_step_result(
    db: Session,
    execution_id: int,
    stage: str,
    result: Dict[str, Any],
    duration_seconds: int = 0,
    tokens_used: int = 0,
    status: str = "completed",
    error_message: str = None,
    agent_metrics: Dict[str, Any] = None  # NEW: Save agent metrics for later review
) -> PipelineStepResult:
    """Save a pipeline step result with agent metrics."""
    # Enhance result with agent metrics if provided
    enhanced_result = result.copy() if result else {}
    if agent_metrics:
        enhanced_result["_agent_metrics"] = agent_metrics  # Store metrics in special key

    step = PipelineStepResult(
        execution_id=execution_id,
        stage=stage,
        stage_order=STAGE_ORDER.get(stage, 0),
        status=status,
        result=enhanced_result,  # Save enhanced result with metrics
        duration_seconds=duration_seconds,
        tokens_used=tokens_used,
        error_message=error_message,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow() if status == "completed" else None
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def complete_pipeline_execution(
    db: Session,
    execution_id: int,
    result: Dict[str, Any],
    status: str = "completed",
    error_message: str = None,
    error_stage: str = None
) -> PipelineExecution:
    """Complete a pipeline execution with final result."""
    print(f"\n{'='*80}\n🎯 COMPLETE_PIPELINE_EXECUTION CALLED: execution_id={execution_id}, status={status}\n{'='*80}\n", flush=True)
    logger.info(f"🎯 COMPLETE_PIPELINE_EXECUTION CALLED: execution_id={execution_id}, status={status}")

    execution = db.query(PipelineExecution).filter(
        PipelineExecution.id == execution_id
    ).first()

    if not execution:
        return None

    execution.status = status
    execution.completed_at = datetime.utcnow()
    execution.final_result = result

    # Calculate duration
    if execution.started_at:
        duration = (datetime.utcnow() - execution.started_at).total_seconds()
        execution.total_duration_seconds = int(duration)

    # Extract final content
    final_text = (
        result.get("final_review", {}).get("final_text") or
        result.get("seo_version", {}).get("optimized_text") or
        result.get("draft", {}).get("full_text") or
        ""
    )
    execution.final_content = final_text
    execution.word_count = len(final_text.split()) if final_text else 0

    # Extract scores
    execution.originality_score = result.get("originality_check", {}).get("originality_score")

    # Error tracking
    if error_message:
        execution.error_message = error_message
        execution.error_stage = error_stage

    db.commit()
    db.refresh(execution)

    # Auto-ingest completed content into RAG if this is a main project in integrated campaign
    logger.info(f"🔍 RAG AUTO-INGESTION CHECK: pipeline_id={execution_id}, status={status}, project_id={execution.project_id}, has_final_text={bool(final_text)}, final_text_length={len(final_text) if final_text else 0}")

    if status == "completed" and execution.project_id and final_text:
        try:
            from .rag.routes import ingest_main_project_content_sync

            logger.info(f"✅ Conditions met! Starting RAG auto-ingestion: project_id={execution.project_id}, pipeline_id={execution_id}")
            ingestion_result = ingest_main_project_content_sync(
                db=db,
                project_id=execution.project_id,
                pipeline_id=execution_id,
                content=final_text,
                topic=execution.topic or "Main Project Content"
            )

            if ingestion_result["status"] == "ingested":
                logger.info(f"✅ Successfully ingested main project content into RAG: {ingestion_result}")
            elif ingestion_result["status"] == "skipped":
                logger.info(f"⏭️  Skipped RAG ingestion: {ingestion_result.get('reason', 'unknown reason')}")
            else:
                logger.warning(f"⚠️  RAG ingestion failed: {ingestion_result}")
        except Exception as e:
            logger.error(f"❌ Error during RAG auto-ingestion: {e}", exc_info=True)
    else:
        logger.warning(f"❌ RAG auto-ingestion SKIPPED - Condition not met: status={status}, project_id={execution.project_id}, has_final_text={bool(final_text)}")

    return execution


# =============================================================================
# REDIS CACHING FOR TRENDS & KEYWORDS
# =============================================================================

def get_trends_cache_key(request: "ContentPipelineRequest") -> str:
    """Generate cache key for trends & keywords based on input parameters."""
    key_data = f"{request.topic}:{request.content_type}:{request.audience}:{request.goal}:{request.brand_voice}"
    return f"trends_keywords:{hashlib.md5(key_data.encode()).hexdigest()}"


def get_cached_trends(request: "ContentPipelineRequest") -> Optional[Dict[str, Any]]:
    """Get cached trends & keywords result."""
    cache_key = get_trends_cache_key(request)
    cached = get_cached_response("pipeline", cache_key)
    if cached:
        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            return None
    return None


def cache_trends_result(request: "ContentPipelineRequest", result: Dict[str, Any]) -> None:
    """Cache trends & keywords result."""
    cache_key = get_trends_cache_key(request)
    try:
        set_cached_response("pipeline", cache_key, json.dumps(result))
        logger.info(f"Cached trends result: {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to cache trends result: {e}")


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/run", response_model=ContentPipelineResponse)
async def run_content_pipeline(request: ContentPipelineRequest, db: Session = Depends(get_db)):
    """
    Run the complete content creation pipeline.

    This endpoint executes all 7 agents in sequence and returns the final result.
    """
    pipeline_id = generate_pipeline_id()

    try:
        # Look up project name if project_id is provided
        project_name = None
        if request.project_id:
            from .models import Project
            project = db.query(Project).filter(Project.id == request.project_id).first()
            if project:
                project_name = project.name
                logger.info(f"Pipeline running for project: {project_name} (ID: {request.project_id})")

        # Create database execution record
        execution = create_pipeline_execution(db, pipeline_id, request)
        execution_id = execution.id

        # Create LLM client wrapper
        llm_client = LLMClientWrapper(user_id=request.user_id)

        # Track stage timing for logging and database persistence
        stage_start_times: Dict[str, datetime] = {}

        # Callbacks to track progress even in non-streaming mode
        def on_stage_start(stage: str, message: str):
            stage_start_times[stage] = datetime.utcnow()

            # Persist current stage for error/debug visibility
            try:
                current_execution = db.query(PipelineExecution).filter(
                    PipelineExecution.id == execution_id
                ).first()
                if current_execution:
                    current_execution.current_stage = stage
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to record current stage '{stage}': {e}")

        def on_stage_complete(stage: str, result: Dict[str, Any]):
            duration_seconds = 0
            if stage in stage_start_times:
                duration_seconds = int((datetime.utcnow() - stage_start_times[stage]).total_seconds())

            try:
                save_step_result(
                    db,
                    execution_id,
                    stage,
                    result,
                    duration_seconds=duration_seconds,
                )

                # Cache trends for reuse
                if stage == "trends_keywords":
                    cache_trends_result(request, result)
            except Exception as e:
                logger.error(f"Failed to persist stage '{stage}' result: {e}")

        # Get Brave Search API key from organization settings
        brave_api_key = _get_brave_api_key(db, request.user_id)

        # Create orchestrator with project context
        orchestrator = ContentPipelineOrchestrator(
            llm_client=llm_client,
            rag_retriever=retrieve_brand_voice_examples,
            on_stage_start=on_stage_start,
            on_stage_complete=on_stage_complete,
            agent_logger=AgentLogger(db, execution_id),
            project_name=project_name,  # Pass project name to orchestrator
        )

        # Run pipeline
        logger.info(f"Starting pipeline {pipeline_id} for topic: {request.topic}")

        result = await orchestrator.run(
            topic=request.topic,
            content_type=request.content_type,
            audience=request.audience,
            goal=request.goal,
            brand_voice=request.brand_voice,
            language=request.language,
            length_constraints=request.length_constraints,
            context_summary=request.context_summary,
            user_id=request.user_id,
            style_document_ids=request.style_document_ids,
            knowledge_document_ids=request.knowledge_document_ids,
            pipeline_id=pipeline_id,  # Pass pipeline_id for file logging
            db=db,  # Pass database session for activity tracking
            execution_id=execution_id,  # Pass execution ID for activity tracking
            brave_search_api_key=brave_api_key,  # Pass Brave API key for web search
        )

        logger.info(f"Pipeline {pipeline_id} completed successfully")

        return ContentPipelineResponse(
            success=True,
            pipeline_id=pipeline_id,
            result=result
        )

    except Exception as e:
        logger.error(f"Pipeline {pipeline_id} failed: {e}")

        # Record failure details for debug page visibility
        try:
            current_execution = db.query(PipelineExecution).filter(
                PipelineExecution.id == execution_id
            ).first()
            current_stage = current_execution.current_stage if current_execution else "unknown"

            complete_pipeline_execution(
                db,
                execution_id,
                {},
                status="failed",
                error_message=str(e),
                error_stage=current_stage,
            )
        except Exception as db_error:
            logger.error(f"Failed to mark execution {execution_id} as failed: {db_error}")

        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}"
        )


@router.post("/run/stream")
async def run_content_pipeline_stream(
    request: ContentPipelineRequest,
    db: Session = Depends(get_db)
):
    """
    Run the content pipeline with streaming updates.

    Returns Server-Sent Events with stage updates as they complete.
    Saves execution history and step results to database.
    Uses Redis caching for trends & keywords.
    """
    pipeline_id = generate_pipeline_id()

    # Look up project name if project_id is provided
    project_name = None
    if request.project_id:
        from .models import Project
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if project:
            project_name = project.name
            logger.info(f"Pipeline running for project: {project_name} (ID: {request.project_id})")

            # If this is a sub-project with a parent, retrieve main project content from RAG
            if project.parent_project_id and project.campaign_id:
                logger.info(f"🔗 SUB-PROJECT DETECTED: {project_name} (parent_id: {project.parent_project_id}, campaign_id: {project.campaign_id})")
                try:
                    # Query RAG for main project content in this campaign
                    from .models import RagDocument
                    main_docs = db.query(RagDocument).filter(
                        RagDocument.campaign_id == project.campaign_id,
                        RagDocument.collection == "knowledge_base"
                    ).order_by(RagDocument.created_at.desc()).all()

                    if main_docs:
                        # Use the most recent main project document
                        logger.info(f"📚 Found {len(main_docs)} RAG documents for campaign {project.campaign_id}")
                        # Set campaign_id for RAG filtering during pipeline execution
                        request.campaign_id = project.campaign_id

                        # Retrieve main project content chunks for context
                        parent_chunks = rag_storage.retrieve_chunks(
                            query=request.topic,
                            collection="knowledge_base",
                            k=5,  # Get top 5 most relevant chunks
                            campaign_id=project.campaign_id
                        )

                        if parent_chunks:
                            # Extract text from chunks and add to context
                            parent_content_text = "\n\n".join([
                                f"[From Main Project]: {chunk.get('text', '')}"
                                for chunk in parent_chunks[:3]  # Use top 3 chunks
                            ])

                            # Add to context_summary for the agents to use
                            if request.context_summary:
                                request.context_summary += f"\n\n**Main Project Reference Content:**\n{parent_content_text}"
                            else:
                                request.context_summary = f"**Main Project Reference Content:**\n{parent_content_text}"

                            logger.info(f"✅ Added main project content to context ({len(parent_chunks)} chunks)")
                    else:
                        logger.warning(f"⚠️  No RAG documents found for campaign {project.campaign_id}")
                except Exception as e:
                    logger.error(f"❌ Error retrieving main project content from RAG: {e}", exc_info=True)

    # Create database execution record
    execution = create_pipeline_execution(db, pipeline_id, request)
    execution_id = execution.id

    # Check for cached trends
    cached_trends = get_cached_trends(request)

    async def event_generator():
        """Generate SSE events for pipeline progress."""
        stages_completed = []
        stage_results = {}  # Store results for database persistence
        stage_start_times = {}  # Track when each stage starts (for duration)
        stage_summaries_data = {}  # Store human-readable summaries for database

        def on_stage_start(stage: str, message: str):
            # Track start time for duration calculation
            stage_start_times[stage] = datetime.utcnow()

            # Update current_stage in database for error tracking
            try:
                current_execution = db.query(PipelineExecution).filter(
                    PipelineExecution.id == execution_id
                ).first()
                if current_execution:
                    current_execution.current_stage = stage
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to update current_stage in database: {e}")

            """Callback for stage start."""
            event_data = {
                "type": "stage_start",
                "pipeline_id": pipeline_id,
                "stage": stage,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            return f"data: {json.dumps(event_data)}\n\n"

        def on_stage_complete(stage: str, result: Dict[str, Any]):
            """Callback for stage completion."""
            stages_completed.append(stage)
            stage_results[stage] = result

            # Calculate stage duration
            duration_seconds = 0
            if stage in stage_start_times:
                duration_seconds = int((datetime.utcnow() - stage_start_times[stage]).total_seconds())

            # Save step result to database
            try:
                save_step_result(db, execution_id, stage, result)
            except Exception as e:
                logger.error(f"Failed to save step result: {e}")

            # Cache trends & keywords result
            if stage == "trends_keywords":
                cache_trends_result(request, result)

            # Estimate tokens based on result content (rough estimation: ~4 chars per token)
            result_text = json.dumps(result)
            estimated_output_tokens = len(result_text) // 4

            # Rough input token estimation (agents typically use 500-2000 tokens of input)
            estimated_input_tokens = 1000  # Conservative estimate
            if stage == "writer":
                estimated_input_tokens = 2000  # Writer uses more context
            elif stage == "final_review":
                estimated_input_tokens = 2500  # Review agent sees full content

            # Include summary data, not full result (to keep SSE small)
            # Also generate human-readable action bullets for transparency
            summary = {}
            actions = []  # Human-readable bullets (top 3-5 per stage)
            if stage == "trends_keywords":
                primary_kw = result.get("primary_keywords", [])
                angles = result.get("angle_ideas", [])
                summary = {
                    "primary_keywords": primary_kw,
                    "angle_count": len(angles),
                    "cached": False,
                    "input_tokens": estimated_input_tokens,
                    "output_tokens": estimated_output_tokens
                }
                actions = [
                    f"Identified {len(primary_kw)} trending keywords: {', '.join(primary_kw[:3])}{'...' if len(primary_kw) > 3 else ''}",
                    f"Generated {len(angles)} unique content angles",
                    f"Analyzed search trends and audience interests"
                ]
            elif stage == "tone_of_voice":
                profile = result.get("style_profile", {})
                formality = profile.get("formality_level", "N/A")
                person = profile.get("person_preference", "N/A")

                # Phase 4: Track which style documents influenced tone analysis
                style_docs_provenance = []
                if request.style_document_ids:
                    try:
                        from app.models import RagDocument
                        style_docs = db.query(RagDocument).filter(RagDocument.id.in_(request.style_document_ids)).all()
                        style_docs_provenance = [{"id": doc.id, "name": doc.original_filename or doc.filename} for doc in style_docs]
                    except Exception as e:
                        logger.warning(f"Failed to fetch style documents: {e}")

                summary = {
                    "formality": formality,
                    "person": person,
                    "sources": style_docs_provenance,  # Phase 4: Document provenance
                    "input_tokens": estimated_input_tokens,
                    "output_tokens": estimated_output_tokens
                }
                # Use actual selected document count, not backend's docs_analyzed (which may be 0)
                doc_count = len(style_docs_provenance) if style_docs_provenance else result.get('docs_analyzed', 0)
                actions = [
                    f"Analyzed brand voice from {doc_count} reference documents",
                    f"Set formality level: {formality}",
                    f"Determined voice style: {person} perspective"
                ]
            elif stage == "structure_outline":
                sections = result.get("sections", [])
                promise = result.get("content_promise", "")
                summary = {
                    "sections": len(sections),
                    "promise": promise[:100],
                    "input_tokens": estimated_input_tokens,
                    "output_tokens": estimated_output_tokens
                }
                actions = [
                    f"Created outline with {len(sections)} main sections",
                    f"Defined content promise: {promise[:80]}...",
                    f"Structured flow for {request.audience} audience"
                ]
            elif stage == "writer":
                text = result.get("full_text", "")
                word_count = len(text.split())

                # Phase 4: Track which knowledge documents influenced content writing
                knowledge_docs_provenance = []
                if request.knowledge_document_ids:
                    try:
                        from app.models import RagDocument
                        knowledge_docs = db.query(RagDocument).filter(RagDocument.id.in_(request.knowledge_document_ids)).all()
                        knowledge_docs_provenance = [{"id": doc.id, "name": doc.original_filename or doc.filename} for doc in knowledge_docs]
                    except Exception as e:
                        logger.warning(f"Failed to fetch knowledge documents: {e}")

                summary = {
                    "word_count": word_count,
                    "preview": text[:200] + "..." if len(text) > 200 else text,
                    "sources": knowledge_docs_provenance,  # Phase 4: Document provenance
                    "input_tokens": estimated_input_tokens,
                    "output_tokens": estimated_output_tokens
                }
                actions = [
                    f"Generated {word_count:,} words of content",
                    f"Applied {request.brand_voice} brand voice throughout",
                    f"Wrote for {request.goal} goal"
                ]
            elif stage == "seo_optimizer":
                seo = result.get("on_page_seo", {})
                focus_kw = seo.get("focus_keyword", "")
                title = seo.get("title_tag", "")
                meta_desc = seo.get("meta_description", "")

                # Phase 3A: Extract before/after diff snippets
                diff_snippets = []
                try:
                    # Get before/after text for comparison
                    before_text = stage_results.get("writer", {}).get("full_text", "") if "writer" in stage_results else ""
                    after_text = result.get("optimized_text", "")

                    # 1. Show SEO title tag changes
                    if title:
                        # Extract original H1 from before_text
                        before_title = ""
                        if before_text:
                            # Look for markdown H1 (# Title) or first heading
                            lines = before_text.split('\n')
                            for line in lines[:5]:  # Check first 5 lines
                                if line.strip().startswith('# '):
                                    before_title = line.strip()[2:].strip()
                                    break

                        diff_snippets.append({
                            "before": before_title if before_title else "(no title tag)",
                            "after": title,
                            "type": "seo_title",
                            "reason": f"Optimized title tag for SEO ({len(title)} chars)"
                        })

                    # 2. Show meta description (newly created)
                    if meta_desc:
                        diff_snippets.append({
                            "before": "(not set)",
                            "after": meta_desc,
                            "type": "meta_description",
                            "reason": f"Created meta description for search engines ({len(meta_desc)} chars)"
                        })

                    # 3. Show content keyword optimization
                    if before_text and after_text:
                        # Show first meaningful difference (first paragraph that changed)
                        before_paras = before_text.split('\n\n')[:3]
                        after_paras = after_text.split('\n\n')[:3]

                        for i, (before_p, after_p) in enumerate(zip(before_paras, after_paras)):
                            if before_p.strip() != after_p.strip() and len(before_p) > 50:
                                diff_snippets.append({
                                    "before": before_p[:400] + "..." if len(before_p) > 400 else before_p,
                                    "after": after_p[:400] + "..." if len(after_p) > 400 else after_p,
                                    "type": "keyword_optimization",
                                    "reason": "SEO keyword optimization in content"
                                })
                                break  # Just show first content change
                except Exception as e:
                    logger.warning(f"Failed to generate SEO diff snippet: {e}")

                # Phase 3: Extract SEO changes for change log
                seo_changes = []
                if focus_kw:
                    seo_changes.append(f"Added focus keyword '{focus_kw}' throughout content")
                if title:
                    seo_changes.append(f"Optimized title tag for search engines")
                if meta_desc:
                    seo_changes.append(f"Created compelling meta description")
                if seo.get("h1"):
                    seo_changes.append(f"Optimized H1 heading structure")

                summary = {
                    "focus_keyword": focus_kw,
                    "title_tag": title,
                    "change_log": seo_changes,  # Phase 3: Include changes
                    "diff_snippets": diff_snippets,  # Phase 3A: Before/after diffs
                    "input_tokens": estimated_input_tokens,
                    "output_tokens": estimated_output_tokens
                }
                # Create more accurate action descriptions
                title_len = len(title)
                meta_len = len(meta_desc)
                title_status = "optimal" if 50 <= title_len <= 60 else ("acceptable" if 40 <= title_len <= 70 else "needs adjustment")
                meta_status = "optimal" if 150 <= meta_len <= 160 else ("acceptable" if 120 <= meta_len <= 165 else "needs adjustment")

                actions = [
                    f"Set focus keyword: '{focus_kw}'",
                    f"Created title tag ({title_len} chars, {title_status}): '{title[:50]}...'",
                    f"Created meta description ({meta_len} chars, {meta_status})",
                    f"Enhanced on-page SEO elements"
                ]
            elif stage == "originality_check":
                score = result.get("originality_score", "")
                flagged = result.get("flagged_passages", [])

                # Phase 3A: Extract before/after diff snippets from rewrites
                diff_snippets = []
                try:
                    for passage in flagged[:3]:  # Show top 3 rewrites (matches change_log count)
                        original = passage.get("original_text", "")
                        rewritten = passage.get("rewritten_text", "")
                        reason = passage.get("reason", "")

                        if original and rewritten:
                            diff_snippets.append({
                                "before": original[:400] + "..." if len(original) > 400 else original,
                                "after": rewritten[:400] + "..." if len(rewritten) > 400 else rewritten,
                                "type": "originality_rewrite",
                                "reason": reason[:120] if reason else "Improved originality"
                            })
                except Exception as e:
                    logger.warning(f"Failed to generate originality diff snippets: {e}")

                # Phase 3: Extract originality changes for change log
                orig_changes = []
                for passage in flagged[:3]:  # Show top 3 rewrites
                    reason = passage.get("reason", "")
                    if reason:
                        orig_changes.append(f"Rewrote passage: {reason[:100]}...")

                summary = {
                    "score": score,
                    "flagged_count": len(flagged),
                    "change_log": orig_changes,  # Phase 3: Include rewrites
                    "diff_snippets": diff_snippets,  # Phase 3A: Before/after diffs
                    "input_tokens": estimated_input_tokens,
                    "output_tokens": estimated_output_tokens
                }
                # Updated to reflect that agent applies fixes, not just flags
                has_rewritten_text = bool(result.get("rewritten_text"))
                actions = [
                    f"Originality score: {score}",
                    f"Rewrote {len(flagged)} passage(s) to improve originality" if flagged else "No rewrites needed - content is original",
                    f"Applied all originality fixes to content" if has_rewritten_text else "Content verified as original"
                ]
            elif stage == "final_review":
                changes = result.get("change_log", [])
                variants = result.get("suggested_variants", [])

                # Phase 3A: Extract before/after diff snippets from final review changes
                diff_snippets = []
                try:
                    # Get before/after text for comparison
                    before_text = stage_results.get("seo_optimizer", {}).get("optimized_text", "") if "seo_optimizer" in stage_results else ""
                    after_text = result.get("final_text", "")

                    if before_text and after_text and before_text != after_text:
                        # Show first 3 paragraphs that changed
                        before_paras = before_text.split('\n\n')
                        after_paras = after_text.split('\n\n')

                        diffs_found = 0
                        for i, (before_p, after_p) in enumerate(zip(before_paras, after_paras)):
                            if before_p.strip() != after_p.strip() and len(before_p) > 50 and diffs_found < 3:
                                # Try to match change to a specific change log entry
                                reason = changes[diffs_found] if diffs_found < len(changes) else "Editorial improvement"
                                diff_snippets.append({
                                    "before": before_p[:400] + "..." if len(before_p) > 400 else before_p,
                                    "after": after_p[:400] + "..." if len(after_p) > 400 else after_p,
                                    "type": "editorial_polish",
                                    "reason": reason[:120] if isinstance(reason, str) else "Editorial improvement"
                                })
                                diffs_found += 1
                except Exception as e:
                    logger.warning(f"Failed to generate final review diff snippets: {e}")

                summary = {
                    "changes": len(changes),
                    "variants": len(variants),
                    "change_log": changes,  # Phase 3: Include full change log
                    "diff_snippets": diff_snippets,  # Phase 3A: Before/after diffs
                    "input_tokens": estimated_input_tokens,
                    "output_tokens": estimated_output_tokens
                }
                actions = [
                    f"Applied {len(changes)} editorial improvements",
                    f"Generated {len(variants)} alternative versions",
                    f"Final quality check completed"
                ]

            # Phase 2: Calculate quality badges for transparency
            badges = []
            if stage == "seo_optimizer":
                # SEO Health Badges
                title = seo.get("title_tag", "")
                meta_desc = seo.get("meta_description", "")
                focus_kw = seo.get("focus_keyword", "")

                # Title length check (optimal: 50-60 chars)
                title_len = len(title)
                if 50 <= title_len <= 60:
                    badges.append({"type": "title_length", "status": "good", "label": "Title Length Optimal", "value": f"{title_len} chars"})
                elif 40 <= title_len < 50 or 60 < title_len <= 70:
                    badges.append({"type": "title_length", "status": "warning", "label": "Title Length Acceptable", "value": f"{title_len} chars"})
                else:
                    badges.append({"type": "title_length", "status": "error", "label": "Title Length Issues", "value": f"{title_len} chars"})

                # Meta description length check (optimal: 150-160 chars)
                meta_len = len(meta_desc)
                if 150 <= meta_len <= 160:
                    badges.append({"type": "meta_length", "status": "good", "label": "Meta Desc Optimal", "value": f"{meta_len} chars"})
                elif 120 <= meta_len < 150 or 160 < meta_len <= 165:
                    badges.append({"type": "meta_length", "status": "warning", "label": "Meta Desc Acceptable", "value": f"{meta_len} chars"})
                else:
                    badges.append({"type": "meta_length", "status": "error", "label": "Meta Desc Issues", "value": f"{meta_len} chars"})

                # Focus keyword in title
                if focus_kw.lower() in title.lower():
                    badges.append({"type": "keyword_in_title", "status": "good", "label": "Keyword in Title", "value": "✓"})
                else:
                    badges.append({"type": "keyword_in_title", "status": "warning", "label": "Keyword Not in Title", "value": "!"})

            elif stage == "originality_check":
                # Originality Score Badge
                try:
                    score_val = float(score) if isinstance(score, (int, float, str)) and score else 0
                    if score_val >= 90:
                        badges.append({"type": "originality", "status": "good", "label": "High Originality", "value": f"{score_val:.0f}%"})
                    elif score_val >= 70:
                        badges.append({"type": "originality", "status": "warning", "label": "Moderate Originality", "value": f"{score_val:.0f}%"})
                    else:
                        badges.append({"type": "originality", "status": "error", "label": "Low Originality", "value": f"{score_val:.0f}%"})
                except (ValueError, TypeError):
                    pass

            # Store complete stage summary for database
            complete_summary = {
                "duration_seconds": duration_seconds,
                "actions": actions,
                "summary": summary,
                "badges": badges  # Phase 2: Include badges in summary
            }
            stage_summaries_data[stage] = complete_summary

            # Update database with stage summary
            try:
                execution = db.query(PipelineExecution).filter(PipelineExecution.id == execution_id).first()
                if execution:
                    if not execution.stage_summaries:
                        execution.stage_summaries = {}
                    execution.stage_summaries[stage] = complete_summary
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to save stage summary: {e}")

            # Send SSE event with duration and actions for real-time UI
            event_data = {
                "type": "stage_complete",
                "pipeline_id": pipeline_id,
                "stage": stage,
                "duration_seconds": duration_seconds,
                "actions": actions,
                "summary": summary,
                "badges": badges,  # Phase 2: Include badges in SSE event
                "timestamp": datetime.utcnow().isoformat()
            }
            return f"data: {json.dumps(event_data)}\n\n"

        try:
            import asyncio
            import uuid

            # Create CheckpointSession if in checkpoint mode
            checkpoint_session_id = None
            if request.checkpoint_mode == "checkpoint":
                from datetime import timedelta

                checkpoint_session_id = f"ckpt_{str(uuid.uuid4())[:8]}_{pipeline_id[:8]}"
                checkpoint_session = CheckpointSession(
                    session_id=checkpoint_session_id,
                    execution_id=execution_id,
                    user_id=request.user_id,
                    mode="checkpoint",
                    status="active",
                    stages_completed=[],
                    stage_results={},
                    user_edits=[],
                    checkpoint_actions=[],
                    expires_at=datetime.utcnow() + timedelta(hours=2)  # 2 hour default timeout
                )
                db.add(checkpoint_session)
                db.commit()
                logger.info(f"Created checkpoint session: {checkpoint_session_id}")

            # Send initial event
            yield f"data: {json.dumps({'type': 'pipeline_start', 'pipeline_id': pipeline_id, 'execution_id': execution_id, 'checkpoint_session_id': checkpoint_session_id, 'checkpoint_mode': request.checkpoint_mode})}\n\n"

            # Create LLM client and orchestrator
            llm_client = LLMClientWrapper(user_id=request.user_id)

            # Create agent logger for capturing communication
            agent_logger = AgentLogger(db, execution_id)

            # Use asyncio Queue to yield events as they happen
            events_queue = asyncio.Queue()

            async def stage_start_callback(stage: str, message: str):
                await events_queue.put(on_stage_start(stage, message))

            async def stage_complete_callback(stage: str, result: Dict[str, Any]):
                await events_queue.put(on_stage_complete(stage, result))

            async def checkpoint_reached_callback(stage: str, result: Dict[str, Any], state: Any, session_id: str):
                """
                Checkpoint callback: sends SSE event and waits for user action.
                Polls CheckpointSession database until user responds.
                """
                logger.info(f"[CHECKPOINT] Stage '{stage}' reached, session: {session_id}")

                # Get previous stage results for before/after comparison
                session = db.query(CheckpointSession).filter(
                    CheckpointSession.session_id == session_id
                ).first()
                previous_results = session.stage_results if session else {}

                # Send checkpoint_reached SSE event
                checkpoint_event = {
                    "type": "checkpoint_reached",
                    "pipeline_id": pipeline_id,
                    "session_id": session_id,
                    "stage": stage,
                    "stage_output": result,  # Full stage output for user preview
                    "previous_results": previous_results,  # All previous stage results for comparison
                    "timestamp": datetime.utcnow().isoformat()
                }
                await events_queue.put(f"data: {json.dumps(checkpoint_event)}\n\n")
                logger.info(f"[CHECKPOINT] SSE event sent for stage: {stage}")

                # Update checkpoint session status
                session = db.query(CheckpointSession).filter(
                    CheckpointSession.session_id == session_id
                ).first()
                if session:
                    session.status = "waiting_approval"
                    session.current_stage = stage
                    stages = session.stages_completed or []
                    if stage not in stages:
                        stages.append(stage)
                    session.stages_completed = stages

                    # Store stage result
                    results = session.stage_results or {}
                    results[stage] = result
                    session.stage_results = results

                    db.commit()
                    logger.info(f"[CHECKPOINT] Session updated to waiting_approval for stage: {stage}")
                else:
                    logger.error(f"[CHECKPOINT] Session not found: {session_id}")
                    return {"action": "approve"}

                # Poll for user action (with timeout)
                max_wait_time = 3600  # 1 hour max wait
                poll_interval = 0.5  # Poll every 500ms
                elapsed = 0

                logger.info(f"[CHECKPOINT] Starting polling loop for stage: {stage}")
                poll_count = 0
                while elapsed < max_wait_time:
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
                    poll_count += 1

                    # Query fresh session from database (don't rely on refresh)
                    db.expire_all()
                    session = db.query(CheckpointSession).filter(
                        CheckpointSession.session_id == session_id
                    ).first()

                    if not session:
                        logger.error(f"[CHECKPOINT] Session disappeared: {session_id}")
                        return {"action": "approve"}

                    # Log polling progress every 5 seconds AND every 20 polls (10 seconds)
                    if int(elapsed) % 5 == 0 or poll_count % 20 == 0:
                        logger.info(f"[CHECKPOINT] Polling stage '{stage}': status={session.status}, elapsed={elapsed:.1f}s, poll#{poll_count}")

                    # Check if user has responded
                    if session.status == "active":
                        logger.info(f"[CHECKPOINT] User approved stage: {stage} (after {poll_count} polls, {elapsed:.1f}s)")
                        # User approved or edited
                        action = {"action": "approve"}

                        # Check for edited output
                        if session.stage_results and stage in session.stage_results:
                            latest_result = session.stage_results[stage]
                            if latest_result != result:  # User edited
                                action["edited_output"] = latest_result
                                action["action"] = "edit"
                                logger.info(f"[CHECKPOINT] User edited output for stage: {stage}")

                        return action

                    elif session.status == "restarting":
                        logger.info(f"[CHECKPOINT] User requested restart for stage: {stage}")
                        session.status = "active"  # Reset for next run
                        db.commit()
                        return {"action": "restart"}

                    elif session.status == "cancelled":
                        logger.info(f"[CHECKPOINT] User cancelled at stage: {stage}")
                        return {"action": "cancel"}

                    elif session.status == "paused":
                        logger.info(f"[CHECKPOINT] User saved/paused at stage: {stage}")
                        # User saved for later
                        return {"action": "cancel"}  # Stop pipeline

                    # Check if mode switched to automatic (approve_all)
                    if session.mode == "automatic":
                        logger.info(f"[CHECKPOINT] Mode switched to automatic at stage: {stage}")
                        session.status = "active"
                        db.commit()
                        return {"action": "approve_all"}

                # Timeout - default to approve
                logger.warning(f"[CHECKPOINT] Timeout after {elapsed:.1f}s for session {session_id} at stage {stage}")
                session.status = "active"
                db.commit()
                return {"action": "approve"}

            # Get Brave Search API key from organization settings
            brave_api_key = _get_brave_api_key(db, request.user_id)

            orchestrator = ContentPipelineOrchestrator(
                llm_client=llm_client,
                rag_retriever=retrieve_brand_voice_examples,
                on_stage_start=stage_start_callback,
                on_stage_complete=stage_complete_callback,
                on_checkpoint_reached=checkpoint_reached_callback if request.checkpoint_mode == "checkpoint" else None,
                agent_logger=agent_logger,
                project_name=project_name,  # Pass project name for RAG filtering
            )

            # Inject cached trends if available
            if cached_trends:
                logger.info(f"Using cached trends for pipeline {pipeline_id}")
                # Send cached trends event
                await events_queue.put(on_stage_start("trends_keywords", "Using cached trends..."))
                await events_queue.put(on_stage_complete("trends_keywords", cached_trends))
                # Update summary to show it was cached
                stage_results["trends_keywords"] = cached_trends

            # Run pipeline in a task so we can yield events as they come
            pipeline_task = asyncio.create_task(orchestrator.run(
                topic=request.topic,
                content_type=request.content_type,
                audience=request.audience,
                goal=request.goal,
                brand_voice=request.brand_voice,
                language=request.language,
                length_constraints=request.length_constraints,
                context_summary=request.context_summary,
                user_id=request.user_id,
                style_document_ids=request.style_document_ids,
                knowledge_document_ids=request.knowledge_document_ids,
                checkpoint_mode=request.checkpoint_mode,
                checkpoint_session_id=checkpoint_session_id,
                pipeline_id=pipeline_id,  # Pass pipeline_id for file logging
                db=db,  # Pass database session for activity tracking
                execution_id=execution_id,  # Pass execution ID for activity tracking
                brave_search_api_key=brave_api_key,  # Pass Brave API key for web search
            ))

            # Yield events as they come while pipeline runs
            # Track last heartbeat time to prevent connection timeout
            last_heartbeat = asyncio.get_event_loop().time()
            heartbeat_interval = 10.0  # Send heartbeat every 10 seconds

            while not pipeline_task.done():
                try:
                    # Wait for event with timeout to check if pipeline is done
                    event = await asyncio.wait_for(events_queue.get(), timeout=0.1)
                    yield event
                    # Reset heartbeat timer after sending an event
                    last_heartbeat = asyncio.get_event_loop().time()
                except asyncio.TimeoutError:
                    # No event yet, check if we need to send heartbeat
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_heartbeat >= heartbeat_interval:
                        # Send heartbeat to keep connection alive during long-running agents
                        heartbeat_data = {
                            "type": "heartbeat",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        yield f"data: {json.dumps(heartbeat_data)}\n\n"
                        last_heartbeat = current_time
                    continue

            # Get pipeline result
            result = await pipeline_task

            # Yield any remaining events
            while not events_queue.empty():
                event = await events_queue.get()
                yield event

            # Complete pipeline execution in database
            complete_pipeline_execution(db, execution_id, result, status="completed")

            # Mark checkpoint session as completed if in checkpoint mode
            if checkpoint_session_id:
                session = db.query(CheckpointSession).filter(
                    CheckpointSession.session_id == checkpoint_session_id
                ).first()
                if session:
                    session.status = "completed"
                    session.completed_at = datetime.utcnow()
                    db.commit()

            # Send completion event with full result
            completion_data = {
                "type": "pipeline_complete",
                "pipeline_id": pipeline_id,
                "execution_id": execution_id,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(completion_data)}\n\n"

        except Exception as e:
            logger.error(f"Pipeline stream error: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

            # Try to get the current stage from the execution record
            try:
                current_execution = db.query(PipelineExecution).filter(
                    PipelineExecution.id == execution_id
                ).first()
                current_stage = current_execution.current_stage if current_execution else "unknown"
            except Exception:
                current_stage = "unknown"

            # Save error to database with stage information
            try:
                complete_pipeline_execution(
                    db, execution_id, {},
                    status="failed",
                    error_message=str(e),
                    error_stage=current_stage
                )
                logger.info(f"Marked execution {execution_id} as failed at stage {current_stage}")
            except Exception as db_error:
                logger.error(f"Failed to save error to database: {db_error}")

            error_data = {
                "type": "pipeline_error",
                "pipeline_id": pipeline_id,
                "execution_id": execution_id,
                "error": str(e),
                "stage": current_stage,
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/stages")
async def get_pipeline_stages():
    """Get the list of pipeline stages."""
    return {
        "stages": [
            {
                "id": "trends_keywords",
                "name": "Trends & Keywords",
                "description": "Research trends and extract strategic keywords",
                "icon": "🔍"
            },
            {
                "id": "tone_of_voice",
                "name": "Tone of Voice",
                "description": "Analyze brand voice and create style profile",
                "icon": "🎨"
            },
            {
                "id": "structure_outline",
                "name": "Structure & Outline",
                "description": "Design content structure and narrative arc",
                "icon": "📋"
            },
            {
                "id": "writer",
                "name": "Writer",
                "description": "Write natural, human-like content",
                "icon": "✍️"
            },
            {
                "id": "seo_optimizer",
                "name": "SEO Optimizer",
                "description": "Optimize for search engines",
                "icon": "📈"
            },
            {
                "id": "originality_check",
                "name": "Originality Check",
                "description": "Check for plagiarism risk",
                "icon": "✅"
            },
            {
                "id": "final_review",
                "name": "Final Review",
                "description": "Polish and prepare for publication",
                "icon": "🎯"
            }
        ]
    }


class BrandVoiceAddRequest(BaseModel):
    """Request model for adding brand voice examples."""
    texts: List[str] = Field(..., description="List of text examples")
    source_type: str = Field(default="other", description="Source type: blog_post, linkedin_post, email, landing_page, other")
    enrich: bool = Field(default=True, description="Whether to enrich chunks with LLM metadata")
    user_id: int = Field(default=1, description="User ID for LLM service")


@router.post("/brand-voice/add")
async def add_brand_voice_examples(request: BrandVoiceAddRequest):
    """
    Add brand voice examples to the vector store for RAG.

    These examples will be used by the Tone-of-Voice agent to learn the brand style.
    Uses context-aware chunking and optional LLM enrichment for metadata.
    """
    try:
        if not request.texts:
            raise HTTPException(status_code=400, detail="No texts provided")

        all_chunks = []
        doc_id = f"doc_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        for i, text in enumerate(request.texts):
            # Context-aware chunking
            chunks = context_aware_chunk(text, max_chunk_size=500)

            if request.enrich:
                # Enrich with LLM metadata
                llm_client = LLMClientWrapper(user_id=request.user_id)
                chunk_enrichment_service.llm_service = llm_client

                enriched = await chunk_enrichment_service.enrich_chunks(
                    chunks,
                    doc_id=f"{doc_id}_{i}",
                    source_type=request.source_type
                )
                all_chunks.extend(enriched)
            else:
                # Basic chunks without enrichment
                for j, chunk_text in enumerate(chunks):
                    chunk = EnrichedChunk(
                        chunk_id=f"{doc_id}_{i}_{j}",
                        doc_id=f"{doc_id}_{i}",
                        text=chunk_text,
                        source_type=request.source_type
                    )
                    all_chunks.append(chunk)

        # Add to enhanced vector store
        enhanced_vector_store.add_chunks(all_chunks)

        # Also add to legacy store for backward compatibility
        plain_texts = [c.text for c in all_chunks]
        vector_store.add_texts(plain_texts)

        return {
            "success": True,
            "message": f"Added {len(all_chunks)} enriched chunks from {len(request.texts)} texts",
            "total_chunks": len(enhanced_vector_store.get_all_chunks()),
            "enriched": request.enrich
        }
    except Exception as e:
        logger.error(f"Failed to add brand voice examples: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brand-voice/search")
async def search_brand_voice(
    query: str,
    k: int = 5,
    source_type: Optional[str] = None,
    use_enhanced: bool = True
):
    """
    Search brand voice examples in the vector store.

    Args:
        query: Search query
        k: Number of results
        source_type: Filter by source type
        use_enhanced: Use enhanced store with metadata

    Useful for testing RAG retrieval.
    """
    try:
        if use_enhanced:
            results = enhanced_vector_store.similarity_search(
                query,
                k=k,
                source_type_filter=source_type
            )
            return {
                "query": query,
                "results": [chunk.to_dict() for chunk in results],
                "count": len(results),
                "store": "enhanced"
            }
        else:
            results = vector_store.similarity_search(query, k=k)
            return {
                "query": query,
                "results": results,
                "count": len(results),
                "store": "legacy"
            }
    except Exception as e:
        logger.error(f"Brand voice search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AdvancedSearchRequest(BaseModel):
    """Request model for advanced search with Phase 2 features."""
    query: str = Field(..., description="Primary search query")
    k: int = Field(default=10, description="Number of results")
    mode: str = Field(
        default="standard",
        description="Search mode: standard, reranked, hierarchical, expanded"
    )
    query_variants: Optional[List[str]] = Field(
        default=None,
        description="Additional query variants for expansion mode"
    )
    source_type: Optional[str] = Field(default=None, description="Filter by source type")
    style_tags: Optional[List[str]] = Field(default=None, description="Filter by style tags")
    audience_tags: Optional[List[str]] = Field(default=None, description="Filter by audience tags")
    use_reranking: bool = Field(default=True, description="Apply reranking in applicable modes")
    top_docs: int = Field(default=3, description="Top documents for hierarchical mode")
    chunks_per_doc: int = Field(default=5, description="Chunks per document for hierarchical mode")
    include_scores: bool = Field(default=False, description="Include relevance scores (reranked mode only)")


@router.post("/brand-voice/search/advanced")
async def advanced_brand_voice_search(request: AdvancedSearchRequest):
    """
    Advanced brand voice search with Phase 2 features.

    Supports multiple search modes:
    - **standard**: Basic similarity search
    - **reranked**: Two-stage with cross-encoder reranking
    - **hierarchical**: Document-first, then chunk retrieval
    - **expanded**: Multi-query with optional reranking

    Phase 2 features provide better precision and coherence.
    """
    try:
        filters = {}
        if request.source_type:
            filters["source_type_filter"] = request.source_type
        if request.style_tags:
            filters["style_tags_filter"] = request.style_tags
        if request.audience_tags:
            filters["audience_tags_filter"] = request.audience_tags

        if request.mode == "reranked" and request.include_scores:
            # Return scores with reranked results
            results = enhanced_vector_store.similarity_search_with_reranking(
                request.query,
                k=request.k,
                **filters
            )
            return {
                "query": request.query,
                "mode": request.mode,
                "results": [
                    {**chunk.to_dict(), "score": float(score)}
                    for chunk, score in results
                ],
                "count": len(results)
            }

        elif request.mode == "hierarchical":
            results = enhanced_vector_store.search_hierarchical(
                request.query,
                k=request.k,
                top_docs=request.top_docs,
                chunks_per_doc=request.chunks_per_doc,
                use_reranking=request.use_reranking,
                **filters
            )
        else:
            # Use unified advanced_search interface
            results = enhanced_vector_store.advanced_search(
                request.query,
                k=request.k,
                mode=request.mode,
                query_variants=request.query_variants,
                use_reranking=request.use_reranking,
                **filters
            )

        return {
            "query": request.query,
            "mode": request.mode,
            "results": [chunk.to_dict() for chunk in results],
            "count": len(results),
            "features": {
                "reranking": request.use_reranking and request.mode in ["reranked", "hierarchical", "expanded"],
                "hierarchical": request.mode == "hierarchical",
                "expansion": request.mode == "expanded"
            }
        }

    except Exception as e:
        logger.error(f"Advanced search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brand-voice/stats")
async def get_brand_voice_stats():
    """Get statistics about the brand voice vector store."""
    try:
        enhanced_chunks = enhanced_vector_store.get_all_chunks()

        # Aggregate stats
        source_types = {}
        style_tags = {}
        audience_tags = {}

        for chunk in enhanced_chunks:
            # Count source types
            st = chunk.source_type
            source_types[st] = source_types.get(st, 0) + 1

            # Count style tags
            for tag in chunk.style_tags:
                style_tags[tag] = style_tags.get(tag, 0) + 1

            # Count audience tags
            for tag in chunk.audience_tags:
                audience_tags[tag] = audience_tags.get(tag, 0) + 1

        return {
            "total_chunks": len(enhanced_chunks),
            "legacy_chunks": len(vector_store.texts),
            "source_types": source_types,
            "top_style_tags": dict(sorted(style_tags.items(), key=lambda x: x[1], reverse=True)[:10]),
            "top_audience_tags": dict(sorted(audience_tags.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    except Exception as e:
        logger.error(f"Brand voice stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/brand-voice/clear")
async def clear_brand_voice_store():
    """Clear all brand voice examples (use with caution)."""
    try:
        enhanced_vector_store.clear()
        return {
            "success": True,
            "message": "Enhanced brand voice store cleared"
        }
    except Exception as e:
        logger.error(f"Failed to clear brand voice store: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/single-agent/{agent_id}")
async def run_single_agent(
    agent_id: str,
    request: ContentPipelineRequest
):
    """
    Run a single agent from the pipeline.

    Useful for testing individual agents or re-running specific stages.
    """
    from .agents.content_pipeline import get_content_agent

    try:
        llm_client = LLMClientWrapper(user_id=request.user_id)
        agent = get_content_agent(agent_id, llm_client=llm_client)

        # Build kwargs based on agent requirements
        kwargs = {
            "topic": request.topic,
            "content_type": request.content_type,
            "audience": request.audience,
            "goal": request.goal,
            "brand_voice": request.brand_voice,
            "language": request.language,
            "length_constraints": request.length_constraints,
            "context_summary": request.context_summary,
        }

        result = await agent.run(**kwargs)

        return {
            "success": True,
            "agent_id": agent_id,
            "result": result
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Single agent execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PIPELINE HISTORY ENDPOINTS
# =============================================================================

@router.get("/history")
async def get_pipeline_history(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status: completed, failed, running"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    Get pipeline execution history.

    Returns a list of past pipeline executions with metadata.
    """
    try:
        from sqlalchemy.orm import joinedload

        query = db.query(PipelineExecution).options(
            joinedload(PipelineExecution.step_results)
        )

        # Apply filters
        if user_id:
            query = query.filter(PipelineExecution.user_id == user_id)
        if project_id:
            query = query.filter(PipelineExecution.project_id == project_id)
        if status:
            query = query.filter(PipelineExecution.status == status)

        # Get total count
        total = query.count()

        # Get paginated results
        executions = query.order_by(
            PipelineExecution.created_at.desc()
        ).offset(offset).limit(limit).all()

        # Build execution list with model information
        execution_list = []
        for ex in executions:
            # Get model used from first step (if any steps exist)
            model_used = None
            if ex.step_results:
                first_step = next((s for s in ex.step_results if s.model_used), None)
                if first_step:
                    model_used = first_step.model_used

            execution_list.append({
                "id": ex.id,
                "pipeline_id": ex.pipeline_id,
                "user_id": ex.user_id,
                "project_id": ex.project_id,
                "topic": ex.topic,
                "content_type": ex.content_type,
                "audience": ex.audience,
                "brand_voice": ex.brand_voice,
                "status": ex.status,
                "word_count": ex.word_count,
                "originality_score": ex.originality_score,
                "total_duration_seconds": ex.total_duration_seconds,
                "created_at": ex.created_at.isoformat() if ex.created_at else None,
                "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
                "error_message": ex.error_message,
                "model_used": model_used,
            })

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "executions": execution_list
        }

    except Exception as e:
        logger.error(f"Failed to get pipeline history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{pipeline_id}")
async def get_pipeline_execution(
    pipeline_id: str,
    include_steps: bool = Query(True, description="Include step results"),
    include_full_result: bool = Query(False, description="Include full JSON result"),
    db: Session = Depends(get_db)
):
    """
    Get a specific pipeline execution by ID.

    Returns execution details, optionally with step results and full output.
    """
    try:
        execution = db.query(PipelineExecution).filter(
            PipelineExecution.pipeline_id == pipeline_id
        ).first()

        if not execution:
            raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")

        result = {
            "id": execution.id,
            "pipeline_id": execution.pipeline_id,
            "user_id": execution.user_id,
            "topic": execution.topic,
            "content_type": execution.content_type,
            "audience": execution.audience,
            "goal": execution.goal,
            "brand_voice": execution.brand_voice,
            "language": execution.language,
            "length_constraints": execution.length_constraints,
            "context_summary": execution.context_summary,
            "status": execution.status,
            "current_stage": execution.current_stage,
            "final_content": execution.final_content,
            "word_count": execution.word_count,
            "originality_score": execution.originality_score,
            "total_duration_seconds": execution.total_duration_seconds,
            "error_message": execution.error_message,
            "error_stage": execution.error_stage,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "created_at": execution.created_at.isoformat() if execution.created_at else None,
        }

        if include_full_result:
            result["final_result"] = execution.final_result

        if include_steps:
            steps = db.query(PipelineStepResult).filter(
                PipelineStepResult.execution_id == execution.id
            ).order_by(PipelineStepResult.stage_order).all()

            result["steps"] = [
                {
                    "stage": step.stage,
                    "stage_order": step.stage_order,
                    "status": step.status,
                    "result": step.result,
                    "duration_seconds": step.duration_seconds,
                    "tokens_used": step.tokens_used,
                    "error_message": step.error_message,
                    "started_at": step.started_at.isoformat() if step.started_at else None,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                }
                for step in steps
            ]

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pipeline execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{pipeline_id}/timeline")
async def get_pipeline_timeline(
    pipeline_id: str,
    db: Session = Depends(get_db)
):
    """
    Get stage-by-stage timeline with human-readable summaries.

    Phase 1B: Retrospective timeline view for transparency.
    Returns what each agent did with action bullets and durations.
    """
    try:
        execution = db.query(PipelineExecution).filter(
            PipelineExecution.pipeline_id == pipeline_id
        ).first()

        if not execution:
            raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")

        # Return stage summaries with metadata
        timeline = {
            "pipeline_id": execution.pipeline_id,
            "status": execution.status,
            "total_duration": execution.total_duration_seconds,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "stages": execution.stage_summaries or {},
            "metadata": {
                "topic": execution.topic,
                "content_type": execution.content_type,
                "word_count": execution.word_count,
                "originality_score": execution.originality_score,
                "brave_metrics": execution.final_result.get("brave_metrics") if execution.final_result else None
            }
        }

        return timeline

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pipeline timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{pipeline_id}/content")
async def get_pipeline_content(
    pipeline_id: str,
    db: Session = Depends(get_db)
):
    """
    Get just the final content from a pipeline execution.

    Useful for quick access to generated content without full metadata.
    """
    try:
        execution = db.query(PipelineExecution).filter(
            PipelineExecution.pipeline_id == pipeline_id
        ).first()

        if not execution:
            raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")

        if execution.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Pipeline {pipeline_id} is not completed (status: {execution.status})"
            )

        return {
            "pipeline_id": pipeline_id,
            "topic": execution.topic,
            "content": execution.final_content,
            "word_count": execution.word_count,
            "seo_metadata": execution.final_result.get("seo_version", {}).get("on_page_seo", {}) if execution.final_result else {},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pipeline content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{pipeline_id}")
async def delete_pipeline_execution(
    pipeline_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a pipeline execution and its step results.
    """
    try:
        execution = db.query(PipelineExecution).filter(
            PipelineExecution.pipeline_id == pipeline_id
        ).first()

        if not execution:
            raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")

        db.delete(execution)
        db.commit()

        return {
            "success": True,
            "message": f"Pipeline {pipeline_id} deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete pipeline execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/stats/summary")
async def get_pipeline_stats(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    db: Session = Depends(get_db)
):
    """
    Get aggregate statistics for pipeline executions.
    """
    try:
        from sqlalchemy import func
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = db.query(PipelineExecution).filter(
            PipelineExecution.created_at >= cutoff_date
        )

        if user_id:
            query = query.filter(PipelineExecution.user_id == user_id)

        total_executions = query.count()
        completed = query.filter(PipelineExecution.status == "completed").count()
        failed = query.filter(PipelineExecution.status == "failed").count()

        # Average metrics for completed pipelines
        completed_query = query.filter(PipelineExecution.status == "completed")
        avg_duration = db.query(func.avg(PipelineExecution.total_duration_seconds)).filter(
            PipelineExecution.status == "completed",
            PipelineExecution.created_at >= cutoff_date
        )
        if user_id:
            avg_duration = avg_duration.filter(PipelineExecution.user_id == user_id)
        avg_duration = avg_duration.scalar() or 0

        avg_words = db.query(func.avg(PipelineExecution.word_count)).filter(
            PipelineExecution.status == "completed",
            PipelineExecution.created_at >= cutoff_date
        )
        if user_id:
            avg_words = avg_words.filter(PipelineExecution.user_id == user_id)
        avg_words = avg_words.scalar() or 0

        # Top content types
        content_types = db.query(
            PipelineExecution.content_type,
            func.count(PipelineExecution.id).label('count')
        ).filter(
            PipelineExecution.created_at >= cutoff_date
        )
        if user_id:
            content_types = content_types.filter(PipelineExecution.user_id == user_id)
        content_types = content_types.group_by(
            PipelineExecution.content_type
        ).order_by(func.count(PipelineExecution.id).desc()).limit(5).all()

        return {
            "period_days": days,
            "total_executions": total_executions,
            "completed": completed,
            "failed": failed,
            "success_rate": round(completed / total_executions * 100, 1) if total_executions > 0 else 0,
            "avg_duration_seconds": round(float(avg_duration), 1),
            "avg_word_count": round(float(avg_words)),
            "top_content_types": [
                {"type": ct, "count": count}
                for ct, count in content_types
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get pipeline stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AGENT LOGS ENDPOINTS
# ============================================================================

@router.get("/history/{pipeline_id}/logs")
async def get_pipeline_logs(
    pipeline_id: str,
    include_prompts: bool = Query(True, description="Include prompt text"),
    include_responses: bool = Query(True, description="Include response text"),
    stage: Optional[str] = Query(None, description="Filter by specific stage"),
    db: Session = Depends(get_db)
):
    """
    Get detailed agent communication logs for a pipeline execution.

    Returns all prompts, responses, and metadata for debugging.
    """
    try:
        from .agent_logger import AgentLogger

        # Get execution
        execution = db.query(PipelineExecution).filter(
            PipelineExecution.pipeline_id == pipeline_id
        ).first()

        if not execution:
            raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")

        # Get logs
        logs = AgentLogger.get_logs_for_execution(
            db,
            execution.id,
            include_prompts=include_prompts,
            include_responses=include_responses
        )

        # Filter by stage if specified
        if stage:
            logs = [log for log in logs if log["stage"] == stage]

        return {
            "pipeline_id": pipeline_id,
            "execution_id": execution.id,
            "topic": execution.topic,
            "status": execution.status,
            "total_stages": len(logs),
            "logs": logs
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pipeline logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{pipeline_id}/logs")
async def delete_pipeline_logs(
    pipeline_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete all agent communication logs for a pipeline execution.

    This clears the detailed logs but keeps the execution record.
    """
    try:
        from .agent_logger import AgentLogger

        # Get execution
        execution = db.query(PipelineExecution).filter(
            PipelineExecution.pipeline_id == pipeline_id
        ).first()

        if not execution:
            raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")

        # Clear log fields but keep step results
        steps = db.query(PipelineStepResult).filter(
            PipelineStepResult.execution_id == execution.id
        ).all()

        for step in steps:
            step.prompt_system = None
            step.prompt_user = None
            step.input_context = None
            step.raw_response = None

        db.commit()

        return {
            "success": True,
            "message": f"Logs cleared for pipeline {pipeline_id}",
            "steps_cleared": len(steps)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete pipeline logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CHECKPOINT MODE ENDPOINTS
# =============================================================================

@router.post("/checkpoint/action")
async def checkpoint_action(
    request: CheckpointActionRequest,
    db: Session = Depends(get_db)
):
    """
    Process user action at a checkpoint.

    Actions:
    - approve: Continue to next stage
    - edit: Modify current stage output and continue
    - restart: Re-run current stage with new instructions
    - skip: Skip current stage
    - approve_all: Approve all remaining stages (exit checkpoint mode)
    - cancel: Cancel entire pipeline
    """
    try:
        from datetime import timedelta

        logger.info(f"[CHECKPOINT_ACTION] Received action '{request.action}' for session: {request.session_id}")

        # Get checkpoint session
        session = db.query(CheckpointSession).filter(
            CheckpointSession.session_id == request.session_id
        ).first()

        if not session:
            logger.error(f"[CHECKPOINT_ACTION] Session not found: {request.session_id}")
            raise HTTPException(status_code=404, detail=f"Checkpoint session {request.session_id} not found")

        logger.info(f"[CHECKPOINT_ACTION] Current session status: {session.status}, current_stage: {session.current_stage}")

        if session.status == "completed":
            raise HTTPException(status_code=400, detail="Checkpoint session already completed")

        if session.status == "cancelled":
            raise HTTPException(status_code=400, detail="Checkpoint session was cancelled")

        # Record action
        action_record = {
            "stage": session.current_stage,
            "action": request.action,
            "timestamp": datetime.utcnow().isoformat(),
            "details": {}
        }

        if request.edited_output:
            action_record["details"]["edited_output"] = request.edited_output

        if request.next_agent_instructions:
            action_record["details"]["next_agent_instructions"] = request.next_agent_instructions
            session.pending_instructions = request.next_agent_instructions

        if request.restart_instructions:
            action_record["details"]["restart_instructions"] = request.restart_instructions

        # Update checkpoint history
        checkpoint_actions = session.checkpoint_actions or []
        checkpoint_actions.append(action_record)
        session.checkpoint_actions = checkpoint_actions

        # Handle different actions
        if request.action == "approve":
            logger.info(f"[CHECKPOINT_ACTION] Setting status to 'active' for approve action")
            session.status = "active"
            session.last_action_at = datetime.utcnow()

        elif request.action == "edit":
            if not request.edited_output:
                raise HTTPException(status_code=400, detail="edited_output required for edit action")

            # Store edited output
            stage_results = session.stage_results or {}
            stage_results[session.current_stage] = request.edited_output
            session.stage_results = stage_results

            # Track edit
            user_edits = session.user_edits or []
            user_edits.append({
                "stage": session.current_stage,
                "action": "edited",
                "timestamp": datetime.utcnow().isoformat()
            })
            session.user_edits = user_edits

            session.status = "active"
            session.last_action_at = datetime.utcnow()

        elif request.action == "restart":
            # Mark for restart
            session.status = "restarting"
            session.last_action_at = datetime.utcnow()

        elif request.action == "skip":
            # Mark stage as skipped
            session.status = "active"
            session.last_action_at = datetime.utcnow()

        elif request.action == "approve_all":
            # Exit checkpoint mode, switch to automatic
            session.mode = "automatic"
            session.status = "active"
            session.last_action_at = datetime.utcnow()

        elif request.action == "cancel":
            session.status = "cancelled"
            session.completed_at = datetime.utcnow()

            # Update execution status
            execution = db.query(PipelineExecution).filter(
                PipelineExecution.id == session.execution_id
            ).first()
            if execution:
                execution.status = "cancelled"

        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")

        # Flush and commit immediately to ensure changes are visible to other sessions
        db.flush()
        db.commit()
        logger.info(f"[CHECKPOINT_ACTION] Action '{request.action}' committed. New status: {session.status}")

        return {
            "success": True,
            "session_id": session.session_id,
            "action": request.action,
            "new_status": session.status,
            "message": f"Checkpoint action '{request.action}' processed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Checkpoint action error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/checkpoint/save")
async def save_checkpoint(
    request: CheckpointSaveRequest,
    db: Session = Depends(get_db)
):
    """
    Save checkpoint session for later resumption.

    Sets status to 'paused' and extends expiration time.
    """
    try:
        from datetime import timedelta

        session = db.query(CheckpointSession).filter(
            CheckpointSession.session_id == request.session_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail=f"Checkpoint session {request.session_id} not found")

        # Update status and expiration
        session.status = "paused"
        session.last_action_at = datetime.utcnow()
        session.expires_at = datetime.utcnow() + timedelta(days=7)  # Keep for 7 days

        db.commit()

        return {
            "success": True,
            "session_id": session.session_id,
            "message": "Checkpoint session saved successfully",
            "expires_at": session.expires_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save checkpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/checkpoint/status/{session_id}", response_model=CheckpointStatusResponse)
async def get_checkpoint_status(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get current status of a checkpoint session.

    Returns session state, current stage, completed stages, and checkpoint history.
    """
    try:
        session = db.query(CheckpointSession).filter(
            CheckpointSession.session_id == session_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail=f"Checkpoint session {session_id} not found")

        return CheckpointStatusResponse(
            session_id=session.session_id,
            status=session.status,
            current_stage=session.current_stage,
            stages_completed=session.stages_completed or [],
            stage_results=session.stage_results or {},
            checkpoint_history=session.checkpoint_actions or [],
            waiting_for_approval=(session.status == "waiting_approval")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get checkpoint status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/checkpoint/list")
async def list_checkpoint_sessions(
    user_id: int = Query(..., description="User ID"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """
    List all checkpoint sessions for a user.

    Useful for showing "Resume pipeline" options.
    """
    try:
        query = db.query(CheckpointSession).filter(
            CheckpointSession.user_id == user_id
        )

        if status:
            query = query.filter(CheckpointSession.status == status)

        sessions = query.order_by(CheckpointSession.last_action_at.desc()).limit(20).all()

        return {
            "success": True,
            "sessions": [
                {
                    "session_id": s.session_id,
                    "execution_id": s.execution_id,
                    "status": s.status,
                    "mode": s.mode,
                    "current_stage": s.current_stage,
                    "stages_completed": s.stages_completed or [],
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "last_action_at": s.last_action_at.isoformat() if s.last_action_at else None,
                }
                for s in sessions
            ]
        }

    except Exception as e:
        logger.error(f"List checkpoint sessions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution/{execution_id}/activities")
async def get_agent_activities(
    execution_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all agent activities for a pipeline execution.

    Returns a list of agent activity records with:
    - Agent name and stage
    - Execution status and duration
    - Decisions made
    - RAG usage
    - Content changes
    - Quality metrics
    """
    try:
        from .models import AgentActivity

        activities = db.query(AgentActivity).filter(
            AgentActivity.pipeline_execution_id == execution_id
        ).order_by(AgentActivity.started_at).all()

        return {
            "success": True,
            "execution_id": execution_id,
            "activities": [
                {
                    "id": a.id,
                    "agent_name": a.agent_name,
                    "stage": a.stage,
                    "status": a.status,
                    "started_at": a.started_at.isoformat() if a.started_at else None,
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                    "duration_seconds": a.duration_seconds,
                    "input_summary": a.input_summary,
                    "output_summary": a.output_summary,
                    "decisions": a.decisions,
                    "rag_documents": a.rag_documents,
                    "content_before": a.content_before,
                    "content_after": a.content_after,
                    "changes_made": a.changes_made,
                    "performance_breakdown": a.performance_breakdown,
                    "model_used": a.model_used,
                    "input_tokens": a.input_tokens,
                    "output_tokens": a.output_tokens,
                    "estimated_cost": float(a.estimated_cost) if a.estimated_cost else 0,
                    "quality_metrics": a.quality_metrics,
                    "badges": a.badges,
                    "warnings": a.warnings,
                    "errors": a.errors,
                }
                for a in activities
            ]
        }

    except Exception as e:
        logger.error(f"Get agent activities error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution/{execution_id}/report")
async def generate_execution_report(
    execution_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate a comprehensive PDF report for a pipeline execution.

    Returns a PDF file with:
    - Executive summary
    - Pipeline metrics
    - Agent-by-agent breakdown
    - RAG usage analysis
    - Content transformations
    - Quality assessments
    - Cost analysis
    """
    try:
        # Check if execution exists
        execution = db.query(PipelineExecution).filter(
            PipelineExecution.id == execution_id
        ).first()

        if not execution:
            raise HTTPException(
                status_code=404,
                detail=f"Pipeline execution {execution_id} not found"
            )

        # Generate report
        generator = ReportGenerator(db)
        pdf_bytes = generator.generate_pdf_report(execution_id)

        # Return PDF as response
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=pipeline_{execution.pipeline_id}_report.pdf"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate report error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
