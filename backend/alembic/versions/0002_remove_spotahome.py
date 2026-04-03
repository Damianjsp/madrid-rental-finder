"""Remove Spotahome portal data

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-03 21:27:00
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    -- Spotahome focuses on short-term / temporary rentals, so remove its data from the
    -- long-term apartment search dataset before deleting the portal registration itself.
    DELETE FROM mrf.listing_images
    WHERE listing_id IN (
        SELECT l.id
        FROM mrf.listings AS l
        JOIN mrf.portals AS p ON p.id = l.portal_id
        WHERE p.key = 'spotahome'
    );

    DELETE FROM mrf.listings
    WHERE portal_id IN (
        SELECT id
        FROM mrf.portals
        WHERE key = 'spotahome'
    );

    DELETE FROM mrf.scraper_runs
    WHERE portal_id IN (
        SELECT id
        FROM mrf.portals
        WHERE key = 'spotahome'
    );

    DELETE FROM mrf.portal_parsing_versions
    WHERE portal_id IN (
        SELECT id
        FROM mrf.portals
        WHERE key = 'spotahome'
    );

    DELETE FROM mrf.portals
    WHERE key = 'spotahome';
    """)


def downgrade() -> None:
    op.execute("""
    INSERT INTO mrf.portals (key, name, tier, base_url)
    SELECT 'spotahome', 'Spotahome', 1, 'https://www.spotahome.com'
    WHERE NOT EXISTS (
        SELECT 1 FROM mrf.portals WHERE key = 'spotahome'
    );
    """)
