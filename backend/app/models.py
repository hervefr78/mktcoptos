"""
SQLAlchemy ORM Models
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, TIMESTAMP, ForeignKey,
    DECIMAL, BIGINT, ARRAY, JSON, Index, func, Float
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    clerk_id = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255))
    role = Column(String(50), nullable=False, default="user", index=True)

    # Profile
    first_name = Column(String(100))
    last_name = Column(String(100))
    avatar_url = Column(Text)

    # Settings
    preferences = Column(JSON, default={})

    # Status
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(TIMESTAMP)

    # Relationships
    user_settings = relationship("UserSettings", back_populates="user", cascade="all, delete-orphan")
    organization_memberships = relationship("OrganizationMember", back_populates="user", foreign_keys="OrganizationMember.user_id")


class Organization(Base):
    """Organization model for multi-tenancy"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)

    # Subscription
    plan = Column(String(50), nullable=False, default="free", index=True)
    plan_started_at = Column(TIMESTAMP)
    plan_expires_at = Column(TIMESTAMP)

    # Billing
    stripe_customer_id = Column(String(255), unique=True)
    stripe_subscription_id = Column(String(255))

    # Quotas
    max_users = Column(Integer, nullable=False, default=1)
    max_projects = Column(Integer, nullable=False, default=3)
    max_storage_gb = Column(Integer, nullable=False, default=5)
    requests_per_day = Column(Integer, nullable=False, default=100)

    # Usage tracking
    current_storage_gb = Column(DECIMAL(10, 2), default=0)
    requests_today = Column(Integer, default=0)
    requests_this_month = Column(Integer, default=0)
    last_reset_date = Column(String(10))  # DATE as string (YYYY-MM-DD)

    # LLM Configuration
    llm_mode = Column(String(50), default="cloud")
    agent_status = Column(String(50))
    agent_last_seen = Column(TIMESTAMP)

    # Encrypted API keys
    openai_api_key = Column(String(500))
    anthropic_api_key = Column(String(500))
    mistral_api_key = Column(String(500))

    # Compliance
    compliance_mode = Column(String(50))
    data_residency = Column(String(50))

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    members = relationship("OrganizationMember", back_populates="organization")
    organization_settings = relationship("OrganizationSettings", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="organization")


class Category(Base):
    """Organization-level categories shared across content and campaigns"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", backref="categories")

    __table_args__ = (
        Index('idx_category_org_name', 'organization_id', 'name', unique=True),
    )


class Campaign(Base):
    """Marketing campaign grouping multiple projects"""

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text)
    model = Column(String(255))

    # Campaign type and settings
    campaign_type = Column(String(50), nullable=False, default="standalone", index=True)  # standalone or integrated
    default_language = Column(String(50), default="auto")

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", backref="campaigns")
    category = relationship("Category", backref="campaigns")

    __table_args__ = (
        Index('idx_campaign_org_name', 'organization_id', 'name'),
        Index('idx_campaign_type', 'campaign_type'),
    )


class OrganizationMember(Base):
    """Organization membership model"""
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="member")

    # Invitation
    invited_by = Column(Integer, ForeignKey("users.id"))
    invited_at = Column(TIMESTAMP, default=datetime.utcnow)
    invitation_token = Column(String(255), unique=True)
    invitation_expires_at = Column(TIMESTAMP)
    joined_at = Column(TIMESTAMP)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="organization_memberships", foreign_keys=[user_id])
    organization = relationship("Organization", back_populates="members")

    __table_args__ = (
        Index('idx_org_members_unique', 'user_id', 'organization_id', unique=True),
    )


class Project(Base):
    """Project model"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Brand voice
    brand_voice = Column(JSON)

    # Settings
    default_tone = Column(String(50), default="professional")
    default_target_audience = Column(Text)
    default_keywords = Column(ARRAY(Text))
    language = Column(String(50), default="auto")  # auto, en, fr, de, es, it

    # Integrated campaign support - main/sub project relationships
    parent_project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    is_main_project = Column(Boolean, default=False, nullable=False, index=True)
    inherit_tone = Column(Boolean, default=True, nullable=False)  # Whether to inherit tone from parent
    content_type = Column(String(100))  # blog, linkedin, newsletter, etc.

    # Sharing
    visibility = Column(String(50), default="organization")

    # Status
    is_archived = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="projects")
    category = relationship("Category", backref="projects")
    campaign = relationship("Campaign", backref="projects")

    # Self-referential relationship for parent/sub projects
    parent_project = relationship("Project", remote_side=[id], backref="sub_projects", foreign_keys=[parent_project_id])

    __table_args__ = (
        Index('idx_project_org_created', 'organization_id', 'created_at'),
        Index('idx_project_org_archived', 'organization_id', 'is_archived'),
        Index('idx_project_owner_archived', 'owner_id', 'is_archived'),
        Index('idx_project_campaign', 'campaign_id'),
        Index('idx_project_main', 'campaign_id', 'is_main_project'),
    )


