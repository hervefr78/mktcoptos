"""Add projects array to generated_images

Revision ID: 010_image_projects
Revises: 009_projects_array
Create Date: 2025-11-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010_image_projects'
down_revision = '009_projects_array'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add projects JSON column to generated_images table
    op.add_column('generated_images', sa.Column('projects', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove projects column
    op.drop_column('generated_images', 'projects')
