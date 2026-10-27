"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-19
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

NOW = sa.text("CURRENT_TIMESTAMP")


def _ts(with_update: bool = True):
    cols = [sa.Column("created_at", sa.DateTime(), server_default=NOW, nullable=False)]
    if with_update:
        cols.append(sa.Column("updated_at", sa.DateTime(), server_default=NOW, nullable=False))
    return cols


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        *_ts(),
        sa.CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "properties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("city", sa.String(60), nullable=False),
        sa.Column("locality", sa.String(120), nullable=False),
        sa.Column("address", sa.String(255)),
        sa.Column("property_type", sa.String(30), nullable=False),
        sa.Column("listing_type", sa.String(10), nullable=False),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("area_sqft", sa.Integer(), nullable=False),
        sa.Column("bedrooms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bathrooms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("has_parking", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("furnishing", sa.String(20)),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        *_ts(),
        sa.CheckConstraint("price > 0", name="ck_properties_price_positive"),
        sa.CheckConstraint("area_sqft > 0", name="ck_properties_area_positive"),
        sa.CheckConstraint("bedrooms >= 0 AND bathrooms >= 0", name="ck_properties_rooms_nonneg"),
        sa.CheckConstraint("property_type IN ('apartment', 'independent_house', 'villa', 'plot', 'commercial')",
                           name="ck_properties_type"),
        sa.CheckConstraint("listing_type IN ('buy', 'rent')", name="ck_properties_listing_type"),
        sa.CheckConstraint("status IN ('active', 'sold', 'rented', 'inactive')", name="ck_properties_status"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    for col in ("city", "locality", "property_type", "listing_type", "status"):
        op.create_index(f"ix_properties_{col}", "properties", [col])
    op.create_index("ix_properties_search", "properties", ["status", "city", "listing_type", "price"])

    op.create_table(
        "property_amenities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.UniqueConstraint("property_id", "name", name="uq_property_amenity"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index("ix_property_amenities_property_id", "property_amenities", ["property_id"])

    op.create_table(
        "property_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("alt", sa.String(200)),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index("ix_property_images_property_id", "property_images", ["property_id"])

    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        *_ts(with_update=False),
        sa.UniqueConstraint("user_id", "property_id", name="uq_favorite_user_property"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"])
    op.create_index("ix_favorites_property_id", "favorites", ["property_id"])

    op.create_table(
        "inquiries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        *_ts(with_update=False),
        sa.CheckConstraint("status IN ('new', 'contacted', 'closed')", name="ck_inquiries_status"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index("ix_inquiries_user_id", "inquiries", ["user_id"])
    op.create_index("ix_inquiries_property_id", "inquiries", ["property_id"])

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        *_ts(),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("criteria", sa.JSON()),
        sa.Column("property_ids", sa.JSON()),
        *_ts(with_update=False),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_messages_role"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4",
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])


def downgrade() -> None:
    for table in ("chat_messages", "chat_sessions", "inquiries", "favorites", "property_images",
                  "property_amenities", "properties", "users"):
        op.drop_table(table)
