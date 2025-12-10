import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio

import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile, Form, Depends, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import RagDocument
from .document_processor import DocumentProcessor
from .storage import RAGStorage

router = APIRouter(prefix="/api/rag")
logger = logging.getLogger(__name__)

# Initialize processor and storage
document_processor = DocumentProcessor()
rag_storage = RAGStorage()


class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    project: str
    projects: List[str] = []
    collection: str
    status: str
    file_size: Optional[int]
    file_type: Optional[str]
    chunks_count: int
    upload_date: datetime

    class Config:
        from_attributes = True


data_dir = Path(__file__).resolve().parents[3] / "data" / "rag_docs"
data_dir.mkdir(parents=True, exist_ok=True)

# File size limit (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


def ingest_main_project_content_sync(
    db: Session,
    project_id: int,
    pipeline_id: int,
    content: str,
    topic: Optional[str] = None
) -> Dict[str, Any]:
    """
    Synchronous helper function to ingest main project content into RAG.
    Called directly from pipeline completion to avoid HTTP overhead.

    Args:
        db: Database session
        project_id: The project ID that generated the content
        pipeline_id: The pipeline execution ID
        content: The generated content text
        topic: Optional topic/title for the content

    Returns:
        Status dict with ingestion result
    """
    try:
        from ..models import Project, Campaign

        # Get project details
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"status": "error", "reason": "Project not found"}

        # Only ingest if this is a main project in an integrated campaign
        if not project.is_main_project:
            return {"status": "skipped", "reason": "Not a main project"}

        # Get campaign details
        if not project.campaign_id:
            return {"status": "skipped", "reason": "No campaign"}

        campaign = db.query(Campaign).filter(Campaign.id == project.campaign_id).first()
        if not campaign or campaign.campaign_type != 'integrated':
            return {"status": "skipped", "reason": "Not an integrated campaign"}

        # Create a temporary text file with the content
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        # Generate filename
        content_title = topic or f"Content from {project.name}"
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in content_title)
        unique_id = uuid.uuid4().hex[:8]
        filename = f"main_content_{unique_id}_{safe_title[:50]}.txt"

        # Save to permanent location
        save_path = data_dir / filename
        shutil.copy(temp_path, save_path)

        # Calculate file size
        file_size = save_path.stat().st_size

        # Create database record
        doc = RagDocument(
            filename=filename,
            original_filename=f"{content_title}.txt",
            file_path=str(save_path),
            file_size=file_size,
            file_type="txt",
            project_name=project.name,
            projects=[project.name],
            campaign_id=project.campaign_id,
            collection="knowledge_base",
            status="pending",
            organization_id=project.organization_id,
            user_id=None,
            created_at=datetime.utcnow()
        )

        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Process document asynchronously in a separate thread to avoid event loop conflicts
        logger.info(f"Processing main project content {doc.id} for RAG: {project.name} (pipeline: {pipeline_id})")
        try:
            import asyncio
            import concurrent.futures
            from threading import Thread

            # Helper function to run async code in a new thread with its own event loop
            def run_async_in_thread(coro):
                """Run async coroutine in a new thread with its own event loop."""
                result = {}
                exception = {}

                def thread_target():
                    try:
                        # Create a new event loop for this thread
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            result['value'] = loop.run_until_complete(coro)
                        finally:
                            loop.close()
                    except Exception as e:
                        exception['error'] = e

                thread = Thread(target=thread_target)
                thread.start()
                thread.join()  # Wait for completion

                if 'error' in exception:
                    raise exception['error']
                return result.get('value')

            # Run the async processing function in a separate thread
            run_async_in_thread(
                process_document_background(
                    doc_id=doc.id,
                    file_path=str(save_path),
                    file_type="txt",
                    original_filename=f"{content_title}.txt",
                    project_name=project.name,
                    collection="knowledge_base"
                )
            )

            logger.info(f"Successfully processed main project content into RAG: document_id={doc.id}")
        except Exception as proc_error:
            logger.error(f"Error processing document: {proc_error}", exc_info=True)
            # Mark document as failed
            doc.status = "failed"
            doc.error_message = str(proc_error)
            db.commit()
            return {"status": "error", "reason": f"Processing failed: {str(proc_error)}"}

        logger.info(f"Successfully ingested main project content into RAG: document_id={doc.id}, project={project.name}")

        return {
            "status": "ingested",
            "document_id": doc.id,
            "project_id": project_id,
            "project_name": project.name,
            "campaign_id": project.campaign_id,
            "pipeline_id": pipeline_id,
            "filename": filename
        }

    except Exception as e:
        logger.error(f"Error ingesting content: {e}", exc_info=True)
        return {"status": "error", "reason": str(e)}


