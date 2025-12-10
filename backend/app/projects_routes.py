"""
Projects API routes.
"""
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .database import get_db
from .models import Project, PipelineExecution, Campaign, Category
from .errors import not_found

router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_current_user_id(request: Request) -> int:
    """
    Get current user ID from request header.

    TODO: Replace with proper JWT/token authentication
    For now, uses X-User-ID header or defaults to user 1 for development.
    """
    user_id = request.headers.get("X-User-ID")
    if user_id:
        try:
            return int(user_id)
        except ValueError:
            pass
    return 1  # Default for development


def get_organization_id(request: Request) -> int:
    """
    Get organization ID from request header.

    TODO: Replace with proper authentication that includes org context
    For now, uses X-Organization-ID header or defaults to org 1 for development.
    """
    org_id = request.headers.get("X-Organization-ID")
    if org_id:
        try:
            return int(org_id)
        except ValueError:
            pass
    return 1  # Default for development


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    default_tone: Optional[str] = Field("professional", max_length=50)
    default_target_audience: Optional[str] = Field(None, max_length=500)
    language: Optional[str] = Field("auto", max_length=50, description="Project language: auto, en, fr, de, es, it")
    campaign_id: int = Field(..., description="Campaign the project belongs to", gt=0)
    content_type: Optional[str] = Field(None, max_length=100)
    is_main_project: bool = Field(default=False, description="Whether this is a main project in an integrated campaign")
    parent_project_id: Optional[int] = Field(None, description="Parent project ID for sub-projects", gt=0)
    inherit_tone: bool = Field(default=True, description="Whether to inherit tone from parent project")


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    default_tone: Optional[str] = Field(None, max_length=50)
    default_target_audience: Optional[str] = Field(None, max_length=500)
    language: Optional[str] = Field(None, max_length=50, description="Project language: auto, en, fr, de, es, it")
    is_archived: Optional[bool] = None
    campaign_id: Optional[int] = Field(None, gt=0)
    content_type: Optional[str] = Field(None, max_length=100)
    is_main_project: Optional[bool] = None
    parent_project_id: Optional[int] = Field(None, gt=0)
    inherit_tone: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    default_tone: Optional[str]
    default_target_audience: Optional[str]
    language: Optional[str]
    category_id: Optional[int]
    category_name: Optional[str]
    campaign_id: Optional[int]
    campaign_name: Optional[str]
    content_type: Optional[str]
    is_main_project: bool
    parent_project_id: Optional[int]
    parent_project_name: Optional[str] = None
    inherit_tone: bool
    is_archived: bool
    created_at: datetime
    updated_at: Optional[datetime]
    recent_executions: Optional[List[dict]] = None

    class Config:
        from_attributes = True


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    request: Request,
    include_archived: bool = Query(False, description="Include archived projects"),
    include_recent_content: bool = Query(False, description="Include recent content executions"),
    content_limit: int = Query(5, description="Number of recent executions to include"),
    db: Session = Depends(get_db)
):
    """List all projects for the current user's organization."""
    organization_id = get_organization_id(request)
    query = (
        db.query(Project)
        .options(joinedload(Project.campaign), joinedload(Project.category))
        .filter(Project.organization_id == organization_id)
    )

    if not include_archived:
        query = query.filter(Project.is_archived == False)

    projects = query.order_by(Project.created_at.desc()).all()

    if include_recent_content and projects:
        # Fetch recent content for these projects
        project_ids = [p.id for p in projects]
        
        # Get executions for these projects
        executions = db.query(PipelineExecution).options(
            joinedload(PipelineExecution.step_results)
        ).filter(
            PipelineExecution.project_id.in_(project_ids)
        ).order_by(
            PipelineExecution.project_id,
            PipelineExecution.created_at.desc()
        ).all()
        
        # Group by project
        executions_by_project = {}
        for exec in executions:
            if exec.project_id not in executions_by_project:
                executions_by_project[exec.project_id] = []
            
            if len(executions_by_project[exec.project_id]) < content_limit:
                # Get model used from first step (if any steps exist)
                model_used = None
                if exec.step_results:
                    first_step = next((s for s in exec.step_results if s.model_used), None)
                    if first_step:
                        model_used = first_step.model_used
                
                # Convert to dict for response
                executions_by_project[exec.project_id].append({
                    "pipeline_id": exec.pipeline_id,
                    "topic": exec.topic,
                    "content_type": exec.content_type,
                    "status": exec.status,
                    "created_at": exec.created_at,
                    "word_count": exec.word_count,
                    "model_used": model_used,
                    "audience": exec.audience
                })
        
        # Attach to project objects
        for project in projects:
            project.recent_executions = executions_by_project.get(project.id, [])
            project.category_name = project.category.name if project.category else None
            project.campaign_name = project.campaign.name if project.campaign else None

    else:
        for project in projects:
            project.category_name = project.category.name if project.category else None
            project.campaign_name = project.campaign.name if project.campaign else None

    # Add parent project names for sub-projects
    for project in projects:
        if project.parent_project_id:
            parent = db.query(Project).filter(Project.id == project.parent_project_id).first()
            project.parent_project_name = parent.name if parent else None
        else:
            project.parent_project_name = None

    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific project by ID."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise not_found("Project", project_id)
    project.category_name = project.category.name if project.category else None
    project.campaign_name = project.campaign.name if project.campaign else None

    # Add parent project name if it exists
    if project.parent_project_id:
        parent = db.query(Project).filter(Project.id == project.parent_project_id).first()
        project.parent_project_name = parent.name if parent else None
    else:
        project.parent_project_name = None

    return project


