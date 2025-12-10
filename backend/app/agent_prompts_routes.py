"""API routes for managing agent prompt overrides."""

from fastapi import APIRouter, HTTPException

from .agent_prompts import (
    BEST_PRACTICES,
    AgentPrompt,
    AgentPromptUpdate,
    PromptGenerationRequest,
    generate_prompt_suggestion,
    get_agent_prompt_config,
    load_agent_prompts,
    save_agent_prompt,
)

router = APIRouter(prefix="/api/agent-prompts", tags=["agent-prompts"])

# NOTE: keep static routes registered before parameterized paths to avoid
# `/{agent_id}` capturing them and returning a 404 for known endpoints such as
# `/best-practices`.
@router.post("/generate", response_model=AgentPromptUpdate)
async def generate_prompt(payload: PromptGenerationRequest) -> AgentPromptUpdate:
    """Generate a deterministic prompt suggestion based on user input."""

    try:
        return generate_prompt_suggestion(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/best-practices", response_model=list[str])
async def best_practices() -> list[str]:
    """Return a curated list of prompt-writing best practices."""

    return BEST_PRACTICES


@router.get("", response_model=list[AgentPrompt])
async def list_agent_prompts() -> list[AgentPrompt]:
    """List all agent prompts with defaults and overrides merged."""

    return list(load_agent_prompts().values())


@router.get("/{agent_id}", response_model=AgentPrompt)
async def get_agent_prompt(agent_id: str) -> AgentPrompt:
    """Return prompt configuration for a single agent."""

    config = get_agent_prompt_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Unknown agent")
    return config


@router.put("/{agent_id}", response_model=AgentPrompt)
async def update_agent_prompt(agent_id: str, payload: AgentPromptUpdate) -> AgentPrompt:
    """Update prompt overrides for a given agent."""

    try:
        return save_agent_prompt(agent_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/generate", response_model=AgentPromptUpdate)
async def generate_prompt(payload: PromptGenerationRequest) -> AgentPromptUpdate:
    """Generate a deterministic prompt suggestion based on user input."""

    try:
        return generate_prompt_suggestion(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/best-practices", response_model=list[str])
async def best_practices() -> list[str]:
    """Return a curated list of prompt-writing best practices."""

    return BEST_PRACTICES
