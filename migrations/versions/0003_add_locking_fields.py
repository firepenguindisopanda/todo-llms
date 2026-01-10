"""add locking fields to users

Revision ID: 0003_add_locking_fields
Revises: 0002_create_refresh_tokens
Create Date: 2026-01-09 00:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_add_locking_fields'
down_revision = '0002_create_refresh_tokens'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
