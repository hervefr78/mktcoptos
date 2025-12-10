"""Add projects array to RAG documents

Revision ID: 009_projects_array
Revises: 008_collection_field
Create Date: 2024-11-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_projects_array'
down_revision = '008_collection_field'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add projects JSON column to rag_documents table
    op.add_column('rag_documents', sa.Column('projects', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Drop projects column
    op.drop_column('rag_documents', 'projects')
