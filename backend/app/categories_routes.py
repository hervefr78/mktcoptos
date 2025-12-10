from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import get_db
from .models import Category, Project
from .projects_routes import get_organization_id
from .settings_service import SettingsService

router = APIRouter(prefix="/api/categories", tags=["categories"])


class CategoryOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class CategoriesResponse(BaseModel):
    categories: List[CategoryOut]


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


def _seed_categories_from_settings(organization_id: int, db: Session) -> List[Category]:
    settings = SettingsService.get_org_settings(organization_id, db)
    brand_voice = settings.brand_voice or {}
    categories_from_settings = brand_voice.get("categories") or []
    normalized_existing = {
        c.name.lower(): c.id for c in db.query(Category).filter(Category.organization_id == organization_id)
    }

    created = False
    for name in categories_from_settings:
        if not isinstance(name, str):
            continue
        cleaned = name.strip()
        if not cleaned:
            continue
        if cleaned.lower() in normalized_existing:
            continue
        db.add(Category(name=cleaned, organization_id=organization_id))
        created = True

    if created:
        db.commit()

    return db.query(Category).filter(Category.organization_id == organization_id).order_by(Category.name.asc()).all()


def _get_categories_for_org(organization_id: int, db: Session) -> List[Category]:
    categories = (
        db.query(Category)
        .filter(Category.organization_id == organization_id)
        .order_by(Category.name.asc())
        .all()
    )
    if categories:
        return categories
    return _seed_categories_from_settings(organization_id, db)


@router.get("", response_model=CategoriesResponse)
async def list_categories(
    request: Request,
    db: Session = Depends(get_db),
):
    organization_id = get_organization_id(request)
    categories = _get_categories_for_org(organization_id, db)
    return CategoriesResponse(categories=categories)


@router.post("", response_model=CategoriesResponse)
async def create_category(
    payload: CategoryCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    organization_id = get_organization_id(request)

    new_name = payload.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Category name cannot be empty")

    existing = (
        db.query(Category)
        .filter(
            Category.organization_id == organization_id,
            func.lower(Category.name) == new_name.lower(),
        )
        .first()
    )
    if existing:
        categories = _get_categories_for_org(organization_id, db)
        return CategoriesResponse(categories=categories)

    category = Category(name=new_name, organization_id=organization_id)
    db.add(category)
    db.commit()
    db.refresh(category)

    categories = _get_categories_for_org(organization_id, db)
    return CategoriesResponse(categories=categories)


@router.delete("/{category_id}", response_model=CategoriesResponse)
async def delete_category(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    organization_id = get_organization_id(request)
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.organization_id == organization_id)
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    db.query(Project).filter(Project.category_id == category.id).update({Project.category_id: None})
    db.delete(category)
    db.commit()

    categories = _get_categories_for_org(organization_id, db)
    return CategoriesResponse(categories=categories)
