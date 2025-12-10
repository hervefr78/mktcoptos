"""Add collection field to RAG documents

Revision ID: 008_collection_field
Revises: 007_add_generated_images
Create Date: 2024-11-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_collection_field'
down_revision = '007_add_generated_images'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add collection column to rag_documents table
    op.add_column('rag_documents', sa.Column('collection', sa.String(50), nullable=False, server_default='knowledge_base'))

    # Create index on collection field
    op.create_index('ix_rag_documents_collection', 'rag_documents', ['collection'])


def downgrade() -> None:
    # Drop index first
    op.drop_index('ix_rag_documents_collection', table_name='rag_documents')

    # Drop collection column
    op.drop_column('rag_documents', 'collection')
