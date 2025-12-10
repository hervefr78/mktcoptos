"""Settings API routes - Database-backed"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import httpx
import asyncio

from .database import get_db
from .settings_service import SettingsService, SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


# Temporary: Get current user (in production, use proper auth)
def get_current_user_id(request: Request) -> int:
    """
    Get current user ID from request

    TODO: Replace with proper authentication middleware
    For now, returns user ID 1 (admin) or from header
    """
    user_id = request.headers.get("X-User-ID")
    if user_id:
        try:
            return int(user_id)
        except:
            pass

    # Default to user 1 (admin) for development
    return 1


@router.get("", response_model=SettingsResponse)
async def get_settings(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get current user's settings

    Returns combined settings (user preferences + organization defaults)
    """
    try:
        settings = SettingsService.get_combined_settings(user_id, db)
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load settings: {str(e)}")


@router.put("", response_model=SettingsResponse)
async def update_settings(
    updates: SettingsUpdate,
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Update current user's settings

    All changes are logged to settings_history for audit trail
    """
    try:
        SettingsService.update_user_settings(user_id, updates, db, request)
        # Return updated settings
        return SettingsService.get_combined_settings(user_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


@router.get("/history")
async def get_settings_history(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """
    Get settings change history for current user

    Shows audit trail of all settings changes
    """
    try:
        user_settings = SettingsService.get_user_settings(user_id, db, create_if_missing=False)
        if not user_settings:
            return []

        history = SettingsService.get_settings_history(
            settings_type='user',
            settings_id=user_settings.id,
            db=db,
            limit=limit
        )

        return [
            {
                "field": h.field_name,
                "oldValue": h.old_value,
                "newValue": h.new_value,
                "changedAt": h.changed_at.isoformat(),
                "ipAddress": h.ip_address,
            }
            for h in history
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load history: {str(e)}")


@router.get("/ollama/models")
async def list_ollama_models(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """List available Ollama models from user's configured Ollama instance"""
    import os
    settings = SettingsService.get_combined_settings(user_id, db)
    # Priority: environment variable > database settings > default
    base_url = os.getenv('OLLAMA_HOST') or settings.ollamaBaseUrl or "http://localhost:11434"
    if base_url in ["http://ollama:11434", "http://ollama:11434/"]:
        base_url = os.getenv('OLLAMA_HOST', "http://host.docker.internal:11434")

    # Retry logic for Ollama startup
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/api/tags", timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return {"models": data.get("models", [])}
        except httpx.ConnectError as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to Ollama at {base_url}. Make sure Ollama is running. Error: {str(e)}"
            )
        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=503,
                detail=f"Ollama connection timeout. The service might be starting up. Please wait a moment and try again."
            )
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Cannot connect to Ollama: {str(e)}")

    raise HTTPException(status_code=503, detail="Failed to connect to Ollama after multiple retries")


