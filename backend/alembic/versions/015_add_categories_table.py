"""Add categories table and project category relation

Revision ID: 015_add_categories_table
Revises: 014_add_language_to_projects
Create Date: 2025-12-02

"""
from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision = '015_add_categories_table'
down_revision = '014_add_language_to_projects'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_category_org_name', 'categories', ['organization_id', 'name'], unique=True)

    op.add_column('projects', sa.Column('category_id', sa.Integer(), nullable=True))
    op.create_index('ix_projects_category_id', 'projects', ['category_id'])
    op.create_foreign_key(
        'fk_projects_category_id',
        'projects',
        'categories',
        ['category_id'],
        ['id'],
        ondelete='SET NULL',
    )

    connection = op.get_bind()

    existing_categories = {}

    settings_rows = connection.execute(sa.text("SELECT organization_id, brand_voice FROM organization_settings"))
    for row in settings_rows:
        brand_voice = row.brand_voice
        if isinstance(brand_voice, str):
            try:
                brand_voice = json.loads(brand_voice)
            except Exception:
                brand_voice = {}
        if not brand_voice:
            continue
        categories = brand_voice.get('categories') or []
        for name in categories:
            if not isinstance(name, str):
                continue
            cleaned = name.strip()
            if not cleaned:
                continue
            key = (row.organization_id, cleaned.lower())
            if key in existing_categories:
                continue
            result = connection.execute(
                sa.text(
                    "INSERT INTO categories (organization_id, name) VALUES (:org_id, :name) RETURNING id"
                ),
                {"org_id": row.organization_id, "name": cleaned},
            )
            new_id = result.scalar_one()
            existing_categories[key] = new_id

    project_rows = connection.execute(sa.text("SELECT id, organization_id, brand_voice FROM projects"))
    for row in project_rows:
        brand_voice = row.brand_voice
        if isinstance(brand_voice, str):
            try:
                brand_voice = json.loads(brand_voice)
            except Exception:
                brand_voice = {}
        category_name = None
        if isinstance(brand_voice, dict):
            category_name = brand_voice.get('category')
        if not category_name or not isinstance(category_name, str):
            continue
        cleaned = category_name.strip()
        if not cleaned:
            continue
        key = (row.organization_id, cleaned.lower())
        category_id = existing_categories.get(key)
        if category_id is None:
            result = connection.execute(
                sa.text(
                    "INSERT INTO categories (organization_id, name) VALUES (:org_id, :name) RETURNING id"
                ),
                {"org_id": row.organization_id, "name": cleaned},
            )
            category_id = result.scalar_one()
            existing_categories[key] = category_id
        connection.execute(
            sa.text("UPDATE projects SET category_id = :cid WHERE id = :pid"),
            {"cid": category_id, "pid": row.id},
        )


def downgrade():
    op.drop_constraint('fk_projects_category_id', 'projects', type_='foreignkey')
    op.drop_index('ix_projects_category_id', table_name='projects')
    op.drop_column('projects', 'category_id')

    op.drop_index('idx_category_org_name', table_name='categories')
    op.drop_table('categories')
