"""Add Brave Search API key for web search integration

Revision ID: 018_add_brave_search
Revises: 017_add_integrated_campaigns
Create Date: 2025-12-03 14:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '018_add_brave_search'
down_revision = '017_add_integrated_campaigns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add brave_search_api_key to user_settings table (if not exists)
    from sqlalchemy import inspect
    from sqlalchemy.engine import reflection

    bind = op.get_bind()
    inspector = inspect(bind)

    # Check if column exists in user_settings
    user_settings_columns = [col['name'] for col in inspector.get_columns('user_settings')]
    if 'brave_search_api_key' not in user_settings_columns:
        op.add_column('user_settings', sa.Column('brave_search_api_key', sa.String(500), nullable=True))

    # Check if column exists in organization_settings
    org_settings_columns = [col['name'] for col in inspector.get_columns('organization_settings')]
    if 'brave_search_api_key' not in org_settings_columns:
        op.add_column('organization_settings', sa.Column('brave_search_api_key', sa.String(500), nullable=True))


def downgrade() -> None:
    # Remove brave_search_api_key from organization_settings table
    op.drop_column('organization_settings', 'brave_search_api_key')

    # Remove brave_search_api_key from user_settings table
    op.drop_column('user_settings', 'brave_search_api_key')
