"""Add ComfyUI settings and hybrid strategy fields

Revision ID: 002_add_comfyui
Revises: 001_add_settings
Create Date: 2025-11-17 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_comfyui'
down_revision = '001_add_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add ComfyUI settings to user_settings table
    op.add_column('user_settings', sa.Column('comfyui_base_url', sa.String(255), server_default='http://localhost:8188'))
    op.add_column('user_settings', sa.Column('sdxl_model', sa.String(255), server_default='sd_xl_turbo_1.0_fp16.safetensors'))
    op.add_column('user_settings', sa.Column('sdxl_steps', sa.Integer(), server_default='6'))
    op.add_column('user_settings', sa.Column('sdxl_cfg_scale', sa.DECIMAL(3, 1), server_default='1.0'))
    op.add_column('user_settings', sa.Column('sdxl_sampler', sa.String(50), server_default='euler_ancestral'))

    # Add hybrid image strategy fields
    op.add_column('user_settings', sa.Column('use_gpt_image_for_posts', sa.Boolean(), server_default='true'))
    op.add_column('user_settings', sa.Column('use_comfyui_for_blogs', sa.Boolean(), server_default='true'))


def downgrade() -> None:
    # Remove hybrid strategy fields
    op.drop_column('user_settings', 'use_comfyui_for_blogs')
    op.drop_column('user_settings', 'use_gpt_image_for_posts')

    # Remove ComfyUI settings
    op.drop_column('user_settings', 'sdxl_sampler')
    op.drop_column('user_settings', 'sdxl_cfg_scale')
    op.drop_column('user_settings', 'sdxl_steps')
    op.drop_column('user_settings', 'sdxl_model')
    op.drop_column('user_settings', 'comfyui_base_url')
