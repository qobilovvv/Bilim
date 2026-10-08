"""Revocable sessions and password reset abuse controls."""
from alembic import op
import sqlalchemy as sa

revision = "b10000000002"
down_revision = "b10000000001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("password_reset_codes", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
    # Existing plaintext challenges cannot be safely used after digest migration.
    op.execute("UPDATE password_reset_codes SET expires_at = now()")
    op.alter_column("password_reset_codes", "code", type_=sa.String(64))
    op.create_table("auth_sessions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_digest", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_table("auth_rate_limits",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_auth_rate_limits_expires_at", "auth_rate_limits", ["expires_at"])


def downgrade():
    op.drop_table("auth_rate_limits")
    op.drop_table("auth_sessions")
    op.drop_column("password_reset_codes", "attempts")
    op.drop_column("users", "auth_version")