@router.post("", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new project for the current user."""
    organization_id = get_organization_id(request)
    owner_id = get_current_user_id(request)

    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == project.campaign_id, Campaign.organization_id == organization_id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=400, detail="Invalid campaign")

    category: Optional[Category] = None
    if campaign.category_id:
        category = db.query(Category).filter(Category.id == campaign.category_id).first()

    brand_voice = {}
    if category:
        brand_voice["category"] = category.name
    if campaign.model:
        brand_voice["model"] = campaign.model

    # Validate parent project if specified
    parent_project = None
    if project.parent_project_id:
        parent_project = (
            db.query(Project)
            .filter(
                Project.id == project.parent_project_id,
                Project.campaign_id == campaign.id,
                Project.organization_id == organization_id,
            )
            .first()
        )
        if not parent_project:
            raise HTTPException(status_code=400, detail="Invalid parent project or parent not in same campaign")

        # If inheriting tone from parent, use parent's tone
        if project.inherit_tone and parent_project.default_tone:
            project.default_tone = parent_project.default_tone

    db_project = Project(
        organization_id=organization_id,
        owner_id=owner_id,
        name=project.name,
        description=project.description,
        default_tone=project.default_tone,
        default_target_audience=project.default_target_audience,
        language=project.language,
        campaign_id=campaign.id,
        category_id=campaign.category_id,
        brand_voice=brand_voice or None,
        content_type=project.content_type,
        is_main_project=project.is_main_project,
        parent_project_id=project.parent_project_id,
        inherit_tone=project.inherit_tone,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    db_project.category_name = category.name if category else None
    db_project.campaign_name = campaign.name
    db_project.parent_project_name = parent_project.name if parent_project else None
    return db_project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """Update a project."""
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise not_found("Project", project_id)

    update_data = project.dict(exclude_unset=True)
    category: Optional[Category] = None
    campaign: Optional[Campaign] = None

    if "campaign_id" in update_data:
        campaign = (
            db.query(Campaign)
            .filter(
                Campaign.id == update_data["campaign_id"],
                Campaign.organization_id == db_project.organization_id,
            )
            .first()
        )
        if not campaign:
            raise HTTPException(status_code=400, detail="Invalid campaign")
        db_project.campaign_id = campaign.id
        if campaign.category_id:
            category = db.query(Category).filter(Category.id == campaign.category_id).first()
            db_project.category_id = campaign.category_id

    # Validate parent project if being updated
    parent_project = None
    if "parent_project_id" in update_data and update_data["parent_project_id"]:
        parent_project = (
            db.query(Project)
            .filter(
                Project.id == update_data["parent_project_id"],
                Project.campaign_id == db_project.campaign_id,
                Project.organization_id == db_project.organization_id,
            )
            .first()
        )
        if not parent_project:
            raise HTTPException(status_code=400, detail="Invalid parent project or parent not in same campaign")

        # If inheriting tone from parent, use parent's tone
        if update_data.get("inherit_tone", True) and parent_project.default_tone:
            update_data["default_tone"] = parent_project.default_tone

    for field, value in update_data.items():
        if field == "campaign_id":
            continue
        setattr(db_project, field, value)

    # Refresh brand voice metadata if we changed campaigns
    if campaign:
        brand_voice = db_project.brand_voice or {}
        if campaign.model:
            brand_voice["model"] = campaign.model
        if category:
            brand_voice["category"] = category.name
        db_project.brand_voice = brand_voice

    db.commit()
    db.refresh(db_project)
    db_project.category_name = db_project.category.name if db_project.category else None
    db_project.campaign_name = db_project.campaign.name if db_project.campaign else None

    # Add parent project name if it exists
    if db_project.parent_project_id:
        parent = db.query(Project).filter(Project.id == db_project.parent_project_id).first()
        db_project.parent_project_name = parent.name if parent else None
    else:
        db_project.parent_project_name = None

    return db_project


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Delete a project."""
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise not_found("Project", project_id)

    db.delete(db_project)
    db.commit()
    return {"message": "Project deleted successfully"}


@router.post("/{project_id}/archive")
async def archive_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Archive a project."""
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise not_found("Project", project_id)

    db_project.is_archived = True
    db.commit()
    return {"message": "Project archived successfully"}


@router.post("/{project_id}/unarchive")
async def unarchive_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Unarchive a project."""
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise not_found("Project", project_id)

    db_project.is_archived = False
    db.commit()
    return {"message": "Project unarchived successfully"}
