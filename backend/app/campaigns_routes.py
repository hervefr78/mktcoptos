from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from .database import get_db
from .models import Category, Project, Campaign
from .projects_routes import get_current_user_id, get_organization_id
from .errors import not_found


router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class CampaignBase(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    category: Optional[str] = Field(None, max_length=255)
    category_id: Optional[int] = Field(None, gt=0)
    model: Optional[str] = Field(None, max_length=255)
    campaign_type: Optional[str] = Field(None, pattern="^(standalone|integrated)$")
    default_language: Optional[str] = Field(None, max_length=50)


class CampaignCreate(CampaignBase):
    name: str = Field(..., min_length=1, max_length=255)
    campaign_type: str = Field(default="standalone", pattern="^(standalone|integrated)$")


class CampaignUpdate(CampaignBase):
    pass


class SubProjectInfo(BaseModel):
    id: int
    name: str
    content_type: Optional[str]
    inherit_tone: bool
    status: Optional[str] = None  # Will be populated from pipeline execution

    class Config:
        from_attributes = True


class CampaignProject(BaseModel):
    id: int
    name: str
    description: Optional[str]
    language: Optional[str]
    content_type: Optional[str]
    is_main_project: bool
    parent_project_id: Optional[int]
    sub_projects: List[SubProjectInfo] = []
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class CampaignResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    category_id: Optional[int]
    model: Optional[str]
    campaign_type: str
    default_language: Optional[str]
    project_count: int
    main_project_count: int = 0
    projects: List[CampaignProject]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


def _resolve_category(payload: CampaignBase, db: Session, organization_id: int) -> Optional[Category]:
    if payload.category_id is not None:
        category = (
            db.query(Category)
            .filter(Category.id == payload.category_id, Category.organization_id == organization_id)
            .first()
        )
        if not category:
            raise HTTPException(status_code=400, detail="Invalid category")
        return category
    if payload.category:
        normalized = payload.category.strip()
        if normalized:
            category = (
                db.query(Category)
                .filter(
                    Category.organization_id == organization_id,
                    func.lower(Category.name) == normalized.lower(),
                )
                .first()
            )
            if not category:
                raise HTTPException(status_code=400, detail="Invalid category")
            return category
    return None


def _build_campaign_response(campaign: Campaign) -> CampaignResponse:
    category_name = campaign.category.name if campaign.category else None

    # Build project hierarchy
    all_projects = sorted(campaign.projects, key=lambda p: p.created_at or datetime.utcnow(), reverse=True)

    # Create a map of projects for easy lookup
    project_map = {p.id: p for p in all_projects}

    # Build the project list with sub-projects
    projects_list = []
    main_project_count = 0

    for project in all_projects:
        # Skip sub-projects, they'll be added under their parent
        if project.parent_project_id:
            continue

        if project.is_main_project:
            main_project_count += 1

        # Get sub-projects for this project
        sub_projects = [
            SubProjectInfo(
                id=sub.id,
                name=sub.name,
                content_type=sub.content_type,
                inherit_tone=sub.inherit_tone,
                status=None,  # Could be populated from pipeline_executions if needed
            )
            for sub in all_projects
            if sub.parent_project_id == project.id
        ]

        projects_list.append(
            CampaignProject(
                id=project.id,
                name=project.name,
                description=project.description,
                language=project.language,
                content_type=project.content_type,
                is_main_project=project.is_main_project,
                parent_project_id=project.parent_project_id,
                sub_projects=sub_projects,
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
        )

    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        category=category_name,
        category_id=campaign.category_id,
        model=campaign.model,
        campaign_type=campaign.campaign_type,
        default_language=campaign.default_language,
        project_count=len(all_projects),
        main_project_count=main_project_count,
        projects=projects_list,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    request: Request,
    db: Session = Depends(get_db),
):
    organization_id = get_organization_id(request)
    campaigns = (
        db.query(Campaign)
        .options(joinedload(Campaign.projects), joinedload(Campaign.category))
        .filter(Campaign.organization_id == organization_id)
        .order_by(Campaign.created_at.desc())
        .all()
    )
    return [_build_campaign_response(campaign) for campaign in campaigns]


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    organization_id = get_organization_id(request)
    campaign = (
        db.query(Campaign)
        .options(joinedload(Campaign.projects), joinedload(Campaign.category))
        .filter(Campaign.id == campaign_id, Campaign.organization_id == organization_id)
        .first()
    )
    if not campaign:
        raise not_found("Campaign", campaign_id)

    return _build_campaign_response(campaign)


@router.post("", response_model=CampaignResponse)
async def create_campaign(
    payload: CampaignCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    organization_id = get_organization_id(request)
    _ = get_current_user_id(request)  # reserved for auditing

    category = _resolve_category(payload, db, organization_id)

    campaign = Campaign(
        organization_id=organization_id,
        category_id=category.id if category else None,
        name=payload.name,
        description=payload.description,
        model=payload.model,
        campaign_type=payload.campaign_type,
        default_language=payload.default_language or "auto",
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return _build_campaign_response(campaign)


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    organization_id = get_organization_id(request)
    campaign = (
        db.query(Campaign)
        .options(joinedload(Campaign.projects), joinedload(Campaign.category))
        .filter(Campaign.id == campaign_id, Campaign.organization_id == organization_id)
        .first()
    )
    if not campaign:
        raise not_found("Campaign", campaign_id)

    update_data = payload.dict(exclude_unset=True)
    for field in ["name", "description", "model", "campaign_type", "default_language"]:
        if field in update_data:
            setattr(campaign, field, update_data[field])

    category = _resolve_category(payload, db, organization_id)
    if category:
        campaign.category_id = category.id

    db.commit()
    db.refresh(campaign)

    return _build_campaign_response(campaign)


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    organization_id = get_organization_id(request)
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.organization_id == organization_id)
        .first()
    )
    if not campaign:
        raise not_found("Campaign", campaign_id)

    # Check if campaign has projects
    project_count = db.query(Project).filter(Project.campaign_id == campaign_id).count()
    if project_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete campaign with {project_count} project(s). Delete projects first."
        )

    db.delete(campaign)
    db.commit()

    return {"message": "Campaign deleted successfully", "id": campaign_id}