async def process_document_background(
    doc_id: int,
    file_path: str,
    file_type: str,
    original_filename: str,
    project_name: str,
    collection: str = "knowledge_base"
):
    """
    Background task to process uploaded document.

    Args:
        doc_id: Database document ID
        file_path: Path to uploaded file
        file_type: File extension
        original_filename: Original filename
        project_name: Project name
        collection: Collection to store in (knowledge_base or brand_voice)
    """
    from ..database import SessionLocal

    db = SessionLocal()
    try:
        # Get document record
        doc = db.query(RagDocument).filter(RagDocument.id == doc_id).first()
        if not doc:
            logger.error(f"Document {doc_id} not found in database")
            return

        # Update status to processing
        doc.status = "processing"
        db.commit()

        # Process document (extract text and chunk)
        success, chunk_count, error_msg = await document_processor.process_document(
            file_path=file_path,
            file_type=file_type,
            doc_id=doc_id,
            original_filename=original_filename,
            project_name=project_name
        )

        if not success:
            doc.status = "failed"
            doc.error_message = error_msg
            doc.chunks_count = 0
            db.commit()
            logger.error(f"Failed to process document {doc_id}: {error_msg}")
            return

        # Get chunks for storage
        text = await document_processor._extract_text(file_path, file_type)
        chunks_list = document_processor._chunk_text(text)

        # Get document's projects array
        from .database import SessionLocal
        db = SessionLocal()
        try:
            doc_record = db.query(RagDocument).filter(RagDocument.id == doc_id).first()
            projects_list = doc_record.projects if doc_record and doc_record.projects else [project_name]
        finally:
            db.close()

        # Get campaign_id from document
        campaign_id = doc_record.campaign_id if doc_record else None

        # Create chunk metadata
        chunks_data = []
        for idx, chunk_text in enumerate(chunks_list):
            chunks_data.append({
                "chunk_id": f"doc{doc_id}_chunk{idx}",
                "document_id": doc_id,
                "document_name": original_filename,
                "project": project_name,  # Keep for backward compatibility
                "projects": projects_list,  # Array of projects this document belongs to
                "campaign_id": campaign_id,  # Campaign association for filtering
                "text": chunk_text,
                "full_text": chunk_text,  # For compatibility
                "chunk_index": idx,
                "created_at": datetime.utcnow().isoformat()
            })

        # Store chunks in vector store (using collection from document record)
        storage_success = rag_storage.store_chunks(chunks_data, collection=collection)

        if storage_success:
            doc.status = "completed"
            doc.chunks_count = chunk_count
            doc.processed_at = datetime.utcnow()
            doc.error_message = None
            db.commit()
            logger.info(f"Successfully processed document {doc_id}: {chunk_count} chunks stored in {collection}")
        else:
            doc.status = "failed"
            doc.error_message = "Failed to store chunks in vector database"
            doc.chunks_count = 0
            db.commit()
            logger.error(f"Failed to store chunks for document {doc_id}")

    except Exception as e:
        logger.error(f"Error in background processing for document {doc_id}: {e}", exc_info=True)
        try:
            doc = db.query(RagDocument).filter(RagDocument.id == doc_id).first()
            if doc:
                doc.status = "failed"
                doc.error_message = f"Processing error: {str(e)}"
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update document status: {db_error}")
    finally:
        db.close()


