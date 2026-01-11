"""Add signup controls, captcha, password policy, and email verification.

Revision ID: 20260111_add_signup_password_policy
Revises: 20260110_add_session_timeout_and_last_seen
Create Date: 2026-01-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = "20260111_add_signup_password_policy"
down_revision = "20260110_add_session_timeout_and_last_seen"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "system_preferences" not in inspector.get_table_names():
        raise RuntimeError("Missing required table 'system_preferences'.")

    prefs_cols = {col["name"] for col in inspector.get_columns("system_preferences")}
    with op.batch_alter_table("system_preferences") as batch_op:
        if "allow_self_signup" not in prefs_cols:
            batch_op.add_column(
                sa.Column("allow_self_signup", sa.Boolean(), nullable=False, server_default=text("0"))
            )
        if "require_signup_verification" not in prefs_cols:
            batch_op.add_column(
                sa.Column("require_signup_verification", sa.Boolean(), nullable=False, server_default=text("0"))
            )
        if "require_signup_captcha" not in prefs_cols:
            batch_op.add_column(
                sa.Column("require_signup_captcha", sa.Boolean(), nullable=False, server_default=text("1"))
            )
        if "signup_captcha_provider" not in prefs_cols:
            batch_op.add_column(sa.Column("signup_captcha_provider", sa.String(length=50), nullable=True))
        if "signup_captcha_site_key" not in prefs_cols:
            batch_op.add_column(sa.Column("signup_captcha_site_key", sa.String(length=255), nullable=True))
        if "password_min_length" not in prefs_cols:
            batch_op.add_column(
                sa.Column("password_min_length", sa.Integer(), nullable=False, server_default=text("12"))
            )
        if "password_require_uppercase" not in prefs_cols:
            batch_op.add_column(
                sa.Column("password_require_uppercase", sa.Boolean(), nullable=False, server_default=text("1"))
            )
        if "password_require_lowercase" not in prefs_cols:
            batch_op.add_column(
                sa.Column("password_require_lowercase", sa.Boolean(), nullable=False, server_default=text("1"))
            )
        if "password_require_number" not in prefs_cols:
            batch_op.add_column(
                sa.Column("password_require_number", sa.Boolean(), nullable=False, server_default=text("1"))
            )
        if "password_require_special" not in prefs_cols:
            batch_op.add_column(
                sa.Column("password_require_special", sa.Boolean(), nullable=False, server_default=text("0"))
            )

    if "users" not in inspector.get_table_names():
        raise RuntimeError("Missing required table 'users'.")

    user_cols = {col["name"] for col in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "is_email_verified" not in user_cols:
            batch_op.add_column(
                sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=text("0"))
            )

    # Initialize defaults for existing row
    op.execute(
        text(
            "UPDATE system_preferences SET allow_self_signup = 0, "
            "require_signup_verification = 0, require_signup_captcha = 1, "
            "signup_captcha_provider = COALESCE(signup_captcha_provider, 'turnstile'), "
            "password_min_length = COALESCE(password_min_length, 12), "
            "password_require_uppercase = COALESCE(password_require_uppercase, 1), "
            "password_require_lowercase = COALESCE(password_require_lowercase, 1), "
            "password_require_number = COALESCE(password_require_number, 1), "
            "password_require_special = COALESCE(password_require_special, 0)"
        )
    )

    op.execute(
        text(
            "UPDATE users SET is_email_verified = 0 WHERE is_email_verified IS NULL"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "system_preferences" in inspector.get_table_names():
        prefs_cols = {col["name"] for col in inspector.get_columns("system_preferences")}
        with op.batch_alter_table("system_preferences") as batch_op:
            if "password_require_special" in prefs_cols:
                batch_op.drop_column("password_require_special")
            if "password_require_number" in prefs_cols:
                batch_op.drop_column("password_require_number")
            if "password_require_lowercase" in prefs_cols:
                batch_op.drop_column("password_require_lowercase")
            if "password_require_uppercase" in prefs_cols:
                batch_op.drop_column("password_require_uppercase")
            if "password_min_length" in prefs_cols:
                batch_op.drop_column("password_min_length")
            if "signup_captcha_site_key" in prefs_cols:
                batch_op.drop_column("signup_captcha_site_key")
            if "signup_captcha_provider" in prefs_cols:
                batch_op.drop_column("signup_captcha_provider")
            if "require_signup_captcha" in prefs_cols:
                batch_op.drop_column("require_signup_captcha")
            if "require_signup_verification" in prefs_cols:
                batch_op.drop_column("require_signup_verification")
            if "allow_self_signup" in prefs_cols:
                batch_op.drop_column("allow_self_signup")

    if "users" in inspector.get_table_names():
        user_cols = {col["name"] for col in inspector.get_columns("users")}
        with op.batch_alter_table("users") as batch_op:
            if "is_email_verified" in user_cols:
                batch_op.drop_column("is_email_verified")
