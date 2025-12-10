"""Settings management for Marketing Assistant"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from config import settings as app_config

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Settings storage path
SETTINGS_FILE = Path(__file__).parent.parent / "data" / "settings.json"


class SettingsModel(BaseModel):
    """Application settings model"""
    # LLM Provider Settings
    llmProvider: str = "ollama"  # "openai" or "ollama"
    llmModel: Optional[str] = None
    openaiApiKey: Optional[str] = None
    openaiOrganizationId: Optional[str] = None
    ollamaBaseUrl: str = "http://localhost:11434"

    # Image Generation Settings
    imageProvider: str = "openai"  # "openai", "stable-diffusion", or "hybrid"
    openaiImageModel: str = "dall-e-3"
    openaiImageQuality: str = "standard"  # "standard" or "hd"
    openaiImageSize: str = "1024x1024"
    openaiImageStyle: str = "natural"  # "natural" or "vivid"
    sdBaseUrl: Optional[str] = "http://localhost:7860"
    useHybridImages: bool = False  # Use OpenAI for quick, SD for high quality

    # Prompt Contexts
    marketingPromptContext: Optional[str] = None
    blogPromptContext: Optional[str] = None
    socialMediaPromptContext: Optional[str] = None
    imagePromptContext: Optional[str] = None

    # General Settings
    timezone: str = "UTC"
    notificationEmail: Optional[str] = None


class SettingsUpdate(BaseModel):
    """Partial settings update"""
    llmProvider: Optional[str] = None
    llmModel: Optional[str] = None
    openaiApiKey: Optional[str] = None
    openaiOrganizationId: Optional[str] = None
    ollamaBaseUrl: Optional[str] = None
    imageProvider: Optional[str] = None
    openaiImageModel: Optional[str] = None
    openaiImageQuality: Optional[str] = None
    openaiImageSize: Optional[str] = None
    openaiImageStyle: Optional[str] = None
    sdBaseUrl: Optional[str] = None
    useHybridImages: Optional[bool] = None
    marketingPromptContext: Optional[str] = None
    blogPromptContext: Optional[str] = None
    socialMediaPromptContext: Optional[str] = None
    imagePromptContext: Optional[str] = None
    timezone: Optional[str] = None
    notificationEmail: Optional[str] = None


def ensure_settings_file():
    """Ensure settings file and directory exist"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        # Create default settings
        default_settings = SettingsModel()
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(default_settings.model_dump(), f, indent=2)


def load_settings() -> SettingsModel:
    """Load settings from file"""
    ensure_settings_file()
    try:
        with open(SETTINGS_FILE, 'r') as f:
            data = json.load(f)
        return SettingsModel(**data)
    except Exception as e:
        print(f"Error loading settings: {e}")
        return SettingsModel()


def save_settings(settings: SettingsModel):
    """Save settings to file"""
    ensure_settings_file()
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings.model_dump(), f, indent=2)


@router.get("")
async def get_settings() -> SettingsModel:
    """Get current settings"""
    return load_settings()


@router.put("")
async def update_settings(update: SettingsUpdate) -> SettingsModel:
    """Update settings"""
    current = load_settings()

    # Update only provided fields
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(current, key):
            setattr(current, key, value)

    save_settings(current)
    return current


@router.get("/ollama/models")
async def list_ollama_models():
    """List available Ollama models"""
    settings = load_settings()
    base_url = settings.ollamaBaseUrl or "http://localhost:11434"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/api/tags", timeout=5.0)
            response.raise_for_status()
            data = response.json()
            return {"models": data.get("models", [])}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot connect to Ollama: {str(e)}")


@router.post("/ollama/test")
async def test_ollama_connection(base_url: Optional[str] = None):
    """Test Ollama connection"""
    settings = load_settings()
    test_url = base_url or settings.ollamaBaseUrl or "http://localhost:11434"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{test_url}/api/tags", timeout=5.0)
            response.raise_for_status()
            return {"connected": True, "url": test_url}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot connect to Ollama: {str(e)}")


@router.post("/openai/test")
async def test_openai_connection(api_key: Optional[str] = None):
    """Test OpenAI API connection"""
    settings = load_settings()
    test_key = api_key or settings.openaiApiKey

    if not test_key:
        raise HTTPException(status_code=400, detail="No API key provided")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {test_key}"},
                timeout=10.0
            )
            response.raise_for_status()
            return {"connected": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot connect to OpenAI: {str(e)}")


@router.get("/openai/models")
async def list_openai_models():
    """List available OpenAI models with pricing info"""
    # Hardcoded model list with pricing (as of 2024)
    models = [
        {
            "id": "gpt-4o",
            "name": "GPT-4o",
            "description": "Most capable model, great for complex tasks",
            "inputPrice": 2.50,
            "outputPrice": 10.00,
            "contextWindow": 128000,
            "bestFor": "Complex reasoning, analysis"
        },
        {
            "id": "gpt-4o-mini",
            "name": "GPT-4o Mini",
            "description": "Affordable and intelligent small model",
            "inputPrice": 0.15,
            "outputPrice": 0.60,
            "contextWindow": 128000,
            "bestFor": "Fast, cost-effective tasks"
        },
        {
            "id": "gpt-4-turbo",
            "name": "GPT-4 Turbo",
            "description": "Previous generation flagship model",
            "inputPrice": 10.00,
            "outputPrice": 30.00,
            "contextWindow": 128000,
            "bestFor": "Complex tasks (legacy)"
        },
        {
            "id": "gpt-3.5-turbo",
            "name": "GPT-3.5 Turbo",
            "description": "Fast and inexpensive model for simple tasks",
            "inputPrice": 0.50,
            "outputPrice": 1.50,
            "contextWindow": 16385,
            "bestFor": "Simple, fast completions"
        }
    ]
    return models


@router.post("/sd/test")
async def test_sd_connection(base_url: Optional[str] = None):
    """Test Stable Diffusion connection"""
    settings = load_settings()
    test_url = base_url or settings.sdBaseUrl or "http://localhost:7860"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{test_url}/sdapi/v1/sd-models", timeout=5.0)
            response.raise_for_status()
            return {"connected": True, "url": test_url}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot connect to Stable Diffusion: {str(e)}")
