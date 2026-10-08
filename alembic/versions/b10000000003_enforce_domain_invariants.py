"""Normalize phone identities and enforce domain invariants.

Existing conflicting phone identities or invalid domain data must be corrected
before this migration. It fails atomically rather than silently changing prices/scores.
"""

import sqlalchemy as sa

from alembic import op

revision = "b10000000003"
down_revision = "b10000000002"
branch_labels = None
depends_on = None

CHECKS = [
    ("users", "ck_users_role", "type IN ('admin', 'author', 'user', 'seller')"),
    ("users", "ck_users_first_name", "length(btrim(first_name)) BETWEEN 1 AND 200"),
    ("users", "ck_users_auth_version", "auth_version >= 0"),
    ("users", "ck_users_phone", "phone IS NULL OR phone ~ '^[1-9][0-9]{7,14}$'"),
    (
        "categories",
        "ck_categories_hierarchy",
        "(parent_id IS NULL AND level = 1) OR (parent_id IS NOT NULL AND level = 2 AND parent_id <> id)",
    ),
    ("courses", "ck_courses_price", "price >= 0"),
    ("courses", "ck_courses_type", "type IN ('foundation', 'middle', 'senior')"),
    ("modules", "ck_modules_order", "order_index >= 0"),
    ("lessons", "ck_lessons_order", "order_index >= 0"),
    ("password_reset_codes", "ck_reset_attempts", "attempts >= 0"),
    ("homeworks", "ck_homeworks_type", "type IN ('test', 'text', 'file', 'none')"),
    (
        "test_homeworks",
        "ck_test_homeworks_values",
        "pass_ball >= 0 AND (timer_minutes IS NULL OR timer_minutes > 0)",
    ),
    ("test_questions", "ck_test_questions_values", "ball >= 0 AND order_index >= 0"),
    ("test_question_options", "ck_test_options_order", "order_index >= 0"),
    (
        "text_homeworks",
        "ck_text_homeworks_values",
        "deadline_days BETWEEN 2 AND 8 AND pass_ball BETWEEN 0 AND 100 AND min_words > 0",
    ),
    (
        "file_homeworks",
        "ck_file_homeworks_values",
        "deadline_days BETWEEN 2 AND 8 AND max_file_size_mb BETWEEN 1 AND 100",
    ),
]


def upgrade():
    op.execute(
        "UPDATE users SET phone = regexp_replace(phone, '[^0-9]', '', 'g') WHERE phone IS NOT NULL"
    )
    op.execute("UPDATE password_reset_codes SET phone = regexp_replace(phone, '[^0-9]', '', 'g')")
    op.alter_column("courses", "is_active", server_default=sa.text("false"))
    for table, name, expression in CHECKS:
        op.create_check_constraint(name, table, expression)


def downgrade():
    for table, name, expression in reversed(CHECKS):
        op.drop_constraint(name, table, type_="check")
    op.alter_column("courses", "is_active", server_default=None)
