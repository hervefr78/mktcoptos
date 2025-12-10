"""Image generation API endpoints"""
import logging
import traceback
import os
import uuid
import base64
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from PIL import Image as PILImage
import httpx

from .llm_service import LLMService
from .database import get_db
from .models import GeneratedImage, PipelineExecution
from .settings_service import SettingsService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["images"])

# Image storage directory
IMAGES_DIR = Path("/app/uploads/images")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


class PromptGenerationRequest(BaseModel):
    """Request model for generating image prompt from content"""
    content: str
    content_type: str = "blog"
    style_hints: Optional[str] = None


class PromptGenerationResponse(BaseModel):
    """Response model for prompt generation"""
    prompt: str
    negative_prompt: str


class ImageGenerationRequest(BaseModel):
    """Request model for image generation"""
    prompt: str
    size: Optional[str] = None
    quality: Optional[str] = None
    style: Optional[str] = None
    pipeline_execution_id: Optional[int] = None  # Link to pipeline execution
    user_id: Optional[int] = None
    project_id: Optional[int] = None


class ImageGenerationResponse(BaseModel):
    """Response model for image generation"""
    id: int
    url: str
    prompt: str
    filename: str
    width: Optional[int] = None
    height: Optional[int] = None
    source: str
    created_at: str


@router.post("/generate-prompt", response_model=PromptGenerationResponse)
async def generate_image_prompt(request: PromptGenerationRequest):
    """
    Generate an image prompt from content using AI

    This endpoint analyzes the content and generates a detailed prompt
    suitable for image generation models.

    Args:
        request: Content and optional style hints

    Returns:
        PromptGenerationResponse with generated prompt and negative prompt
    """
    try:
        # Create a prompt to generate the image description
        system_prompt = """You are an expert at creating image generation prompts.
Given content, create a detailed, visually descriptive prompt for generating a hero image.
Focus on:
- Visual elements that represent the main theme
- Appropriate style (professional, modern, creative)
- Composition and color suggestions
- Mood and atmosphere

Also provide a negative prompt to avoid common issues."""

        user_prompt = f"""Content type: {request.content_type}
Style hints: {request.style_hints or 'professional, modern'}

Content to create image for:
{request.content[:2000]}

Generate:
1. A detailed image prompt (2-3 sentences)
2. A negative prompt to avoid issues

Format your response as:
PROMPT: [your image prompt]
NEGATIVE: [your negative prompt]"""

        response = await LLMService.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=500
        )

        # Parse the response
        prompt = ""
        negative_prompt = "blurry, low quality, distorted, ugly, bad anatomy"

        if "PROMPT:" in response:
            parts = response.split("NEGATIVE:")
            prompt = parts[0].replace("PROMPT:", "").strip()
            if len(parts) > 1:
                negative_prompt = parts[1].strip()
        else:
            prompt = response.strip()

        return PromptGenerationResponse(
            prompt=prompt,
            negative_prompt=negative_prompt
        )
    except Exception as e:
        logger.error(f"Prompt generation failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Prompt generation failed: {str(e)}")


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest, db: Session = Depends(get_db)):
    """
    Generate an image using the configured provider (OpenAI DALL-E, ComfyUI, or Stable Diffusion)
    and save it to the database with metadata.

    The provider, model, and default settings are loaded from the settings configuration.

    Args:
        request: Image generation request with prompt and optional parameters
        db: Database session

    Returns:
        ImageGenerationResponse with the saved image information
    """
    logger.info(f"Image generation request: prompt='{request.prompt[:100]}...', size={request.size}, quality={request.quality}, style={request.style}")
    try:
        # Get settings to determine provider and model
        user_id = request.user_id or 1
        settings = SettingsService.get_combined_settings(user_id, db)

        # Generate image and get URL
        url = await LLMService.generate_image(
            prompt=request.prompt,
            size=request.size,
            quality=request.quality,
            style=request.style,
            user_id=user_id
        )
        logger.info(f"Image generated successfully: {url[:100]}...")

        # Download and save the image
        image_data = None
        if url.startswith('data:image'):
            # Handle base64 encoded images
            header, encoded = url.split(',', 1)
            image_data = base64.b64decode(encoded)
        else:
            # Download from URL
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                image_data = response.content

        # Generate unique filename
        ext = ".png"
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = IMAGES_DIR / unique_filename

        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(image_data)

        # Get image dimensions
        width, height = None, None
        try:
            with PILImage.open(file_path) as img:
                width, height = img.size
        except Exception as e:
            logger.warning(f"Could not get image dimensions: {e}")

        # Determine source and model info based on provider
        source = settings.imageProvider
        openai_model = None
        sdxl_model = None

        if settings.imageProvider == 'openai':
            source = 'openai'
            openai_model = settings.openaiImageModel or 'gpt-image-1'
        elif settings.imageProvider == 'stable-diffusion':
            source = 'stable-diffusion'
            sdxl_model = 'sdxl-base-1.0'  # Default SDXL model
        elif settings.imageProvider == 'comfyui':
            source = 'comfyui'
            sdxl_model = getattr(settings, 'comfyuiModel', 'flux1-schnell-fp8.safetensors')

        # Create database record
        db_image = GeneratedImage(
            user_id=request.user_id,
            project_id=request.project_id,
            pipeline_execution_id=request.pipeline_execution_id,
            prompt=request.prompt,
            filename=unique_filename,
            file_path=str(file_path),
            file_size=len(image_data),
            mime_type='image/png',
            width=width,
            height=height,
            source=source,
            openai_model=openai_model,
            sdxl_model=sdxl_model,
            quality=request.quality,
            style=request.style,
            projects=[request.project_id] if request.project_id else []  # Initialize projects array
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)

        logger.info(f"Image saved to database: id={db_image.id}, filename={unique_filename}")

        # Return full URL path (frontend will prepend API_BASE)
        return ImageGenerationResponse(
            id=db_image.id,
            url=f"/api/images/{db_image.id}",  # Relative URL - frontend adds API_BASE
            prompt=db_image.prompt,
            filename=db_image.filename,
            width=db_image.width,
            height=db_image.height,
            source=db_image.source,
            created_at=db_image.created_at.isoformat() if db_image.created_at else datetime.utcnow().isoformat()
        )
    except ValueError as e:
        logger.error(f"Image generation validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Image generation failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


@router.get("/topics")
async def list_topics(db: Session = Depends(get_db)):
    """Get unique topics from pipeline executions for filtering"""
    try:
        # Get unique topics from pipeline executions that have images
        topics = db.query(PipelineExecution.topic, PipelineExecution.id).filter(
            PipelineExecution.id.in_(
                db.query(GeneratedImage.pipeline_execution_id).filter(
                    GeneratedImage.pipeline_execution_id.isnot(None)
                ).distinct()
            )
        ).distinct().all()

        return [{"id": t.id, "topic": t.topic} for t in topics]
    except Exception as e:
        logger.error(f"Failed to list topics: {str(e)}")
        return []


@router.get("/list")
async def list_images(
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    sortBy: str = Query("newest"),
    model: Optional[str] = Query(None),
    contentType: Optional[str] = Query(None),
    topicId: Optional[int] = Query(None),
    projectId: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List images from the database with pagination and filtering

    Args:
        limit: Maximum number of images to return
        page: Page number (1-indexed)
        sortBy: Sort order (newest, oldest)
        model: Filter by model/source
        contentType: Filter by content type (blog post, etc.)
        topicId: Filter by pipeline execution ID (topic)

    Returns:
        Paginated list of image records
    """
    try:
        from sqlalchemy.orm import joinedload
        offset = (page - 1) * limit
        query = db.query(GeneratedImage).options(
            joinedload(GeneratedImage.project),
            joinedload(GeneratedImage.pipeline_execution).joinedload(PipelineExecution.project)
        )

        # Apply model filter
        if model:
            if model in ["comfyui", "stable-diffusion", "manual-upload"]:
                query = query.filter(GeneratedImage.source == model)
            else:
                query = query.filter(GeneratedImage.openai_model == model)

        # Apply topic filter
        if topicId:
            query = query.filter(GeneratedImage.pipeline_execution_id == topicId)

        # Apply project filter
        if projectId:
            from sqlalchemy import or_, func
            # Images are associated with projects via:
            # 1. project_id field (single project)
            # 2. projects JSON array (multiple projects)
            # 3. pipeline_execution.project_id (inherited from content generation)
            query = query.filter(
                or_(
                    GeneratedImage.project_id == projectId,
                    func.json_contains(GeneratedImage.projects, str(projectId)),
                )
            )

        # Apply content type filter
        if contentType and contentType != "all":
            query = query.join(PipelineExecution).filter(
                PipelineExecution.content_type == contentType
            )

        # Get total count
        total = query.count()

        # Apply sorting
        if sortBy == "oldest":
            query = query.order_by(GeneratedImage.created_at.asc())
        else:
            query = query.order_by(GeneratedImage.created_at.desc())

        # Apply pagination
        images = query.offset(offset).limit(limit).all()

        # Load all projects referenced in images for efficient lookup
        from .models import Project
        all_project_ids = set()
        for img in images:
            if img.project_id:
                all_project_ids.add(img.project_id)
            if img.projects:
                all_project_ids.update(img.projects)
            if img.pipeline_execution and img.pipeline_execution.project_id:
                all_project_ids.add(img.pipeline_execution.project_id)

        projects_map = {}
        if all_project_ids:
            projects = db.query(Project).filter(Project.id.in_(all_project_ids)).all()
            projects_map = {p.id: {"id": p.id, "name": p.name} for p in projects}

        # Format response with content association
        def format_image(img):
            result = {
                "id": img.id,
                "prompt": img.prompt,
                "filename": img.filename,
                "width": img.width,
                "height": img.height,
                "source": img.source,
                "openaiModel": img.openai_model,
                "sdxlModel": img.sdxl_model,
                "quality": img.quality,
                "style": img.style,
                "createdAt": img.created_at.isoformat() if img.created_at else None,
                "pipelineExecution": None,
                "project": None,
                "projects": []
            }

            # Collect all unique project IDs associated with this image
            unique_project_ids = set()

            # From projects array (multi-project associations)
            if img.projects:
                unique_project_ids.update(img.projects)

            # From direct project_id
            if img.project_id:
                unique_project_ids.add(img.project_id)

            # From pipeline execution's project
            if img.pipeline_execution and img.pipeline_execution.project_id:
                unique_project_ids.add(img.pipeline_execution.project_id)

            # Build projects array from project IDs
            result["projects"] = [
                projects_map[pid] for pid in unique_project_ids
                if pid in projects_map
            ]

            # Keep legacy "project" field for backward compatibility (first project or None)
            if result["projects"]:
                result["project"] = result["projects"][0]

            # Add pipeline execution info if available
            if img.pipeline_execution:
                result["pipelineExecution"] = {
                    "id": img.pipeline_execution.id,
                    "pipelineId": img.pipeline_execution.pipeline_id,
                    "topic": img.pipeline_execution.topic,
                    "contentType": img.pipeline_execution.content_type,
                    "status": img.pipeline_execution.status,
                    "projectId": img.pipeline_execution.project_id
                }
            return result

        return {
            "images": [format_image(img) for img in images],
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "totalPages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        logger.error(f"Failed to list images: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to list images: {str(e)}")


@router.post("/generate/marketing")
async def generate_marketing_image(prompt: str, context: Optional[str] = None):
    """
    Generate a marketing image with optimized settings

    This endpoint uses marketing-optimized defaults (vivid style, HD quality)

    Args:
        prompt: Image description
        context: Optional marketing context for better prompts

    Returns:
        Image URL
    """
    try:
        # Enhance prompt with marketing context if provided
        enhanced_prompt = prompt
        if context:
            enhanced_prompt = f"{prompt}. Marketing context: {context}"

        url = await LLMService.generate_image(
            prompt=enhanced_prompt,
            size="1792x1024",  # Landscape for marketing materials
            quality="hd",
            style="vivid"
        )

        return {
            "url": url,
            "prompt": enhanced_prompt,
            "type": "marketing"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Marketing image generation failed: {str(e)}")


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    source: str = Form("manual-upload"),
    db: Session = Depends(get_db)
):
    """
    Upload an image to the gallery

    Args:
        file: The image file to upload
        prompt: Description of the image
        source: Source of the image (default: manual-upload)

    Returns:
        The created image record
    """
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024
        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is 10MB"
            )

        # Generate unique filename
        ext = Path(file.filename).suffix.lower() or ".png"
        if ext == ".jpg":
            ext = ".jpeg"
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = IMAGES_DIR / unique_filename

        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(content)

        # Get image dimensions
        width, height = None, None
        try:
            with PILImage.open(file_path) as img:
                width, height = img.size
        except Exception as e:
            logger.warning(f"Could not get image dimensions: {e}")

        # Determine mime type
        mime_type = file.content_type or "image/png"

        # Create database record
        db_image = GeneratedImage(
            prompt=prompt,
            filename=unique_filename,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=mime_type,
            width=width,
            height=height,
            source=source
        )
        db.add(db_image)
        db.commit()
        db.refresh(db_image)

        logger.info(f"Image uploaded successfully: {unique_filename}")

        return {
            "id": db_image.id,
            "prompt": db_image.prompt,
            "filename": db_image.filename,
            "width": db_image.width,
            "height": db_image.height,
            "source": db_image.source,
            "createdAt": db_image.created_at.isoformat() if db_image.created_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload image: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@router.get("/{image_id}")
async def get_image(image_id: int, db: Session = Depends(get_db)):
    """
    Get an image by ID (returns the actual image file)

    Args:
        image_id: The image ID

    Returns:
        The image file
    """
    try:
        image = db.query(GeneratedImage).filter(GeneratedImage.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")

        file_path = Path(image.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Image file not found")

        return FileResponse(
            path=str(file_path),
            media_type=image.mime_type or "image/png",
            filename=image.filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get image: {str(e)}")


@router.patch("/{image_id}/projects")
async def update_image_projects(
    image_id: int,
    project_ids: List[int] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Update project associations for an image

    Args:
        image_id: The image ID
        project_ids: List of project IDs to associate with the image

    Returns:
        Updated image info with project details
    """
    try:
        from .models import Project

        # Get the image
        image = db.query(GeneratedImage).filter(GeneratedImage.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")

        # Validate that all project IDs exist
        if project_ids:
            projects = db.query(Project).filter(Project.id.in_(project_ids)).all()
            if len(projects) != len(project_ids):
                raise HTTPException(status_code=400, detail="One or more project IDs are invalid")

        # Update projects array
        image.projects = project_ids if project_ids else []
        image.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(image)

        # Return updated image info
        return {
            "id": image.id,
            "projects": image.projects,
            "updated_at": image.updated_at.isoformat() if image.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update image projects: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to update image projects: {str(e)}")


@router.delete("/{image_id}")
async def delete_image(image_id: int, db: Session = Depends(get_db)):
    """
    Delete an image by ID

    Args:
        image_id: The image ID

    Returns:
        Success message
    """
    try:
        image = db.query(GeneratedImage).filter(GeneratedImage.id == image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")

        # Delete file from disk
        file_path = Path(image.file_path)
        if file_path.exists():
            file_path.unlink()

        # Delete database record
        db.delete(image)
        db.commit()

        logger.info(f"Image deleted successfully: {image_id}")
        return {"message": "Image deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete image: {str(e)}")
