"""Persist retryable media cleanup after content changes."""
from alembic import op
import sqlalchemy as sa

revision = "b10000000001"
down_revision = "0843806de7ed"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("media_cleanup_queue",
                    sa.Column("path", sa.String(), primary_key=True),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                              server_default=sa.func.now()))


def downgrade():
    op.drop_table("media_cleanup_queue")
