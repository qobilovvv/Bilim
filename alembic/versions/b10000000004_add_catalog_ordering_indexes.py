"""Indexes for catalog and moderation list ordering."""

from alembic import op

revision = "b10000000004"
down_revision = "b10000000003"
branch_labels = None
depends_on = None

INDEXES = [
    ("courses", "ix_courses_teacher_created", "teacher_id", "created_at", "id"),
    ("courses", "ix_courses_category_created", "category_id", "created_at", "id"),
    ("courses", "ix_courses_created", "created_at", "id"),
    ("users", "ix_users_type_created", "type", "created_at", "id"),
]


def upgrade():
    for table, name, *columns in INDEXES:
        op.create_index(name, table, columns)


def downgrade():
    for table, name, *columns in reversed(INDEXES):
        op.drop_index(name, table_name=table)