@router.post("/ollama/test")
async def test_ollama_connection(
    base_url: str = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Test Ollama connection"""
    import os
    settings = SettingsService.get_combined_settings(user_id, db)
    # Priority: provided URL > environment variable > database settings > default
    test_url = base_url or os.getenv('OLLAMA_HOST') or settings.ollamaBaseUrl or "http://localhost:11434"
    if test_url in ["http://ollama:11434", "http://ollama:11434/"]:
        test_url = os.getenv('OLLAMA_HOST', "http://host.docker.internal:11434")

    # Retry logic for Ollama startup
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{test_url}/api/tags", timeout=10.0)
                response.raise_for_status()
                return {"connected": True, "url": test_url}
        except httpx.ConnectError as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to Ollama at {test_url}. Make sure Ollama is running."
            )
        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            raise HTTPException(
                status_code=503,
                detail=f"Ollama connection timeout. The service might be starting up. Please wait and try again."
            )
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Cannot connect to Ollama: {str(e)}")

    raise HTTPException(status_code=503, detail="Failed to connect to Ollama after multiple retries")


@router.post("/openai/test")
async def test_openai_connection(
    api_key: str = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Test OpenAI API connection"""
    settings = SettingsService.get_combined_settings(user_id, db)
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


@router.get("/openai/models/available")
async def get_available_openai_models(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Query OpenAI API to check which models are actually accessible with your API key"""
    try:
        settings = SettingsService.get_combined_settings(user_id, db)
        api_key = settings.openaiApiKey or os.getenv('OPENAI_API_KEY')

        if not api_key:
            raise HTTPException(status_code=400, detail="OpenAI API key not configured")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0
            )

            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"OpenAI API error: {response.text}")

            models_data = response.json()
            # Filter for chat/completion models only
            chat_models = [
                m for m in models_data.get('data', [])
                if 'gpt' in m['id'] or 'o1' in m['id'] or 'o3' in m['id'] or 'o4' in m['id']
            ]

            return {
                "available": True,
                "models": sorted([m['id'] for m in chat_models]),
                "count": len(chat_models)
            }
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="OpenAI API timeout")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot query OpenAI models: {str(e)}")


@router.get("/openai/models")
async def list_openai_models():
    """List OpenAI models according to documentation

    Note: GPT-5 and GPT-4.1 models may require beta access or special organization permissions.
    If you get 400 errors, your API key may not have access yet. Use /openai/models/available
    to check which models are accessible with your current API key.
    """
    models = [
        # GPT-5 series (May require beta access)
        {
            "id": "gpt-5",
            "name": "GPT-5",
            "description": "Next generation flagship model (400k context)",
            "inputPrice": 1.25,
            "outputPrice": 10.00,
            "contextWindow": 400000,
            "bestFor": "Complex tasks, creative writing, analysis",
            "requiresBeta": True
        },
        {
            "id": "gpt-5-pro",
            "name": "GPT-5 Pro",
            "description": "Most powerful GPT-5 with premium reasoning (400k context)",
            "inputPrice": 15.00,
            "outputPrice": 120.00,
            "contextWindow": 400000,
            "bestFor": "Enterprise, complex analysis, maximum capability",
            "requiresBeta": True
        },
        {
            "id": "gpt-5-mini",
            "name": "GPT-5 Mini",
            "description": "Fast and efficient GPT-5 variant (400k context)",
            "inputPrice": 0.25,
            "outputPrice": 2.00,
            "contextWindow": 400000,
            "bestFor": "Balanced performance and cost",
            "requiresBeta": True
        },
        {
            "id": "gpt-5-nano",
            "name": "GPT-5 Nano",
            "description": "Ultra-fast, lowest cost GPT-5 model (400k context)",
            "inputPrice": 0.05,
            "outputPrice": 0.40,
            "contextWindow": 400000,
            "bestFor": "High volume, simple tasks",
            "requiresBeta": True
        },
        # GPT-4.1 series (May require beta access)
        {
            "id": "gpt-4.1",
            "name": "GPT-4.1",
            "description": "Latest GPT-4 series with 1M context window",
            "inputPrice": 2.00,
            "outputPrice": 8.00,
            "contextWindow": 1000000,
            "bestFor": "Long context, complex analysis",
            "requiresBeta": True
        },
        {
            "id": "gpt-4.1-mini",
            "name": "GPT-4.1 Mini",
            "description": "Fast GPT-4.1 variant with 1M context",
            "inputPrice": 0.40,
            "outputPrice": 1.60,
            "contextWindow": 1000000,
            "bestFor": "Long context, fast responses",
            "requiresBeta": True
        },
        {
            "id": "gpt-4.1-nano",
            "name": "GPT-4.1 Nano",
            "description": "Ultra-fast GPT-4.1 with 1M context",
            "inputPrice": 0.10,
            "outputPrice": 0.40,
            "contextWindow": 1000000,
            "bestFor": "Simple tasks, high volume",
            "requiresBeta": True
        },
        # GPT-4o series (Generally available)
        {
            "id": "gpt-4o",
            "name": "GPT-4o",
            "description": "High-intelligence flagship model (128k context)",
            "inputPrice": 2.50,
            "outputPrice": 10.00,
            "contextWindow": 128000,
            "bestFor": "Complex reasoning, analysis, creative writing",
            "requiresBeta": False
        },
        {
            "id": "gpt-4o-mini",
            "name": "GPT-4o Mini",
            "description": "Affordable and intelligent model (128k context)",
            "inputPrice": 0.15,
            "outputPrice": 0.60,
            "contextWindow": 128000,
            "bestFor": "Fast, cost-effective tasks",
            "requiresBeta": False
        },
        # GPT-4 series
        {
            "id": "gpt-4-turbo",
            "name": "GPT-4 Turbo",
            "description": "Previous generation flagship (128k context)",
            "inputPrice": 10.00,
            "outputPrice": 30.00,
            "contextWindow": 128000,
            "bestFor": "Complex tasks",
            "requiresBeta": False
        },
        {
            "id": "gpt-4",
            "name": "GPT-4",
            "description": "Original GPT-4 model",
            "inputPrice": 30.00,
            "outputPrice": 60.00,
            "contextWindow": 8192,
            "bestFor": "High-quality complex tasks",
            "requiresBeta": False
        },
        # GPT-3.5 series
        {
            "id": "gpt-3.5-turbo",
            "name": "GPT-3.5 Turbo",
            "description": "Fast and inexpensive model",
            "inputPrice": 0.50,
            "outputPrice": 1.50,
            "contextWindow": 16385,
            "bestFor": "Simple, fast completions",
            "requiresBeta": False
        }
    ]
    return models


@router.post("/sd/test")
async def test_sd_connection(
    base_url: str = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Test Stable Diffusion connection"""
    settings = SettingsService.get_combined_settings(user_id, db)
    test_url = base_url or settings.sdBaseUrl or "http://localhost:7860"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{test_url}/sdapi/v1/sd-models", timeout=5.0)
            response.raise_for_status()
            return {"connected": True, "url": test_url}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot connect to Stable Diffusion: {str(e)}")


@router.post("/migrate-from-json")
async def migrate_from_json(
    json_file_path: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Migrate settings from JSON file to database

    This endpoint is for one-time migration from the old JSON-based system
    """
    try:
        settings = SettingsService.migrate_from_json(json_file_path, user_id, db)
        return {
            "success": True,
            "message": "Settings migrated successfully",
            "userId": user_id,
            "settingsId": settings.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/services")
async def check_services_health(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Check health status of all AI services (Ollama, OpenAI, ComfyUI)
    Returns connection status and configuration info
    """
    import os

    settings = SettingsService.get_combined_settings(user_id, db)

    results = {
        "llmProvider": settings.llmProvider,
        "imageProvider": settings.imageProvider,
        "services": {}
    }

    # Check Ollama
    # Priority: environment variable > database settings > default
    # Use host.docker.internal when running in Docker to reach host services
    ollama_url = os.getenv('OLLAMA_HOST') or settings.ollamaBaseUrl or "http://localhost:11434"
    # If the stored URL is the old Docker service name, use the env var or host.docker.internal
    if ollama_url in ["http://ollama:11434", "http://ollama:11434/"]:
        ollama_url = os.getenv('OLLAMA_HOST', "http://host.docker.internal:11434")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                results["services"]["ollama"] = {
                    "status": "connected",
                    "url": ollama_url,
                    "modelsCount": len(models),
                    "models": [m.get("name", "") for m in models[:5]],  # First 5 models
                    "selectedModel": settings.llmModel if settings.llmProvider == "ollama" else None
                }
            else:
                results["services"]["ollama"] = {
                    "status": "error",
                    "url": ollama_url,
                    "error": f"HTTP {response.status_code}"
                }
    except Exception as e:
        results["services"]["ollama"] = {
            "status": "disconnected",
            "url": ollama_url,
            "error": str(e)
        }

    # Check OpenAI
    api_key = settings.openaiApiKey or os.getenv('OPENAI_API_KEY')
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if response.status_code == 200:
                    results["services"]["openai"] = {
                        "status": "connected",
                        "configured": True,
                        "selectedModel": settings.llmModel if settings.llmProvider == "openai" else None,
                        "imageModel": settings.openaiImageModel
                    }
                else:
                    results["services"]["openai"] = {
                        "status": "error",
                        "configured": True,
                        "error": f"HTTP {response.status_code} - Invalid API key"
                    }
        except Exception as e:
            results["services"]["openai"] = {
                "status": "error",
                "configured": True,
                "error": str(e)
            }
    else:
        results["services"]["openai"] = {
            "status": "not_configured",
            "configured": False,
            "error": "API key not set"
        }

    # Check ComfyUI
    # Priority: environment variable > database settings > default
    # Use host.docker.internal when running in Docker to reach host services
    comfyui_url = os.getenv('COMFYUI_BASE_URL') or settings.comfyuiBaseUrl or "http://localhost:8188"
    if comfyui_url in ["http://comfyui:8188", "http://comfyui:8188/"]:
        comfyui_url = os.getenv('COMFYUI_BASE_URL', "http://host.docker.internal:8188")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{comfyui_url}/system_stats")
            if response.status_code == 200:
                results["services"]["comfyui"] = {
                    "status": "connected",
                    "url": comfyui_url,
                    "selectedModel": settings.sdxlModel
                }
            else:
                results["services"]["comfyui"] = {
                    "status": "error",
                    "url": comfyui_url,
                    "error": f"HTTP {response.status_code}"
                }
    except Exception as e:
        results["services"]["comfyui"] = {
            "status": "disconnected",
            "url": comfyui_url,
            "error": str(e)
        }

    return results


@router.get("/health/infrastructure")
async def check_infrastructure_health():
    """
    Check health status of infrastructure components via HTTP/TCP checks
    This works from inside the container without needing Docker CLI access
    """
    import socket

    services = [
        {
            "name": "postgres",
            "host": "postgres",
            "port": 5432,
            "type": "database",
            "check": "tcp"
        },
        {
            "name": "redis",
            "host": "redis",
            "port": 6379,
            "type": "cache",
            "check": "tcp"
        },
        {
            "name": "backend",
            "host": "localhost",
            "port": 8000,
            "type": "api",
            "check": "http",
            "path": "/health"
        },
        {
            "name": "frontend",
            "host": "frontend",
            "port": 3000,
            "type": "web",
            "check": "tcp"
        },
        {
            "name": "ollama",
            "host": "host.docker.internal",  # Ollama runs on host, accessed via host.docker.internal from Docker
            "port": 11434,
            "type": "llm",
            "check": "http",
            "path": "/api/tags"
        },
        {
            "name": "chromadb",
            "host": "chromadb",
            "port": 8000,
            "type": "vectordb",
            "check": "http",
            "path": "/api/v1/heartbeat"
        },
    ]

    results = {"services": []}

    for service in services:
        service_info = {
            "name": service["name"],
            "host": service["host"],
            "port": service["port"],
            "type": service["type"],
            "status": "unknown"
        }

        try:
            if service["check"] == "tcp":
                # TCP connection check
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((service["host"], service["port"]))
                sock.close()

                if result == 0:
                    service_info["status"] = "healthy"
                else:
                    service_info["status"] = "unreachable"
                    service_info["error"] = f"Cannot connect to {service['host']}:{service['port']}"

            elif service["check"] == "http":
                # HTTP health check
                url = f"http://{service['host']}:{service['port']}{service.get('path', '/')}"
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(url)
                    if response.status_code < 500:
                        service_info["status"] = "healthy"
                    else:
                        service_info["status"] = "unhealthy"
                        service_info["error"] = f"HTTP {response.status_code}"

        except socket.timeout:
            service_info["status"] = "timeout"
            service_info["error"] = "Connection timed out"
        except socket.gaierror:
            service_info["status"] = "unreachable"
            service_info["error"] = f"Cannot resolve hostname {service['host']}"
        except httpx.ConnectError:
            service_info["status"] = "unreachable"
            service_info["error"] = f"Cannot connect to {service['host']}:{service['port']}"
        except httpx.TimeoutException:
            service_info["status"] = "timeout"
            service_info["error"] = "Request timed out"
        except Exception as e:
            service_info["status"] = "error"
            service_info["error"] = str(e)

        results["services"].append(service_info)

    return results
