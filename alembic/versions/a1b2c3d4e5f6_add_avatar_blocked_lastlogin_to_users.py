"""Add avatar, is_blocked, last_login to users

Revision ID: a1b2c3d4e5f6
Revises: 5dd6b9efb16e
Create Date: 2026-07-01 14:57:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '5dd6b9efb16e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('avatar', sa.String(), nullable=True))
    op.add_column('users', sa.Column('is_blocked', sa.Boolean(), nullable=True, server_default=sa.text('false')))
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'is_blocked')
    op.drop_column('users', 'avatar')
