"""initial

Revision ID: 20250101000000
Revises: 
Create Date: 2025-01-01 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20250101000000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enums
    listingstatus = sa.Enum("draft", "active", "sold", "archived", name="listingstatus")
    offerstatus = sa.Enum("pending", "accepted", "rejected", "withdrawn", "expired", name="offerstatus")
    negotiationstatus = sa.Enum("open", "closed", "cancelled", name="negotiationstatus")
    swapstatus = sa.Enum("proposed", "accepted", "rejected", "completed", "cancelled", name="swapstatus")
    transactionstatus = sa.Enum("pending", "succeeded", "failed", "refunded", name="transactionstatus")

    listingstatus.create(op.get_bind(), checkfirst=True)
    offerstatus.create(op.get_bind(), checkfirst=True)
    negotiationstatus.create(op.get_bind(), checkfirst=True)
    swapstatus.create(op.get_bind(), checkfirst=True)
    transactionstatus.create(op.get_bind(), checkfirst=True)

    # users
    op.create_table(
        "users",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    # regions
    op.create_table(
        "regions",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
    )
    op.create_index(op.f("ix_regions_name"), "regions", ["name"], unique=True)
    op.create_index(op.f("ix_regions_code"), "regions", ["code"], unique=True)

    # categories
    op.create_table(
        "categories",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=True)

    # listings
    op.create_table(
        "listings",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("status", listingstatus, nullable=False, server_default="active"),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("region_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
    )
    op.create_index(op.f("ix_listings_title"), "listings", ["title"], unique=False)
    op.create_index(op.f("ix_listings_seller_id"), "listings", ["seller_id"], unique=False)

    # offers
    op.create_table(
        "offers",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", offerstatus, nullable=False, server_default="pending"),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buyer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_offers_listing_id"), "offers", ["listing_id"], unique=False)
    op.create_index(op.f("ix_offers_buyer_id"), "offers", ["buyer_id"], unique=False)

    # negotiations
    op.create_table(
        "negotiations",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("status", negotiationstatus, nullable=False, server_default="open"),
        sa.Column("last_message", sa.Text(), nullable=True),
        sa.Column("channel_id", sa.String(length=120), nullable=True),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("offer_id"),
    )
    op.create_index(op.f("ix_negotiations_channel_id"), "negotiations", ["channel_id"], unique=False)

    # swaps
    op.create_table(
        "swaps",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("status", swapstatus, nullable=False, server_default="proposed"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("channel_id", sa.String(length=120), nullable=True),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("initiator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("counterparty_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["initiator_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["counterparty_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_swaps_listing_id"), "swaps", ["listing_id"], unique=False)
    op.create_index(op.f("ix_swaps_channel_id"), "swaps", ["channel_id"], unique=False)

    # transactions
    op.create_table(
        "transactions",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("status", transactionstatus, nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="stripe"),
        sa.Column("provider_payment_intent_id", sa.String(length=120), nullable=True),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("buyer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_transactions_provider_payment_intent_id"), "transactions", ["provider_payment_intent_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_provider_payment_intent_id"), table_name="transactions")
    op.drop_table("transactions")

    op.drop_index(op.f("ix_swaps_channel_id"), table_name="swaps")
    op.drop_index(op.f("ix_swaps_listing_id"), table_name="swaps")
    op.drop_table("swaps")

    op.drop_index(op.f("ix_negotiations_channel_id"), table_name="negotiations")
    op.drop_table("negotiations")

    op.drop_index(op.f("ix_offers_buyer_id"), table_name="offers")
    op.drop_index(op.f("ix_offers_listing_id"), table_name="offers")
    op.drop_table("offers")

    op.drop_index(op.f("ix_listings_seller_id"), table_name="listings")
    op.drop_index(op.f("ix_listings_title"), table_name="listings")
    op.drop_table("listings")

    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_table("categories")

    op.drop_index(op.f("ix_regions_code"), table_name="regions")
    op.drop_index(op.f("ix_regions_name"), table_name="regions")
    op.drop_table("regions")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    # Drop enums
    sa.Enum(name="transactionstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="swapstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="negotiationstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="offerstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="listingstatus").drop(op.get_bind(), checkfirst=True)