# ============================================================================
# SETTINGS MODELS (NEW)
# ============================================================================

class UserSettings(Base):
    """User-specific settings (personal preferences)"""
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # LLM Provider Settings (Personal)
    llm_provider = Column(String(50), default="ollama")  # "openai" or "ollama"
    llm_model = Column(String(100))
    openai_api_key = Column(String(500))  # User's personal API key
    openai_organization_id = Column(String(255))
    ollama_base_url = Column(String(255), default="http://localhost:11434")

    # Web Search Settings
    brave_search_api_key = Column(String(500))  # For web search in Research & Originality agents

    # Image Generation Settings (Personal)
    image_provider = Column(String(50), default="openai")
    openai_image_model = Column(String(50), default="dall-e-3")
    openai_image_quality = Column(String(20), default="standard")
    openai_image_size = Column(String(20), default="1024x1024")
    openai_image_style = Column(String(20), default="natural")
    sd_base_url = Column(String(255), default="http://localhost:7860")
    use_hybrid_images = Column(Boolean, default=False)

    # ComfyUI Settings
    comfyui_base_url = Column(String(255), default="http://localhost:8188")
    sdxl_model = Column(String(255), default="sd_xl_turbo_1.0_fp16.safetensors")
    sdxl_steps = Column(Integer, default=6)
    sdxl_cfg_scale = Column(DECIMAL(3, 1), default=1.0)
    sdxl_sampler = Column(String(50), default="euler_ancestral")

    # Hybrid Image Strategy
    use_gpt_image_for_posts = Column(Boolean, default=True)
    use_comfyui_for_blogs = Column(Boolean, default=True)

    # Prompt Contexts (Personal)
    marketing_prompt_context = Column(Text)
    blog_prompt_context = Column(Text)
    social_media_prompt_context = Column(Text)
    image_prompt_context = Column(Text)

    # UI Preferences
    theme = Column(String(20), default="light")  # light, dark, auto
    sidebar_width = Column(Integer, default=240)
    default_view = Column(String(50), default="list")

    # Notification Preferences
    timezone = Column(String(50), default="UTC")
    notification_email = Column(String(255))
    email_notifications = Column(Boolean, default=True)
    browser_notifications = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="user_settings")


class OrganizationSettings(Base):
    """Organization-level settings (shared across team)"""
    __tablename__ = "organization_settings"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Default LLM Provider for Organization
    default_llm_provider = Column(String(50), default="ollama")
    default_llm_model = Column(String(100))
    default_ollama_base_url = Column(String(255), default="http://localhost:11434")

    # Organization-wide API Keys (shared)
    org_openai_api_key = Column(String(500))
    org_anthropic_api_key = Column(String(500))
    brave_search_api_key = Column(String(500))  # For web search in Research & Originality agents

    # Default Image Generation
    default_image_provider = Column(String(50), default="openai")
    default_image_model = Column(String(50), default="dall-e-3")

    # Organization Prompt Contexts (defaults for new projects)
    org_marketing_prompt_context = Column(Text)
    org_blog_prompt_context = Column(Text)
    org_social_media_prompt_context = Column(Text)
    org_image_prompt_context = Column(Text)

    # Brand Guidelines (organization-wide)
    brand_voice = Column(JSON)
    brand_colors = Column(ARRAY(String))
    brand_fonts = Column(ARRAY(String))

    # Content Policies
    content_approval_required = Column(Boolean, default=False)
    auto_publish_enabled = Column(Boolean, default=False)

    # Compliance & Security
    data_retention_days = Column(Integer, default=90)
    pii_detection_enabled = Column(Boolean, default=True)
    content_moderation_enabled = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="organization_settings")


class SettingsHistory(Base):
    """Audit trail for settings changes"""
    __tablename__ = "settings_history"

    id = Column(Integer, primary_key=True, index=True)

    # What was changed
    settings_type = Column(String(50), nullable=False, index=True)  # "user", "organization"
    settings_id = Column(Integer, nullable=False, index=True)  # ID of user_settings or organization_settings

    # Who changed it
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), index=True)

    # What changed
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)

    # Context
    change_reason = Column(Text)
    ip_address = Column(String(45))  # Supports IPv6
    user_agent = Column(Text)

    # Timestamp
    changed_at = Column(TIMESTAMP, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('idx_settings_history_lookup', 'settings_type', 'settings_id', 'changed_at'),
    )


# ============================================================================
# CONTENT PIPELINE MODELS
# ============================================================================

