"""
Settings Service - Database-backed user and organization settings
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from .database import get_db
from .models import User, Organization, UserSettings, OrganizationSettings, SettingsHistory
import json


class SettingsResponse(BaseModel):
    """Combined settings response (user + organization defaults)"""
    # LLM Provider Settings
    llmProvider: str = "ollama"
    llmModel: Optional[str] = None
    openaiApiKey: Optional[str] = None
    openaiOrganizationId: Optional[str] = None
    ollamaBaseUrl: str = "http://localhost:11434"

    # Web Search Settings
    braveSearchApiKey: Optional[str] = None

    # Image Generation Settings
    imageProvider: str = "openai"
    openaiImageModel: str = "dall-e-3"
    openaiImageQuality: str = "standard"
    openaiImageSize: str = "1024x1024"
    openaiImageStyle: str = "natural"
    sdBaseUrl: str = "http://localhost:7860"
    useHybridImages: bool = False

    # ComfyUI Settings
    comfyuiBaseUrl: str = "http://localhost:8188"
    sdxlModel: str = "sd_xl_turbo_1.0_fp16.safetensors"
    sdxlSteps: int = 6
    sdxlCfgScale: float = 1.0
    sdxlSampler: str = "euler_ancestral"

    # Hybrid Image Strategy
    useGptImageForPosts: bool = True
    useComfyuiForBlogs: bool = True

    # Prompt Contexts
    marketingPromptContext: Optional[str] = None
    blogPromptContext: Optional[str] = None
    socialMediaPromptContext: Optional[str] = None
    imagePromptContext: Optional[str] = None

    # UI Preferences
    theme: str = "light"
    sidebarWidth: int = 240
    timezone: str = "UTC"
    notificationEmail: Optional[str] = None


class SettingsUpdate(BaseModel):
    """Partial settings update"""
    llmProvider: Optional[str] = None
    llmModel: Optional[str] = None
    openaiApiKey: Optional[str] = None
    openaiOrganizationId: Optional[str] = None
    ollamaBaseUrl: Optional[str] = None
    braveSearchApiKey: Optional[str] = None  # Web search API key
    imageProvider: Optional[str] = None
    openaiImageModel: Optional[str] = None
    openaiImageQuality: Optional[str] = None
    openaiImageSize: Optional[str] = None
    openaiImageStyle: Optional[str] = None
    sdBaseUrl: Optional[str] = None
    useHybridImages: Optional[bool] = None
    comfyuiBaseUrl: Optional[str] = None
    sdxlModel: Optional[str] = None
    sdxlSteps: Optional[int] = None
    sdxlCfgScale: Optional[float] = None
    sdxlSampler: Optional[str] = None
    useGptImageForPosts: Optional[bool] = None
    useComfyuiForBlogs: Optional[bool] = None
    marketingPromptContext: Optional[str] = None
    blogPromptContext: Optional[str] = None
    socialMediaPromptContext: Optional[str] = None
    imagePromptContext: Optional[str] = None
    theme: Optional[str] = None
    sidebarWidth: Optional[int] = None
    timezone: Optional[str] = None
    notificationEmail: Optional[str] = None


class SettingsService:
    """Service for managing user and organization settings"""

    @staticmethod
    def get_user_settings(
        user_id: int,
        db: Session,
        create_if_missing: bool = True
    ) -> UserSettings:
        """
        Get user settings, creating default if missing

        Args:
            user_id: User ID
            db: Database session
            create_if_missing: Create default settings if none exist

        Returns:
            UserSettings object
        """
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()

        if not settings and create_if_missing:
            # Create default settings
            settings = UserSettings(user_id=user_id)
            db.add(settings)
            db.commit()
            db.refresh(settings)

        return settings

    @staticmethod
    def get_org_settings(
        org_id: int,
        db: Session,
        create_if_missing: bool = True
    ) -> Optional[OrganizationSettings]:
        """
        Get organization settings

        Args:
            org_id: Organization ID
            db: Database session
            create_if_missing: Create default settings if none exist

        Returns:
            OrganizationSettings object or None
        """
        settings = db.query(OrganizationSettings).filter(
            OrganizationSettings.organization_id == org_id
        ).first()

        if not settings and create_if_missing:
            settings = OrganizationSettings(organization_id=org_id)
            db.add(settings)
            db.commit()
            db.refresh(settings)

        return settings

    @staticmethod
    def get_combined_settings(
        user_id: int,
        db: Session
    ) -> SettingsResponse:
        """
        Get combined settings (user overrides organization defaults)

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Combined settings as SettingsResponse
        """
        user_settings = SettingsService.get_user_settings(user_id, db)

        # Convert to dict for easy access
        response = SettingsResponse(
            llmProvider=user_settings.llm_provider or "ollama",
            llmModel=user_settings.llm_model,
            openaiApiKey=user_settings.openai_api_key,
            openaiOrganizationId=user_settings.openai_organization_id,
            ollamaBaseUrl=user_settings.ollama_base_url or "http://localhost:11434",

            braveSearchApiKey=user_settings.brave_search_api_key,

            imageProvider=user_settings.image_provider or "openai",
            openaiImageModel=user_settings.openai_image_model or "dall-e-3",
            openaiImageQuality=user_settings.openai_image_quality or "standard",
            openaiImageSize=user_settings.openai_image_size or "1024x1024",
            openaiImageStyle=user_settings.openai_image_style or "natural",
            sdBaseUrl=user_settings.sd_base_url or "http://localhost:7860",
            useHybridImages=user_settings.use_hybrid_images or False,

            comfyuiBaseUrl=user_settings.comfyui_base_url or "http://localhost:8188",
            sdxlModel=user_settings.sdxl_model or "sd_xl_turbo_1.0_fp16.safetensors",
            sdxlSteps=user_settings.sdxl_steps or 6,
            sdxlCfgScale=float(user_settings.sdxl_cfg_scale) if user_settings.sdxl_cfg_scale is not None else 1.0,
            sdxlSampler=user_settings.sdxl_sampler or "euler_ancestral",

            useGptImageForPosts=user_settings.use_gpt_image_for_posts if user_settings.use_gpt_image_for_posts is not None else True,
            useComfyuiForBlogs=user_settings.use_comfyui_for_blogs if user_settings.use_comfyui_for_blogs is not None else True,

            marketingPromptContext=user_settings.marketing_prompt_context,
            blogPromptContext=user_settings.blog_prompt_context,
            socialMediaPromptContext=user_settings.social_media_prompt_context,
            imagePromptContext=user_settings.image_prompt_context,

            theme=user_settings.theme or "light",
            sidebarWidth=user_settings.sidebar_width or 240,
            timezone=user_settings.timezone or "UTC",
            notificationEmail=user_settings.notification_email,
        )

        return response

    @staticmethod
    def update_user_settings(
        user_id: int,
        updates: SettingsUpdate,
        db: Session,
        request: Optional[Request] = None
    ) -> UserSettings:
        """
        Update user settings and log changes

        Args:
            user_id: User ID
            updates: Settings updates
            db: Database session
            request: Optional FastAPI request for audit trail

        Returns:
            Updated UserSettings
        """
        settings = SettingsService.get_user_settings(user_id, db)

        # Track changes for audit log
        changes = []

        # Update fields
        update_data = updates.model_dump(exclude_unset=True)
        for field, new_value in update_data.items():
            # Convert camelCase to snake_case
            db_field = ''.join(['_' + c.lower() if c.isupper() else c for c in field]).lstrip('_')

            if hasattr(settings, db_field):
                old_value = getattr(settings, db_field)

                # Only update if changed
                if old_value != new_value:
                    changes.append({
                        'field': db_field,
                        'old_value': str(old_value) if old_value is not None else None,
                        'new_value': str(new_value) if new_value is not None else None
                    })
                    setattr(settings, db_field, new_value)

        # Save changes
        if changes:
            db.commit()
            db.refresh(settings)

            # Log to history
            ip_address = None
            user_agent = None
            if request:
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get('user-agent')

            for change in changes:
                history = SettingsHistory(
                    settings_type='user',
                    settings_id=settings.id,
                    changed_by_user_id=user_id,
                    field_name=change['field'],
                    old_value=change['old_value'],
                    new_value=change['new_value'],
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                db.add(history)

            db.commit()

        return settings

    @staticmethod
    def get_settings_history(
        settings_type: str,
        settings_id: int,
        db: Session,
        limit: int = 50
    ) -> list:
        """
        Get settings change history

        Args:
            settings_type: "user" or "organization"
            settings_id: Settings ID
            db: Database session
            limit: Maximum number of records

        Returns:
            List of SettingsHistory records
        """
        history = db.query(SettingsHistory).filter(
            SettingsHistory.settings_type == settings_type,
            SettingsHistory.settings_id == settings_id
        ).order_by(SettingsHistory.changed_at.desc()).limit(limit).all()

        return history

    @staticmethod
    def migrate_from_json(json_file_path: str, user_id: int, db: Session) -> UserSettings:
        """
        Migrate settings from JSON file to database

        Args:
            json_file_path: Path to JSON settings file
            user_id: User ID to associate settings with
            db: Database session

        Returns:
            Created UserSettings
        """
        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)

            # Create settings update from JSON
            updates = SettingsUpdate(**data)

            # Update or create settings
            return SettingsService.update_user_settings(user_id, updates, db)
        except Exception as e:
            raise Exception(f"Failed to migrate settings from JSON: {str(e)}")
