from __future__ import annotations

"""Helper utilities for managing agent prompt overrides."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .agents.prompts.content_pipeline_prompts import (
    FINAL_REVIEWER_AGENT_PROMPT,
    ORIGINALITY_PLAGIARISM_AGENT_PROMPT,
    SEO_OPTIMIZER_AGENT_PROMPT,
    STRUCTURE_OUTLINE_AGENT_PROMPT,
    TONE_OF_VOICE_RAG_AGENT_PROMPT,
    TRENDS_KEYWORDS_AGENT_PROMPT,
    WRITER_AGENT_PROMPT,
)

DATA_DIR = Path(__file__).parent / "data"
PROMPTS_FILE = DATA_DIR / "agent_prompts.json"


class AgentPrompt(BaseModel):
    """Agent prompt configuration returned to clients."""

    agentId: str = Field(..., description="Agent identifier")
    name: str
    description: str
    systemPrompt: str
    userPromptTemplate: str
    variables: List[str] = Field(default_factory=list)
    defaultSystemPrompt: str
    defaultUserPromptTemplate: str
    updatedAt: Optional[str] = None
    source: str = "default"


class AgentPromptUpdate(BaseModel):
    """Payload for updating an agent prompt."""

    systemPrompt: Optional[str] = None
    userPromptTemplate: Optional[str] = None


class PromptGenerationRequest(BaseModel):
    """Payload for generating a tailored prompt suggestion."""

    agentId: str
    goal: Optional[str] = None
    audience: Optional[str] = None
    brandVoice: Optional[str] = None
    outputFormat: Optional[str] = None
    constraints: Optional[str] = None
    variables: Optional[Dict[str, str]] = None


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_saved_prompts() -> Dict[str, Dict[str, str]]:
    """Load saved prompt overrides from disk."""

    _ensure_data_dir()
    if not PROMPTS_FILE.exists():
        return {}

    try:
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_prompts(data: Dict[str, Dict[str, str]]) -> None:
    """Persist prompt overrides to disk."""

    _ensure_data_dir()
    with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_default_prompts() -> Dict[str, Dict[str, str]]:
    """Return the default prompts for all content pipeline agents."""

    return {
        "trends_keywords": {
            "name": "Trends & Keywords Agent",
            "description": "Researches the topic to surface trends, keywords, and search intent insights.",
            "systemPrompt": TRENDS_KEYWORDS_AGENT_PROMPT,
            "userPromptTemplate": (
                "Analyze the following topic and provide trend research and keyword extraction:\n\n"
                "Topic: {topic}\n"
                "Content Type: {content_type}\n"
                "Target Audience: {audience}\n"
                "Goal: {goal}\n"
                "Brand Voice: {brand_voice}\n"
                "Language: {language}\n"
                "Context: {context_summary}\n\n"
                "Provide your analysis in the specified JSON format."
            ),
            "variables": [
                "topic",
                "content_type",
                "audience",
                "goal",
                "brand_voice",
                "language",
                "length_constraints",
                "context_summary",
            ],
        },
        "tone_of_voice": {
            "name": "Tone-of-Voice RAG Agent",
            "description": "Builds a style profile from brand guidelines and retrieved examples.",
            "systemPrompt": TONE_OF_VOICE_RAG_AGENT_PROMPT,
            "userPromptTemplate": (
                "Analyze the following brand voice examples and create a style profile:\n\n"
                "Topic: {topic}\n"
                "Content Type: {content_type}\n"
                "Target Audience: {audience}\n"
                "Goal: {goal}\n"
                "Brand Voice Guidelines: {brand_voice}\n"
                "Language: {language}\n\n"
                "Style Examples from RAG:\n{retrieved_style_chunks}\n\n"
                "Additional Context: {context_summary}\n\n"
                "Create a detailed style profile in the specified JSON format."
            ),
            "variables": [
                "topic",
                "content_type",
                "audience",
                "goal",
                "brand_voice",
                "language",
                "retrieved_style_chunks",
                "context_summary",
            ],
        },
        "structure_outline": {
            "name": "Structure & Outline Agent",
            "description": "Designs a conversion-oriented outline using research and style context.",
            "systemPrompt": STRUCTURE_OUTLINE_AGENT_PROMPT,
            "userPromptTemplate": (
                "Create a detailed content outline based on the following:\n\n"
                "Topic: {topic}\n"
                "Content Type: {content_type}\n"
                "Target Audience: {audience}\n"
                "Goal: {goal}\n"
                "Brand Voice: {brand_voice}\n"
                "Language: {language}\n"
                "Length: {length_constraints}\n\n"
                "Research & Keywords:\n{trends_info}\n\n"
                "Style Profile: {style_profile}\n\n"
                "Context: {context_summary}\n\n"
                "Create a conversion-oriented outline in the specified JSON format."
            ),
            "variables": [
                "topic",
                "content_type",
                "audience",
                "goal",
                "brand_voice",
                "language",
                "length_constraints",
                "context_summary",
                "trends_info",
                "style_profile",
            ],
        },
        "writer": {
            "name": "Writer Agent",
            "description": "Produces the full draft following the outline, research, and style guidance.",
            "systemPrompt": WRITER_AGENT_PROMPT,
            "userPromptTemplate": (
                "Write the full content based on the following brief:\n\n"
                "Topic: {topic}\n"
                "Content Type: {content_type}\n"
                "Target Audience: {audience}\n"
                "Goal: {goal}\n"
                "Brand Voice: {brand_voice}\n"
                "Language: {language}\n"
                "Length: {length_constraints}\n\n"
                "Outline:\n{outline}\n\n"
                "Research & Keywords:\n{trends_info}\n\n"
                "Style Profile:\n{style_profile}\n\n"
                "Context: {context_summary}\n\n"
                "Write the complete Markdown content."
            ),
            "variables": [
                "topic",
                "content_type",
                "audience",
                "goal",
                "brand_voice",
                "language",
                "length_constraints",
                "outline",
                "trends_info",
                "style_profile",
                "context_summary",
            ],
        },
        "seo_optimizer": {
            "name": "SEO Optimizer Agent",
            "description": "Optimizes the draft for SEO and readability with on-page elements.",
            "systemPrompt": SEO_OPTIMIZER_AGENT_PROMPT,
            "userPromptTemplate": (
                "Optimize the following draft for SEO and readability:\n\n"
                "Topic: {topic}\n"
                "Content Type: {content_type}\n"
                "Target Audience: {audience}\n"
                "Goal: {goal}\n"
                "Brand Voice: {brand_voice}\n"
                "Language: {language}\n"
                "Focus Keywords: {focus_keywords}\n\n"
                "Draft Content:\n{draft}\n\n"
                "Style Profile:\n{style_profile}\n\n"
                "Provide optimized content and on-page SEO elements in the specified JSON format."
            ),
            "variables": [
                "topic",
                "content_type",
                "audience",
                "goal",
                "brand_voice",
                "language",
                "focus_keywords",
                "draft",
                "style_profile",
            ],
        },
        "originality_plagiarism": {
            "name": "Originality & Plagiarism Agent",
            "description": "Flags generic or risky passages and suggests rewrites to improve originality.",
            "systemPrompt": ORIGINALITY_PLAGIARISM_AGENT_PROMPT,
            "userPromptTemplate": (
                "Review the optimized content for originality and plagiarism risks.\n\n"
                "Topic: {topic}\n"
                "Content Type: {content_type}\n"
                "Audience: {audience}\n"
                "Goal: {goal}\n"
                "Language: {language}\n\n"
                "Optimized Draft:\n{draft}\n\n"
                "Return an originality score and rewrite suggestions in the specified JSON format."
            ),
            "variables": [
                "topic",
                "content_type",
                "audience",
                "goal",
                "language",
                "draft",
            ],
        },
        "final_reviewer": {
            "name": "Final Reviewer Agent",
            "description": "Polishes the content, applies fixes, and prepares the final deliverable.",
            "systemPrompt": FINAL_REVIEWER_AGENT_PROMPT,
            "userPromptTemplate": (
                "Perform final editorial review of the content.\n\n"
                "Topic: {topic}\n"
                "Content Type: {content_type}\n"
                "Audience: {audience}\n"
                "Goal: {goal}\n"
                "Language: {language}\n"
                "Brand Voice: {brand_voice}\n\n"
                "Draft to Review:\n{draft}\n\n"
                "Originality Notes:\n{originality_notes}\n\n"
                "Provide the polished content and change log in the specified JSON format."
            ),
            "variables": [
                "topic",
                "content_type",
                "audience",
                "goal",
                "language",
                "brand_voice",
                "draft",
                "originality_notes",
            ],
        },
    }


def load_agent_prompts() -> Dict[str, AgentPrompt]:
    """Load prompts merged with defaults and any saved overrides."""

    defaults = get_default_prompts()
    saved = _load_saved_prompts()

    merged: Dict[str, AgentPrompt] = {}
    for agent_id, default in defaults.items():
        custom = saved.get(agent_id, {})
        system_prompt = custom.get("systemPrompt", default["systemPrompt"])
        user_template = custom.get("userPromptTemplate", default["userPromptTemplate"])
        merged[agent_id] = AgentPrompt(
            agentId=agent_id,
            name=default["name"],
            description=default["description"],
            systemPrompt=system_prompt,
            userPromptTemplate=user_template,
            defaultSystemPrompt=default["systemPrompt"],
            defaultUserPromptTemplate=default["userPromptTemplate"],
            variables=default.get("variables", []),
            updatedAt=custom.get("updatedAt"),
            source="custom" if agent_id in saved else "default",
        )

    return merged


def get_agent_prompt_config(agent_id: str) -> Optional[AgentPrompt]:
    """Return a single agent prompt configuration."""

    return load_agent_prompts().get(agent_id)


def save_agent_prompt(agent_id: str, update: AgentPromptUpdate) -> AgentPrompt:
    """Save overrides for a specific agent and return the merged config."""

    defaults = get_default_prompts()
    if agent_id not in defaults:
        raise ValueError(f"Unknown agent: {agent_id}")

    saved = _load_saved_prompts()
    current = saved.get(agent_id, {})

    if update.systemPrompt is not None:
        current["systemPrompt"] = update.systemPrompt
    if update.userPromptTemplate is not None:
        current["userPromptTemplate"] = update.userPromptTemplate

    current["updatedAt"] = datetime.utcnow().isoformat()
    saved[agent_id] = current
    _save_prompts(saved)

    return load_agent_prompts()[agent_id]


BEST_PRACTICES = [
    "Anchor the agent's role and success criteria in the first lines.",
    "List required inputs and variables explicitly so missing data is obvious.",
    "Spell out structure and output format, including JSON keys if applicable.",
    "Include do/don't lists to guardrail tone, brand safety, and claims.",
    "Add examples or mini checklists for nuanced instructions (style, SEO, QA).",
    "Set refusal and hallucination guidance (e.g., cite sources, avoid guessing).",
    "Keep temperature guidance close to creative steps, lower for evaluators.",
    "Define how to handle ambiguity (ask clarifying questions or note assumptions).",
]


def generate_prompt_suggestion(request: PromptGenerationRequest) -> AgentPromptUpdate:
    """Generate a deterministic prompt suggestion using provided context."""

    defaults = get_default_prompts()
    default = defaults.get(request.agentId)
    if not default:
        raise ValueError("Unknown agent")

    parts = [default["systemPrompt"].strip(), "\n\n## Customization Notes\n"]
    if request.goal:
        parts.append(f"- Primary goal: {request.goal}")
    if request.audience:
        parts.append(f"- Audience focus: {request.audience}")
    if request.brandVoice:
        parts.append(f"- Style and tone: {request.brandVoice}")
    if request.outputFormat:
        parts.append(f"- Output format: {request.outputFormat}")
    if request.constraints:
        parts.append(f"- Constraints: {request.constraints}")
    if request.variables:
        for key, value in request.variables.items():
            parts.append(f"- Variable {key}: {value}")

    system_prompt = "\n".join(parts).strip()

    user_template = default["userPromptTemplate"]
    if request.variables:
        guidance = "\n\n" + "\n".join(
            [f"{k}: {{{k}}} (example: {v})" for k, v in request.variables.items()]
        )
        user_template = f"{default['userPromptTemplate']}\n\nInclude the following variable guidance when filling the template:{guidance}"

    return AgentPromptUpdate(systemPrompt=system_prompt, userPromptTemplate=user_template)