class PipelineExecution(Base):
    """
    Stores complete pipeline execution history.

    Each record represents one full run of the content pipeline.
    """
    __tablename__ = "pipeline_executions"

    id = Column(Integer, primary_key=True, index=True)
    pipeline_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), index=True)

    # Input parameters
    topic = Column(Text, nullable=False)
    content_type = Column(String(100), default="blog post")
    audience = Column(String(255), default="general")
    goal = Column(String(100), default="awareness")
    brand_voice = Column(String(255), default="professional")
    language = Column(String(50), default="English")
    length_constraints = Column(String(100), default="1000-1500 words")
    context_summary = Column(Text)

    # Execution status
    status = Column(String(50), nullable=False, default="pending", index=True)  # pending, running, completed, failed
    current_stage = Column(String(50))

    # Final result (stored as JSON)
    final_result = Column(JSON)
    final_content = Column(Text)  # Extracted final text for easy access

    # Stage-by-stage summaries for transparency (Phase 1A: Real-time progress)
    stage_summaries = Column(JSON, default=dict)  # {stage_name: {duration, actions, inputs, outputs}}

    # Metadata
    word_count = Column(Integer)
    seo_score = Column(Integer)
    originality_score = Column(String(20))

    # Metrics
    total_duration_seconds = Column(Integer)
    total_tokens_used = Column(Integer)
    estimated_cost = Column(DECIMAL(10, 4))

    # Error tracking
    error_message = Column(Text)
    error_stage = Column(String(50))

    # Timestamps
    started_at = Column(TIMESTAMP, default=datetime.utcnow)
    completed_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    step_results = relationship("PipelineStepResult", back_populates="execution", cascade="all, delete-orphan")
    project = relationship("Project", backref="pipeline_executions")

    __table_args__ = (
        Index('idx_pipeline_user_created', 'user_id', 'created_at'),
        Index('idx_pipeline_status_created', 'status', 'created_at'),
        Index('idx_pipeline_project_created', 'project_id', 'created_at'),
    )


class PipelineStepResult(Base):
    """
    Stores individual step results within a pipeline execution.

    Enables:
    - Pipeline resume on failure
    - Step-by-step editing
    - Audit trail for debugging
    """
    __tablename__ = "pipeline_step_results"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("pipeline_executions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Step identification
    stage = Column(String(50), nullable=False, index=True)  # trends_keywords, tone_of_voice, etc.
    stage_order = Column(Integer, nullable=False)  # 1-7

    # Status
    status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed

    # Result (stored as JSON)
    result = Column(JSON)

    # Metrics
    duration_seconds = Column(Integer)
    tokens_used = Column(Integer)

    # Agent logging - captures full communication
    prompt_system = Column(Text)  # Full system prompt sent to LLM
    prompt_user = Column(Text)  # User prompt sent to LLM
    input_context = Column(JSON)  # Structured input data (topic, audience, previous results)
    raw_response = Column(Text)  # Raw LLM response before parsing
    model_used = Column(String(100))  # e.g., "gpt-4o-mini", "claude-3-sonnet"
    temperature = Column(Float)  # Temperature setting used
    input_tokens = Column(Integer)  # Input token count
    output_tokens = Column(Integer)  # Output token count

    # Error tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Timestamps
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)

    # Relationships
    execution = relationship("PipelineExecution", back_populates="step_results")

    __table_args__ = (
        Index('idx_step_execution_stage', 'execution_id', 'stage'),
    )


