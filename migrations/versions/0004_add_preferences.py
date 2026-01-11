"""add preferences json to users

Revision ID: 0004_add_preferences
Revises: 0003_add_locking_fields
Create Date: 2026-01-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004_add_preferences'
down_revision = '0003_add_locking_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('preferences', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('users', 'preferences')
