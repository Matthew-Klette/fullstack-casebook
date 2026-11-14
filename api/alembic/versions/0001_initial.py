"""initial schema

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
    )
    op.create_table(
        "memberships",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("team_id", sa.Integer, sa.ForeignKey("teams.id"), primary_key=True),
        sa.Column("role", sa.String(20), nullable=False),
    )
    op.create_table(
        "shifts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("team_id", sa.Integer, sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("notes", sa.String(2000), nullable=False),
        sa.Column("starts_at", sa.DateTime, nullable=False),
        sa.Column("assignee_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_shifts_team_starts", "shifts", ["team_id", "starts_at"])
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_table(
        "payroll_exports",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("team_id", sa.Integer, sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("shift_count", sa.Integer, nullable=False),
        sa.Column("remote_ref", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_payroll_exports_team_id", "payroll_exports", ["team_id"])


def downgrade() -> None:
    for table in ("payroll_exports", "refresh_tokens", "shifts", "memberships", "users", "teams"):
        op.drop_table(table)
