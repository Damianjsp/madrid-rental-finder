"""Initial schema — full mrf DDL

Revision ID: 0001
Revises: 
Create Date: 2026-03-10 00:00:00
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- Schema + extensions ----
    op.execute("CREATE SCHEMA IF NOT EXISTS mrf")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")

    # ---- portals ----
    op.create_table(
        "portals",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("tier", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("base_url", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
        schema="mrf",
    )

    # ---- scraper_runs ----
    op.create_table(
        "scraper_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("portal_id", sa.SmallInteger(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("listings_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("listings_new", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("listings_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "meta",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.ForeignKeyConstraint(["portal_id"], ["mrf.portals.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="mrf",
    )

    # ---- districts ----
    op.create_table(
        "districts",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=False, server_default="Madrid"),
        sa.Column("zone", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="mrf",
    )

    # ---- neighborhoods ----
    op.create_table(
        "neighborhoods",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("district_id", sa.SmallInteger()),
        sa.Column("municipality", sa.Text(), nullable=False, server_default="Madrid"),
        sa.Column("zone", sa.Text()),
        sa.Column("safety_score", sa.SmallInteger()),
        sa.Column("transport_score", sa.SmallInteger()),
        sa.Column("commute_to_sol_min", sa.SmallInteger()),
        sa.Column("commute_to_sol_max", sa.SmallInteger()),
        sa.Column("commute_to_atocha_min", sa.SmallInteger()),
        sa.Column("commute_to_atocha_max", sa.SmallInteger()),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["district_id"], ["mrf.districts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("municipality", "name", name="uq_neighborhoods_municipality_name"),
        schema="mrf",
    )

    # ---- transport_nodes ----
    op.create_table(
        "transport_nodes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("lines", postgresql.ARRAY(sa.Text())),
        sa.Column("lat", sa.Double()),
        sa.Column("lon", sa.Double()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind", "name", name="uq_transport_nodes_kind_name"),
        schema="mrf",
    )

    # ---- neighborhood_transport_nodes ----
    op.create_table(
        "neighborhood_transport_nodes",
        sa.Column("neighborhood_id", sa.BigInteger(), nullable=False),
        sa.Column("transport_node_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["neighborhood_id"],
            ["mrf.neighborhoods.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["transport_node_id"],
            ["mrf.transport_nodes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("neighborhood_id", "transport_node_id"),
        schema="mrf",
    )

    # ---- cost_benchmarks ----
    op.create_table(
        "cost_benchmarks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("scope_kind", sa.Text(), nullable=False),
        sa.Column("scope_name", sa.Text(), nullable=False),
        sa.Column("avg_rent_1bed", sa.Integer()),
        sa.Column("avg_rent_2bed", sa.Integer()),
        sa.Column("avg_rent_3bed", sa.Integer()),
        sa.Column("avg_house", sa.Integer()),
        sa.Column("avg_chalet", sa.Integer()),
        sa.Column("observed_at", sa.Date(), nullable=False),
        sa.Column("source", sa.Text()),
        sa.Column(
            "meta",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope_kind", "scope_name", "observed_at", name="uq_cost_benchmarks"),
        schema="mrf",
    )

    # ---- listings ----
    op.create_table(
        "listings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("portal_id", sa.SmallInteger(), nullable=False),
        sa.Column("source_listing_id", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("price_eur", sa.Integer()),
        sa.Column("deposit_eur", sa.Integer()),
        sa.Column("expenses_included", sa.Boolean()),
        sa.Column("bedrooms", sa.SmallInteger()),
        sa.Column("bathrooms", sa.SmallInteger()),
        sa.Column("size_m2", sa.Numeric(6, 2)),
        sa.Column("property_type", sa.Text()),
        sa.Column("furnished", sa.Boolean()),
        sa.Column("elevator", sa.Boolean()),
        sa.Column("parking", sa.Boolean()),
        sa.Column("address_raw", sa.Text()),
        sa.Column("neighborhood_raw", sa.Text()),
        sa.Column("district_raw", sa.Text()),
        sa.Column("municipality_raw", sa.Text()),
        sa.Column("neighborhood_id", sa.BigInteger()),
        sa.Column("district_id", sa.SmallInteger()),
        sa.Column("lat", sa.Double()),
        sa.Column("lon", sa.Double()),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("scraper_run_id", sa.BigInteger()),
        sa.Column(
            "raw",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("tsv", postgresql.TSVECTOR()),
        sa.ForeignKeyConstraint(["district_id"], ["mrf.districts.id"]),
        sa.ForeignKeyConstraint(["neighborhood_id"], ["mrf.neighborhoods.id"]),
        sa.ForeignKeyConstraint(["portal_id"], ["mrf.portals.id"]),
        sa.ForeignKeyConstraint(["scraper_run_id"], ["mrf.scraper_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "portal_id", "source_listing_id", name="uq_listings_portal_source"
        ),
        schema="mrf",
    )

    op.create_index("idx_listings_active", "listings", ["is_active"], schema="mrf")
    op.create_index("idx_listings_price", "listings", ["price_eur"], schema="mrf")
    op.create_index("idx_listings_bedrooms", "listings", ["bedrooms"], schema="mrf")
    op.create_index("idx_listings_size", "listings", ["size_m2"], schema="mrf")
    op.create_index("idx_listings_last_seen", "listings", ["last_seen_at"], schema="mrf")
    op.create_index("idx_listings_neighborhood", "listings", ["neighborhood_id"], schema="mrf")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_listings_tsv ON mrf.listings USING GIN(tsv)"
    )

    # ---- listing_images ----
    op.create_table(
        "listing_images",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("listing_id", sa.BigInteger(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("position", sa.SmallInteger()),
        sa.ForeignKeyConstraint(
            ["listing_id"], ["mrf.listings.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("listing_id", "url", name="uq_listing_images"),
        schema="mrf",
    )

    # ---- portal_parsing_versions ----
    op.create_table(
        "portal_parsing_versions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("portal_id", sa.SmallInteger(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column(
            "deployed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("notes", sa.Text()),
        sa.ForeignKeyConstraint(["portal_id"], ["mrf.portals.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="mrf",
    )

    # ---- TSV trigger ----
    op.execute("""
        CREATE OR REPLACE FUNCTION mrf.listings_tsv_update() RETURNS trigger AS $$
        BEGIN
          NEW.tsv :=
            setweight(to_tsvector('spanish', unaccent(coalesce(NEW.title,''))), 'A') ||
            setweight(to_tsvector('spanish', unaccent(coalesce(NEW.description,''))), 'B') ||
            setweight(to_tsvector('spanish', unaccent(coalesce(NEW.neighborhood_raw,''))), 'C') ||
            setweight(to_tsvector('spanish', unaccent(coalesce(NEW.district_raw,''))), 'C');
          RETURN NEW;
        END $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS trg_listings_tsv_update ON mrf.listings;
        CREATE TRIGGER trg_listings_tsv_update
        BEFORE INSERT OR UPDATE OF title, description, neighborhood_raw, district_raw
        ON mrf.listings
        FOR EACH ROW EXECUTE FUNCTION mrf.listings_tsv_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_listings_tsv_update ON mrf.listings")
    op.execute("DROP FUNCTION IF EXISTS mrf.listings_tsv_update()")
    op.drop_table("portal_parsing_versions", schema="mrf")
    op.drop_table("listing_images", schema="mrf")
    op.drop_table("listings", schema="mrf")
    op.drop_table("cost_benchmarks", schema="mrf")
    op.drop_table("neighborhood_transport_nodes", schema="mrf")
    op.drop_table("transport_nodes", schema="mrf")
    op.drop_table("neighborhoods", schema="mrf")
    op.drop_table("districts", schema="mrf")
    op.drop_table("scraper_runs", schema="mrf")
    op.drop_table("portals", schema="mrf")
    op.execute("DROP SCHEMA IF EXISTS mrf CASCADE")
