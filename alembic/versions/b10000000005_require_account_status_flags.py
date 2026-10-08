"""Remove ambiguous NULL account status flags."""
from alembic import op
import sqlalchemy as sa

revision = "b10000000005"
down_revision = "b10000000004"
branch_labels = None
depends_on = None


def upgrade():
    for column in ("is_active", "is_blocked", "is_superuser"):
        op.execute(sa.text(f"UPDATE users SET {column} = false WHERE {column} IS NULL"))
        op.alter_column("users", column, existing_type=sa.Boolean(), nullable=False)


def downgrade():
    for column in ("is_active", "is_blocked", "is_superuser"):
        op.alter_column("users", column, existing_type=sa.Boolean(), nullable=True)