class AgentActivity(Base):
    """
    Tracks detailed activity for each AI agent during content pipeline execution.

    Each row represents one agent execution with real-time updates for:
    - Decisions made during execution
    - RAG documents accessed
    - Content changes (before/after)
    - Performance breakdown
    - LLM usage and costs
    - Quality metrics
    """
    __tablename__ = "agent_activities"

    id = Column(Integer, primary_key=True, index=True)
    pipeline_execution_id = Column(Integer, ForeignKey("pipeline_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False)
    stage = Column(String(50), nullable=False, index=True)

    # Execution tracking
    started_at = Column(TIMESTAMP, nullable=False)
    completed_at = Column(TIMESTAMP)
    duration_seconds = Column(Float)
    status = Column(String(20), default="running", index=True)  # running, completed, failed

    # Input/Output
    input_summary = Column(JSON)
    output_summary = Column(JSON)

    # Decisions & Actions (array - append as they happen)
    decisions = Column(JSON, default=list)  # [{timestamp, description, data}]

    # RAG tracking
    rag_documents = Column(JSON, default=list)  # [{doc_id, doc_name, chunks_used, influence_score, purpose}]

    # Before/After (for optimization agents)
    content_before = Column(Text)
    content_after = Column(Text)
    changes_made = Column(JSON, default=list)  # [{type, before, after, reason, location}]

    # Performance metrics
    performance_breakdown = Column(JSON)

    # LLM usage
    model_used = Column(String(100))
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    estimated_cost = Column(DECIMAL(10, 6), default=0)

    # Quality metrics
    quality_metrics = Column(JSON)
    badges = Column(JSON, default=list)

    # Diagnostics
    warnings = Column(JSON, default=list)
    errors = Column(JSON, default=list)

    # Audit
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    execution = relationship("PipelineExecution", backref="agent_activities")

    __table_args__ = (
        Index('idx_agent_activities_pipeline', 'pipeline_execution_id'),
        Index('idx_agent_activities_stage', 'stage'),
        Index('idx_agent_activities_status', 'status'),
        Index('idx_agent_activities_created', 'created_at'),
    )


class CheckpointSession(Base):
    """
    Stores checkpoint session state for manual pipeline control.

    Enables users to pause, review, edit, and resume pipeline execution
    at each stage boundary.
    """
    __tablename__ = "checkpoint_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), unique=True, nullable=False, index=True)
    execution_id = Column(Integer, ForeignKey("pipeline_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)

    # Session configuration
    mode = Column(String(20), nullable=False, default="automatic")  # automatic or checkpoint

    # Current state
    status = Column(String(50), nullable=False, default="active", index=True)  # active, waiting_approval, paused, completed, cancelled
    current_stage = Column(String(50))  # Which stage we're waiting at
    stages_completed = Column(JSON, default=list)  # List of completed stage names

    # Stage results (for editing and resuming)
    stage_results = Column(JSON, default=dict)  # {stage_name: result_data}

    # User modifications tracking
    user_edits = Column(JSON, default=list)  # [{stage, action, changes, timestamp}]

    # Checkpoint history
    checkpoint_actions = Column(JSON, default=list)  # [{stage, action, timestamp, details}]

    # Next agent instructions (user can provide guidance)
    pending_instructions = Column(Text)  # Instructions for next stage

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_action_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(TIMESTAMP)
    expires_at = Column(TIMESTAMP)  # Auto-cleanup old sessions (7 days)

    # Relationships
    execution = relationship("PipelineExecution", backref="checkpoint_sessions")

    __table_args__ = (
        Index('idx_checkpoint_user_status', 'user_id', 'status'),
        Index('idx_checkpoint_expires', 'expires_at'),
    )


class GeneratedImage(Base):
    """Generated/Uploaded Image model for image gallery"""
    __tablename__ = "generated_images"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), index=True)
    pipeline_execution_id = Column(Integer, ForeignKey("pipeline_executions.id", ondelete="SET NULL"), index=True)

    # Multi-project support (stores array of project IDs)
    projects = Column(JSON, default=list)  # Array of project IDs for multi-project associations

    # Image metadata
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # Size in bytes
    mime_type = Column(String(100), default="image/png")

    # Dimensions
    width = Column(Integer)
    height = Column(Integer)

    # Generation details
    source = Column(String(50), default="openai", index=True)  # openai, comfyui, stable-diffusion, manual-upload
    openai_model = Column(String(100))  # dall-e-3, gpt-image-1, etc.
    sdxl_model = Column(String(255))  # For ComfyUI
    quality = Column(String(20))
    style = Column(String(20))

    # Generation metrics
    generation_time_seconds = Column(Integer)

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow, index=True)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pipeline_execution = relationship("PipelineExecution", backref="images")
    project = relationship("Project", backref="generated_images")

    __table_args__ = (
        Index('idx_image_user_created', 'user_id', 'created_at'),
        Index('idx_image_source_created', 'source', 'created_at'),
        Index('idx_image_pipeline', 'pipeline_execution_id'),
    )


class RagDocument(Base):
    """RAG Document model for knowledge base storage"""
    __tablename__ = "rag_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # Size in bytes
    file_type = Column(String(50))  # pdf, docx, txt

    # Organization and project
    organization_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    project_name = Column(String(255), default="General")
    projects = Column(JSON, default=list)  # Array of project names for multi-project support
    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    # Campaign association for integrated campaigns
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)

    # Collection type (brand_voice for style/tone, knowledge_base for content/facts)
    collection = Column(String(50), default="knowledge_base", index=True)  # brand_voice or knowledge_base

    # Processing status
    status = Column(String(50), default="pending", index=True)  # pending, processing, completed, failed
    chunks_count = Column(Integer, default=0)
    error_message = Column(Text)

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(TIMESTAMP)

    __table_args__ = (
        Index('idx_rag_doc_org_project', 'organization_id', 'project_id'),
    )