@router.get("/documents", response_model=List[DocumentResponse])
def list_documents(
    project: Optional[str] = Query(None, description="Filter by project name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    campaign_id: Optional[int] = Query(None, description="Filter by campaign ID"),
    db: Session = Depends(get_db)
) -> List[DocumentResponse]:
    """List all RAG documents, optionally filtered by project, status, or campaign."""
    query = db.query(RagDocument)

    if project:
        query = query.filter(RagDocument.project_name == project)
    if status:
        query = query.filter(RagDocument.status == status)
    if campaign_id is not None:
        query = query.filter(RagDocument.campaign_id == campaign_id)

    docs = query.order_by(RagDocument.created_at.desc()).all()

    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            project=doc.project_name,
            projects=doc.projects if doc.projects else [doc.project_name],
            collection=getattr(doc, 'collection', 'knowledge_base'),
            status=doc.status,
            file_size=doc.file_size,
            file_type=doc.file_type,
            chunks_count=doc.chunks_count or 0,
            upload_date=doc.created_at
        )
        for doc in docs
    ]


@router.post("/documents", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project: str = Form("General"),
    collection: str = Form("knowledge_base"),
    campaign_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
) -> DocumentResponse:
    """Upload a document to the knowledge base or brand voice collection."""
    # Validate file extension
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in {"pdf", "docx", "txt", "md"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: pdf, docx, txt, md"
        )

    # Read file content to check size
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    # Generate unique filename to avoid collisions
    unique_id = uuid.uuid4().hex[:8]
    safe_filename = f"{unique_id}_{file.filename}"
    save_path = data_dir / safe_filename

    # Save file to disk
    with save_path.open("wb") as buffer:
        buffer.write(content)

    # Validate collection parameter
    if collection not in ["knowledge_base", "brand_voice"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid collection: {collection}. Must be 'knowledge_base' or 'brand_voice'"
        )

    # Create database record with pending status
    doc = RagDocument(
        filename=safe_filename,
        original_filename=file.filename,
        file_path=str(save_path),
        file_size=file_size,
        file_type=ext,
        project_name=project,
        projects=[project] if project else ["General"],  # Initialize with first project
        campaign_id=campaign_id,  # Associate with campaign
        collection=collection,
        status="pending",
        organization_id=None,  # TODO: Get from auth context when implemented
        user_id=None,  # TODO: Get from auth context when implemented
        created_at=datetime.utcnow()
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Trigger background processing
    logger.info(f"Scheduling background processing for document {doc.id}: {file.filename} (collection: {collection})")
    background_tasks.add_task(
        process_document_background,
        doc_id=doc.id,
        file_path=str(save_path),
        file_type=ext,
        original_filename=file.filename,
        project_name=project,
        collection=collection
    )

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        project=doc.project_name,
        projects=doc.projects if doc.projects else [doc.project_name],
        collection=getattr(doc, 'collection', 'knowledge_base'),
        status=doc.status,
        file_size=doc.file_size,
        file_type=doc.file_type,
        chunks_count=doc.chunks_count or 0,
        upload_date=doc.created_at
    )


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db)
) -> DocumentResponse:
    """Get a specific document by ID."""
    doc = db.query(RagDocument).filter(RagDocument.id == doc_id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        project=doc.project_name,
        projects=doc.projects if doc.projects else [doc.project_name],
        collection=getattr(doc, 'collection', 'knowledge_base'),
        status=doc.status,
        file_size=doc.file_size,
        file_type=doc.file_type,
        chunks_count=doc.chunks_count or 0,
        upload_date=doc.created_at
    )


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Delete a document from the knowledge base."""
    doc = db.query(RagDocument).filter(RagDocument.id == doc_id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete chunks from vector store (using document's collection)
    chunks_deleted = 0
    collection = getattr(doc, 'collection', 'knowledge_base')  # Default to knowledge_base for old records
    try:
        chunks_deleted = rag_storage.delete_document_chunks(
            document_id=doc_id,
            collection=collection
        )
        logger.info(f"Deleted {chunks_deleted} chunks for document {doc_id} from {collection} collection")
    except Exception as e:
        logger.warning(f"Failed to delete chunks for document {doc_id} from {collection}: {e}")

    # Delete file from disk (with error handling)
    file_path = Path(doc.file_path)
    file_deleted = False
    file_error = None

    if file_path.exists():
        try:
            file_path.unlink()
            file_deleted = True
            logger.info(f"Deleted file: {file_path}")
        except PermissionError as e:
            file_error = f"Permission denied: {e}"
            logger.warning(f"Failed to delete file {file_path}: {e}")
        except OSError as e:
            file_error = f"OS error: {e}"
            logger.warning(f"Failed to delete file {file_path}: {e}")
        except Exception as e:
            file_error = f"Unexpected error: {e}"
            logger.error(f"Unexpected error deleting file {file_path}: {e}")

    # Delete from database (always proceed even if file deletion failed)
    try:
        db.delete(doc)
        db.commit()
        logger.info(f"Deleted document {doc_id} from database")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete document {doc_id} from database: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document from database: {str(e)}"
        )

    # Return status with file deletion info
    response = {"status": "deleted", "id": doc_id, "chunks_deleted": chunks_deleted}
    if file_error:
        response["warning"] = f"Document deleted but file removal failed: {file_error}"

    return response


@router.patch("/documents/{doc_id}/status")
def update_document_status(
    doc_id: int,
    status: str = Form(...),
    error_message: Optional[str] = Form(None),
    chunks_count: Optional[int] = Form(None),
    db: Session = Depends(get_db)
) -> DocumentResponse:
    """Update the processing status of a document."""
    doc = db.query(RagDocument).filter(RagDocument.id == doc_id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    valid_statuses = {"pending", "processing", "completed", "failed"}
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )

    doc.status = status
    doc.updated_at = datetime.utcnow()

    if error_message:
        doc.error_message = error_message
    if chunks_count is not None:
        doc.chunks_count = chunks_count
    if status == "completed":
        doc.processed_at = datetime.utcnow()

    db.commit()
    db.refresh(doc)

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        project=doc.project_name,
        projects=doc.projects if doc.projects else [doc.project_name],
        collection=getattr(doc, 'collection', 'knowledge_base'),
        status=doc.status,
        file_size=doc.file_size,
        file_type=doc.file_type,
        chunks_count=doc.chunks_count or 0,
        upload_date=doc.created_at
    )


@router.get("/stats")
def get_rag_stats(db: Session = Depends(get_db)) -> Dict:
    """Get statistics about the knowledge base."""
    total_docs = db.query(RagDocument).count()
    completed_docs = db.query(RagDocument).filter(RagDocument.status == "completed").count()
    pending_docs = db.query(RagDocument).filter(RagDocument.status == "pending").count()
    processing_docs = db.query(RagDocument).filter(RagDocument.status == "processing").count()
    failed_docs = db.query(RagDocument).filter(RagDocument.status == "failed").count()

    # Get total storage used
    from sqlalchemy import func
    total_size = db.query(func.sum(RagDocument.file_size)).scalar() or 0

    # Get chunk statistics
    total_chunks = db.query(func.sum(RagDocument.chunks_count)).scalar() or 0

    # Get storage stats
    storage_stats = rag_storage.get_stats(collection="knowledge_base")

    return {
        "total_documents": total_docs,
        "completed": completed_docs,
        "pending": pending_docs,
        "processing": processing_docs,
        "failed": failed_docs,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "total_chunks": total_chunks,
        "vector_store_chunks": storage_stats.get("total_chunks", 0)
    }


@router.patch("/documents/{doc_id}/projects")
def update_document_projects(
    doc_id: int,
    projects: List[str],
    db: Session = Depends(get_db)
) -> DocumentResponse:
    """Add or update projects for a document."""
    doc = db.query(RagDocument).filter(RagDocument.id == doc_id).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Update projects array
    doc.projects = projects if projects else ["General"]
    doc.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(doc)

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        project=doc.project_name,
        projects=doc.projects if doc.projects else [doc.project_name],
        collection=getattr(doc, 'collection', 'knowledge_base'),
        status=doc.status,
        file_size=doc.file_size,
        file_type=doc.file_type,
        chunks_count=doc.chunks_count or 0,
        upload_date=doc.created_at
    )


@router.post("/retrieve")
async def retrieve_chunks(
    query: str = Form(...),
    collection: str = Form("knowledge_base"),
    k: int = Form(10),
    document_ids: Optional[str] = Form(None),
    campaign_id: Optional[int] = Form(None)
) -> Dict[str, Any]:
    """
    Retrieve relevant chunks from the knowledge base.

    Args:
        query: Search query
        collection: Collection to search (knowledge_base or brand_voice)
        k: Number of results to return
        document_ids: Comma-separated list of document IDs to filter by
        campaign_id: Campaign ID to filter chunks by (for campaign-scoped search)

    Returns:
        Dictionary with chunks and metadata
    """
    try:
        # Parse document IDs if provided
        doc_ids = None
        if document_ids:
            try:
                doc_ids = [int(id.strip()) for id in document_ids.split(",") if id.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid document_ids format")

        # Retrieve chunks
        chunks = rag_storage.retrieve_chunks(
            query=query,
            collection=collection,
            k=k,
            document_ids=doc_ids,
            campaign_id=campaign_id
        )

        return {
            "query": query,
            "collection": collection,
            "k": k,
            "document_ids": doc_ids,
            "campaign_id": campaign_id,
            "chunks": chunks,
            "count": len(chunks)
        }

    except Exception as e:
        logger.error(f"Error retrieving chunks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")


@router.post("/ingest-content")
async def ingest_content(
    background_tasks: BackgroundTasks,
    project_id: int = Form(...),
    pipeline_id: int = Form(...),
    content: str = Form(...),
    topic: Optional[str] = Form(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Automatically ingest completed main project content into RAG.
    This endpoint is called when a main project completes content generation.
    
    Args:
        project_id: The project ID that generated the content
        pipeline_id: The pipeline execution ID
        content: The generated content text
        topic: Optional topic/title for the content
        
    Returns:
        Status of the ingestion
    """
    try:
        from ..models import Project, Campaign
        
        # Get project details
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Only ingest if this is a main project in an integrated campaign
        if not project.is_main_project:
            return {
                "status": "skipped",
                "reason": "Not a main project",
                "project_id": project_id
            }
        
        # Get campaign details
        campaign = None
        if project.campaign_id:
            campaign = db.query(Campaign).filter(Campaign.id == project.campaign_id).first()
            
            # Only ingest for integrated campaigns
            if campaign and campaign.campaign_type != 'integrated':
                return {
                    "status": "skipped",
                    "reason": "Not an integrated campaign",
                    "project_id": project_id,
                    "campaign_id": project.campaign_id
                }
        
        # Create a temporary text file with the content
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Generate filename
        content_title = topic or f"Content from {project.name}"
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in content_title)
        unique_id = uuid.uuid4().hex[:8]
        filename = f"main_content_{unique_id}_{safe_title[:50]}.txt"
        
        # Save to permanent location
        save_path = data_dir / filename
        import shutil
        shutil.copy(temp_path, save_path)
        
        # Calculate file size
        file_size = save_path.stat().st_size
        
        # Create database record
        doc = RagDocument(
            filename=filename,
            original_filename=f"{content_title}.txt",
            file_path=str(save_path),
            file_size=file_size,
            file_type="txt",
            project_name=project.name,
            projects=[project.name],
            campaign_id=project.campaign_id,
            collection="knowledge_base",
            status="pending",
            organization_id=project.organization_id,
            user_id=None,
            created_at=datetime.utcnow()
        )
        
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # Trigger background processing
        logger.info(f"Scheduling background processing for main project content {doc.id}: {project.name} (pipeline: {pipeline_id})")
        background_tasks.add_task(
            process_document_background,
            doc_id=doc.id,
            file_path=str(save_path),
            file_type="txt",
            original_filename=f"{content_title}.txt",
            project_name=project.name,
            collection="knowledge_base"
        )
        
        return {
            "status": "ingested",
            "document_id": doc.id,
            "project_id": project_id,
            "project_name": project.name,
            "campaign_id": project.campaign_id,
            "pipeline_id": pipeline_id,
            "filename": filename,
            "message": "Main project content queued for RAG ingestion"
        }
        
    except Exception as e:
        logger.error(f"Error ingesting content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")
