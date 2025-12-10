from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response, PlainTextResponse
from pydantic import BaseModel
from typing import AsyncGenerator
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from alembic.config import Config
from alembic import command
import os
import logging

from .agent_manager import AgentManager
from tasks import run_llm, ingest_data
from utils.cache import get_cached_response, set_cached_response
from . import logging as app_logging
from .users import router as users_router
from .auth import router as auth_router
from . import users as users_module
from . import auth as auth_module
from .rag.routes import router as rag_router
from .settings_routes import router as settings_router
from .agent_prompts_routes import router as agent_prompts_router
from .image_routes import router as image_router
from .content_pipeline_routes import router as content_pipeline_router
from .projects_routes import router as projects_router
from .campaigns_routes import router as campaigns_router
from .categories_routes import router as categories_router
from .debug_routes import router as debug_router
from typing import List, Dict
from datetime import datetime


users_module.ensure_default_admin()

app_logging.setup_logging()
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],  # Frontend origins
    allow_origin_regex=r"http://localhost(:\d+)?|http://127\.0\.0\.1(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

app.add_middleware(app_logging.RequestIdMiddleware)
app.include_router(users_router)
app.include_router(rag_router)
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(agent_prompts_router)
app.include_router(image_router)
app.include_router(content_pipeline_router)
app.include_router(projects_router)
app.include_router(campaigns_router)
app.include_router(categories_router)
app.include_router(debug_router)


@app.on_event("startup")
def startup_event() -> None:
    """Run database migrations and create default admin on startup"""
    logger = logging.getLogger(__name__)

    # Run Alembic migrations
    try:
        logger.info("Running database migrations...")
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Failed to run database migrations: {e}")
        # Continue anyway - migrations might already be applied

    # Create default admin user
    users_module.ensure_default_admin()


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint returning a basic health message."""
    return {"message": "API running"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring and docker health checks."""
    return {
        "status": "healthy",
        "service": "marketer-backend",
        "version": "1.0.0"
    }

REQUEST_COUNT = Counter(
    "app_requests_total", "Total Request Count", ["method", "endpoint", "http_status"]
)


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    response = await call_next(request)
    REQUEST_COUNT.labels(
        request.method, request.url.path, response.status_code
    ).inc()
    return response


agent_manager = AgentManager()

recent_activity: List[Dict[str, str]] = []


def add_activity(message: str) -> None:
    recent_activity.append({"message": message, "timestamp": datetime.utcnow().isoformat()})
    if len(recent_activity) > 20:
        recent_activity.pop(0)


class LLMRequest(BaseModel):
    prompt: str


class IngestRequest(BaseModel):
    items: list[str]


class ContentRequest(BaseModel):
    content: str


@app.post('/llm')
async def llm_endpoint(req: LLMRequest):
    task = run_llm.delay(req.prompt)
    return {'task_id': task.id}


@app.post('/ingest')
async def ingest_endpoint(req: IngestRequest):
    task = ingest_data.delay(req.items)
    return {'task_id': task.id}


@app.get('/agents')
async def list_agents():
    return [
        {'name': name, 'description': agent.description()}
        for name, agent in agent_manager.available_agents.items()
    ]


class AgentRunRequest(BaseModel):
    params: dict = {}


@app.post('/agents/{agent_name}')
async def run_agent(agent_name: str, req: AgentRunRequest):
    agent = agent_manager.available_agents.get(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')
    result = agent.run(**req.params)
    return {'result': result}


@app.post('/agents/{agent_name}/stream')
async def stream_agent(agent_name: str, req: AgentRunRequest) -> StreamingResponse:
    agent = agent_manager.available_agents.get(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')

    async def event_stream() -> AsyncGenerator[str, None]:
        prompt = req.params.get('prompt', '')
        cached = get_cached_response(agent_name, prompt)
        if cached:
            for token in cached.split():
                yield f"data: {token}\n\n"
            return

        result = agent.run(**req.params)
        set_cached_response(agent_name, prompt, result)
        for token in result.split():
            yield f"data: {token}\n\n"

    return StreamingResponse(event_stream(), media_type='text/event-stream')


@app.get("/status")
async def get_status() -> Dict[str, List[Dict[str, str]]]:
    return {"activities": recent_activity}


@app.post('/export/wordpress')
async def export_wordpress(req: ContentRequest):
    """Stub endpoint to export content to WordPress."""
    add_activity("Exported content to WordPress")
    return {"status": "success"}


@app.post('/share/linkedin')
async def share_linkedin(req: ContentRequest):
    """Stub endpoint to share content on LinkedIn."""
    add_activity("Shared content on LinkedIn")
    return {"status": "shared"}


@app.post('/share/x')
async def share_x(req: ContentRequest):
    """Stub endpoint to share content on X (formerly Twitter)."""
    add_activity("Shared content on X")
    return {"status": "shared"}


@app.get("/metrics")
def metrics() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.get("/logs")
async def get_logs(
    limit: int = 100,
    user = Depends(auth_module.require_admin)
) -> PlainTextResponse:
    """
    Get application logs. Requires admin authentication.

    This endpoint is protected to prevent exposure of sensitive information
    that may be present in application logs.
    """
    try:
        with open("logs/app.log", "r") as f:
            lines = f.readlines()[-limit:]
        return PlainTextResponse("".join(lines))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log file not found")
