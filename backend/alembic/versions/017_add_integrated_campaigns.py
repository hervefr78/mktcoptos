"""Add integrated campaigns support with main/sub project relationships

Revision ID: 017_add_integrated_campaigns
Revises: 016_add_campaigns_table
Create Date: 2025-12-02

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '017_add_integrated_campaigns'
down_revision = '016_add_campaigns_table'
branch_labels = None
depends_on = None


def upgrade():
    # Add new fields to campaigns table
    op.add_column('campaigns', sa.Column('campaign_type', sa.String(length=50), server_default='standalone', nullable=False))
    op.add_column('campaigns', sa.Column('default_language', sa.String(length=50), server_default='auto'))
    op.create_index('idx_campaign_type', 'campaigns', ['campaign_type'])

    # Add new fields to projects table for parent/sub relationships
    op.add_column('projects', sa.Column('parent_project_id', sa.Integer(), nullable=True))
    op.add_column('projects', sa.Column('is_main_project', sa.Boolean(), server_default='0', nullable=False))
    op.add_column('projects', sa.Column('inherit_tone', sa.Boolean(), server_default='1', nullable=False))
    op.add_column('projects', sa.Column('content_type', sa.String(length=100)))

    # Add foreign key for parent_project_id (self-referential)
    op.create_index('ix_projects_parent_project_id', 'projects', ['parent_project_id'])
    op.create_foreign_key(
        'fk_projects_parent_project_id',
        'projects',
        'projects',
        ['parent_project_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # Add indexes for new project fields
    op.create_index('idx_project_main', 'projects', ['campaign_id', 'is_main_project'])

    # Add campaign_id to rag_documents for campaign-scoped filtering
    op.add_column('rag_documents', sa.Column('campaign_id', sa.Integer(), nullable=True))
    op.create_index('ix_rag_documents_campaign_id', 'rag_documents', ['campaign_id'])
    op.create_foreign_key(
        'fk_rag_documents_campaign_id',
        'rag_documents',
        'campaigns',
        ['campaign_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade():
    # Remove rag_documents changes
    op.drop_constraint('fk_rag_documents_campaign_id', 'rag_documents', type_='foreignkey')
    op.drop_index('ix_rag_documents_campaign_id', table_name='rag_documents')
    op.drop_column('rag_documents', 'campaign_id')

    # Remove project indexes and constraints
    op.drop_index('idx_project_main', table_name='projects')
    op.drop_constraint('fk_projects_parent_project_id', 'projects', type_='foreignkey')
    op.drop_index('ix_projects_parent_project_id', table_name='projects')

    # Remove project columns
    op.drop_column('projects', 'content_type')
    op.drop_column('projects', 'inherit_tone')
    op.drop_column('projects', 'is_main_project')
    op.drop_column('projects', 'parent_project_id')

    # Remove campaign columns
    op.drop_index('idx_campaign_type', table_name='campaigns')
    op.drop_column('campaigns', 'default_language')
    op.drop_column('campaigns', 'campaign_type')
