"""Add campaigns table and link projects to campaigns

Revision ID: 016_add_campaigns_table
Revises: 015_add_categories_table
Create Date: 2025-12-15

"""
from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision = '016_add_campaigns_table'
down_revision = '015_add_categories_table'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'campaigns',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('category_id', sa.Integer(), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('model', sa.String(length=255)),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_campaign_org_name', 'campaigns', ['organization_id', 'name'])

    op.add_column('projects', sa.Column('campaign_id', sa.Integer(), nullable=True))
    op.create_index('ix_projects_campaign_id', 'projects', ['campaign_id'])
    op.create_foreign_key(
        'fk_projects_campaign_id',
        'projects',
        'campaigns',
        ['campaign_id'],
        ['id'],
        ondelete='SET NULL',
    )

    connection = op.get_bind()
    metadata = sa.MetaData()
    metadata.bind = connection

    campaigns_table = sa.Table('campaigns', metadata, autoload_with=connection)
    projects_table = sa.Table('projects', metadata, autoload_with=connection)

    project_rows = connection.execute(sa.select(projects_table)).fetchall()

    for row in project_rows:
        brand_voice = row.brand_voice
        if isinstance(brand_voice, str):
            try:
                brand_voice = json.loads(brand_voice)
            except Exception:
                brand_voice = {}
        model_used = None
        if isinstance(brand_voice, dict):
            model_used = brand_voice.get('model')

        insert_result = connection.execute(
            campaigns_table.insert().values(
                organization_id=row.organization_id,
                category_id=row.category_id,
                name=row.name,
                description=row.description,
                model=model_used,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )
        campaign_id = insert_result.inserted_primary_key[0] if insert_result.inserted_primary_key else None
        if campaign_id is not None:
            connection.execute(
                projects_table.update()
                .where(projects_table.c.id == row.id)
                .values(campaign_id=campaign_id)
            )


def downgrade():
    op.drop_constraint('fk_projects_campaign_id', 'projects', type_='foreignkey')
    op.drop_index('ix_projects_campaign_id', table_name='projects')
    op.drop_column('projects', 'campaign_id')

    op.drop_index('ix_campaigns_category_id', table_name='campaigns')
    op.drop_index('idx_campaign_org_name', table_name='campaigns')
    op.drop_table('campaigns')
