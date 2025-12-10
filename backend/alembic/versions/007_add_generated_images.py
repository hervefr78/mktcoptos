"""Add generated_images table for image gallery

Revision ID: 007_add_generated_images
Revises: 006_add_rag_documents
Create Date: 2024-01-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007_add_generated_images'
down_revision = '006_add_rag_documents'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'generated_images',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('pipeline_execution_id', sa.Integer(), nullable=True),

        # Image metadata
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('negative_prompt', sa.Text(), nullable=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(100), server_default='image/png'),

        # Dimensions
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),

        # Generation details
        sa.Column('source', sa.String(50), server_default='openai'),
        sa.Column('openai_model', sa.String(100), nullable=True),
        sa.Column('sdxl_model', sa.String(255), nullable=True),
        sa.Column('quality', sa.String(20), nullable=True),
        sa.Column('style', sa.String(20), nullable=True),

        # Generation metrics
        sa.Column('generation_time_seconds', sa.Integer(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()')),

        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['pipeline_execution_id'], ['pipeline_executions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_generated_images_id', 'generated_images', ['id'])
    op.create_index('ix_generated_images_user_id', 'generated_images', ['user_id'])
    op.create_index('ix_generated_images_project_id', 'generated_images', ['project_id'])
    op.create_index('ix_generated_images_pipeline', 'generated_images', ['pipeline_execution_id'])
    op.create_index('ix_generated_images_source', 'generated_images', ['source'])
    op.create_index('ix_generated_images_created_at', 'generated_images', ['created_at'])
    op.create_index('idx_image_user_created', 'generated_images', ['user_id', 'created_at'])
    op.create_index('idx_image_source_created', 'generated_images', ['source', 'created_at'])
    op.create_index('idx_image_pipeline', 'generated_images', ['pipeline_execution_id'])


def downgrade() -> None:
    op.drop_index('idx_image_pipeline', table_name='generated_images')
    op.drop_index('idx_image_source_created', table_name='generated_images')
    op.drop_index('idx_image_user_created', table_name='generated_images')
    op.drop_index('ix_generated_images_created_at', table_name='generated_images')
    op.drop_index('ix_generated_images_source', table_name='generated_images')
    op.drop_index('ix_generated_images_pipeline', table_name='generated_images')
    op.drop_index('ix_generated_images_project_id', table_name='generated_images')
    op.drop_index('ix_generated_images_user_id', table_name='generated_images')
    op.drop_index('ix_generated_images_id', table_name='generated_images')
    op.drop_table('generated_images')
