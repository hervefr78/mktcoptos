"""Add settings tables for user and organization preferences

Revision ID: 001_add_settings
Revises:
Create Date: 2025-11-17 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_settings'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_settings table
    op.create_table(
        'user_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        # LLM Provider Settings
        sa.Column('llm_provider', sa.String(50), server_default='ollama'),
        sa.Column('llm_model', sa.String(100)),
        sa.Column('openai_api_key', sa.String(500)),
        sa.Column('openai_organization_id', sa.String(255)),
        sa.Column('ollama_base_url', sa.String(255), server_default='http://localhost:11434'),

        # Image Generation Settings
        sa.Column('image_provider', sa.String(50), server_default='openai'),
        sa.Column('openai_image_model', sa.String(50), server_default='dall-e-3'),
        sa.Column('openai_image_quality', sa.String(20), server_default='standard'),
        sa.Column('openai_image_size', sa.String(20), server_default='1024x1024'),
        sa.Column('openai_image_style', sa.String(20), server_default='natural'),
        sa.Column('sd_base_url', sa.String(255), server_default='http://localhost:7860'),
        sa.Column('use_hybrid_images', sa.Boolean(), server_default='false'),

        # Prompt Contexts
        sa.Column('marketing_prompt_context', sa.Text()),
        sa.Column('blog_prompt_context', sa.Text()),
        sa.Column('social_media_prompt_context', sa.Text()),
        sa.Column('image_prompt_context', sa.Text()),

        # UI Preferences
        sa.Column('theme', sa.String(20), server_default='light'),
        sa.Column('sidebar_width', sa.Integer(), server_default='240'),
        sa.Column('default_view', sa.String(50), server_default='list'),

        # Notification Preferences
        sa.Column('timezone', sa.String(50), server_default='UTC'),
        sa.Column('notification_email', sa.String(255)),
        sa.Column('email_notifications', sa.Boolean(), server_default='true'),
        sa.Column('browser_notifications', sa.Boolean(), server_default='true'),

        # Timestamps
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('idx_user_settings_user_id', 'user_settings', ['user_id'])

    # Create organization_settings table
    op.create_table(
        'organization_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),

        # Default LLM Provider
        sa.Column('default_llm_provider', sa.String(50), server_default='ollama'),
        sa.Column('default_llm_model', sa.String(100)),
        sa.Column('default_ollama_base_url', sa.String(255), server_default='http://localhost:11434'),

        # Organization API Keys
        sa.Column('org_openai_api_key', sa.String(500)),
        sa.Column('org_anthropic_api_key', sa.String(500)),

        # Default Image Generation
        sa.Column('default_image_provider', sa.String(50), server_default='openai'),
        sa.Column('default_image_model', sa.String(50), server_default='dall-e-3'),

        # Organization Prompt Contexts
        sa.Column('org_marketing_prompt_context', sa.Text()),
        sa.Column('org_blog_prompt_context', sa.Text()),
        sa.Column('org_social_media_prompt_context', sa.Text()),
        sa.Column('org_image_prompt_context', sa.Text()),

        # Brand Guidelines
        sa.Column('brand_voice', postgresql.JSON(astext_type=sa.Text())),
        sa.Column('brand_colors', postgresql.ARRAY(sa.String())),
        sa.Column('brand_fonts', postgresql.ARRAY(sa.String())),

        # Content Policies
        sa.Column('content_approval_required', sa.Boolean(), server_default='false'),
        sa.Column('auto_publish_enabled', sa.Boolean(), server_default='false'),

        # Compliance & Security
        sa.Column('data_retention_days', sa.Integer(), server_default='90'),
        sa.Column('pii_detection_enabled', sa.Boolean(), server_default='true'),
        sa.Column('content_moderation_enabled', sa.Boolean(), server_default='true'),

        # Timestamps
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('organization_id')
    )
    op.create_index('idx_org_settings_org_id', 'organization_settings', ['organization_id'])

    # Create settings_history table (audit trail)
    op.create_table(
        'settings_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('settings_type', sa.String(50), nullable=False),
        sa.Column('settings_id', sa.Integer(), nullable=False),
        sa.Column('changed_by_user_id', sa.Integer()),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('old_value', sa.Text()),
        sa.Column('new_value', sa.Text()),
        sa.Column('change_reason', sa.Text()),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.Text()),
        sa.Column('changed_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'])
    )
    op.create_index('idx_settings_history_type', 'settings_history', ['settings_type'])
    op.create_index('idx_settings_history_id', 'settings_history', ['settings_id'])
    op.create_index('idx_settings_history_user', 'settings_history', ['changed_by_user_id'])
    op.create_index('idx_settings_history_time', 'settings_history', ['changed_at'])
    op.create_index('idx_settings_history_lookup', 'settings_history', ['settings_type', 'settings_id', 'changed_at'])

    # Add triggers for updated_at
    op.execute("""
        CREATE TRIGGER update_user_settings_updated_at
        BEFORE UPDATE ON user_settings
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER update_organization_settings_updated_at
        BEFORE UPDATE ON organization_settings
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_organization_settings_updated_at ON organization_settings;")
    op.execute("DROP TRIGGER IF EXISTS update_user_settings_updated_at ON user_settings;")

    # Drop tables
    op.drop_index('idx_settings_history_lookup', 'settings_history')
    op.drop_index('idx_settings_history_time', 'settings_history')
    op.drop_index('idx_settings_history_user', 'settings_history')
    op.drop_index('idx_settings_history_id', 'settings_history')
    op.drop_index('idx_settings_history_type', 'settings_history')
    op.drop_table('settings_history')

    op.drop_index('idx_org_settings_org_id', 'organization_settings')
    op.drop_table('organization_settings')

    op.drop_index('idx_user_settings_user_id', 'user_settings')
    op.drop_table('user_settings')
