"""Add RAG documents table

Revision ID: 006_add_rag_documents
Revises: 005_add_agent_logging
Create Date: 2024-01-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_add_rag_documents'
down_revision = '005_add_agent_logging'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rag_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('project_name', sa.String(255), default='General'),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('chunks_count', sa.Integer(), default=0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('processed_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rag_documents_id', 'rag_documents', ['id'])
    op.create_index('ix_rag_documents_organization_id', 'rag_documents', ['organization_id'])
    op.create_index('ix_rag_documents_project_id', 'rag_documents', ['project_id'])
    op.create_index('ix_rag_documents_user_id', 'rag_documents', ['user_id'])
    op.create_index('ix_rag_documents_status', 'rag_documents', ['status'])
    op.create_index('idx_rag_doc_org_project', 'rag_documents', ['organization_id', 'project_id'])


def downgrade() -> None:
    op.drop_index('idx_rag_doc_org_project', table_name='rag_documents')
    op.drop_index('ix_rag_documents_status', table_name='rag_documents')
    op.drop_index('ix_rag_documents_user_id', table_name='rag_documents')
    op.drop_index('ix_rag_documents_project_id', table_name='rag_documents')
    op.drop_index('ix_rag_documents_organization_id', table_name='rag_documents')
    op.drop_index('ix_rag_documents_id', table_name='rag_documents')
    op.drop_table('rag_documents')
