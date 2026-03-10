"""SQLAlchemy ORM models — mirrors the mrf schema exactly."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Double,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    ARRAY,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Reference tables
# ---------------------------------------------------------------------------


class Portal(Base):
    __tablename__ = "portals"
    __table_args__ = {"schema": "mrf"}

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    tier: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    base_url: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    runs: Mapped[List["ScraperRun"]] = relationship("ScraperRun", back_populates="portal")
    listings: Mapped[List["Listing"]] = relationship("Listing", back_populates="portal")


class ScraperRun(Base):
    __tablename__ = "scraper_runs"
    __table_args__ = {"schema": "mrf"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    portal_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("mrf.portals.id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="running")
    listings_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    listings_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    listings_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    portal: Mapped["Portal"] = relationship("Portal", back_populates="runs")


class District(Base):
    __tablename__ = "districts"
    __table_args__ = {"schema": "mrf"}

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    city: Mapped[str] = mapped_column(Text, nullable=False, default="Madrid")
    zone: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    neighborhoods: Mapped[List["Neighborhood"]] = relationship(
        "Neighborhood", back_populates="district"
    )
    listings: Mapped[List["Listing"]] = relationship("Listing", back_populates="district")


class Neighborhood(Base):
    __tablename__ = "neighborhoods"
    __table_args__ = (
        UniqueConstraint("municipality", "name", name="uq_neighborhoods_municipality_name"),
        {"schema": "mrf"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    district_id: Mapped[Optional[int]] = mapped_column(
        SmallInteger, ForeignKey("mrf.districts.id")
    )
    municipality: Mapped[str] = mapped_column(Text, nullable=False, default="Madrid")
    zone: Mapped[Optional[str]] = mapped_column(Text)
    safety_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    transport_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    commute_to_sol_min: Mapped[Optional[int]] = mapped_column(SmallInteger)
    commute_to_sol_max: Mapped[Optional[int]] = mapped_column(SmallInteger)
    commute_to_atocha_min: Mapped[Optional[int]] = mapped_column(SmallInteger)
    commute_to_atocha_max: Mapped[Optional[int]] = mapped_column(SmallInteger)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    district: Mapped[Optional["District"]] = relationship(
        "District", back_populates="neighborhoods"
    )
    listings: Mapped[List["Listing"]] = relationship("Listing", back_populates="neighborhood")
    transport_nodes: Mapped[List["TransportNode"]] = relationship(
        "TransportNode",
        secondary="mrf.neighborhood_transport_nodes",
        back_populates="neighborhoods",
    )


class TransportNode(Base):
    __tablename__ = "transport_nodes"
    __table_args__ = (
        UniqueConstraint("kind", "name", name="uq_transport_nodes_kind_name"),
        {"schema": "mrf"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    lines: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    lat: Mapped[Optional[float]] = mapped_column(Double)
    lon: Mapped[Optional[float]] = mapped_column(Double)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    neighborhoods: Mapped[List["Neighborhood"]] = relationship(
        "Neighborhood",
        secondary="mrf.neighborhood_transport_nodes",
        back_populates="transport_nodes",
    )


class NeighborhoodTransportNode(Base):
    __tablename__ = "neighborhood_transport_nodes"
    __table_args__ = {"schema": "mrf"}

    neighborhood_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("mrf.neighborhoods.id", ondelete="CASCADE"), primary_key=True
    )
    transport_node_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("mrf.transport_nodes.id", ondelete="CASCADE"), primary_key=True
    )


class CostBenchmark(Base):
    __tablename__ = "cost_benchmarks"
    __table_args__ = (
        UniqueConstraint(
            "scope_kind", "scope_name", "observed_at", name="uq_cost_benchmarks"
        ),
        {"schema": "mrf"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scope_kind: Mapped[str] = mapped_column(Text, nullable=False)
    scope_name: Mapped[str] = mapped_column(Text, nullable=False)
    avg_rent_1bed: Mapped[Optional[int]] = mapped_column(Integer)
    avg_rent_2bed: Mapped[Optional[int]] = mapped_column(Integer)
    avg_rent_3bed: Mapped[Optional[int]] = mapped_column(Integer)
    avg_house: Mapped[Optional[int]] = mapped_column(Integer)
    avg_chalet: Mapped[Optional[int]] = mapped_column(Integer)
    observed_at: Mapped[datetime] = mapped_column(Date, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("portal_id", "source_listing_id", name="uq_listings_portal_source"),
        Index("idx_listings_active", "is_active"),
        Index("idx_listings_price", "price_eur"),
        Index("idx_listings_bedrooms", "bedrooms"),
        Index("idx_listings_size", "size_m2"),
        Index("idx_listings_last_seen", "last_seen_at"),
        Index("idx_listings_neighborhood", "neighborhood_id"),
        {"schema": "mrf"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    portal_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("mrf.portals.id"), nullable=False
    )
    source_listing_id: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)

    title: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)

    price_eur: Mapped[Optional[int]] = mapped_column(Integer)
    deposit_eur: Mapped[Optional[int]] = mapped_column(Integer)
    expenses_included: Mapped[Optional[bool]] = mapped_column(Boolean)

    bedrooms: Mapped[Optional[int]] = mapped_column(SmallInteger)
    bathrooms: Mapped[Optional[int]] = mapped_column(SmallInteger)
    size_m2: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))

    property_type: Mapped[Optional[str]] = mapped_column(Text)
    furnished: Mapped[Optional[bool]] = mapped_column(Boolean)
    elevator: Mapped[Optional[bool]] = mapped_column(Boolean)
    parking: Mapped[Optional[bool]] = mapped_column(Boolean)

    address_raw: Mapped[Optional[str]] = mapped_column(Text)
    neighborhood_raw: Mapped[Optional[str]] = mapped_column(Text)
    district_raw: Mapped[Optional[str]] = mapped_column(Text)
    municipality_raw: Mapped[Optional[str]] = mapped_column(Text)

    neighborhood_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("mrf.neighborhoods.id")
    )
    district_id: Mapped[Optional[int]] = mapped_column(
        SmallInteger, ForeignKey("mrf.districts.id")
    )

    lat: Mapped[Optional[float]] = mapped_column(Double)
    lon: Mapped[Optional[float]] = mapped_column(Double)

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    scraper_run_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("mrf.scraper_runs.id")
    )
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    tsv: Mapped[Optional[str]] = mapped_column(TSVECTOR)

    portal: Mapped["Portal"] = relationship("Portal", back_populates="listings")
    neighborhood: Mapped[Optional["Neighborhood"]] = relationship(
        "Neighborhood", back_populates="listings"
    )
    district: Mapped[Optional["District"]] = relationship("District", back_populates="listings")
    images: Mapped[List["ListingImage"]] = relationship(
        "ListingImage", back_populates="listing", cascade="all, delete-orphan"
    )


class ListingImage(Base):
    __tablename__ = "listing_images"
    __table_args__ = (
        UniqueConstraint("listing_id", "url", name="uq_listing_images"),
        {"schema": "mrf"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("mrf.listings.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[Optional[int]] = mapped_column(SmallInteger)

    listing: Mapped["Listing"] = relationship("Listing", back_populates="images")


class PortalParsingVersion(Base):
    __tablename__ = "portal_parsing_versions"
    __table_args__ = {"schema": "mrf"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    portal_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("mrf.portals.id"), nullable=False
    )
    version: Mapped[str] = mapped_column(Text, nullable=False)
    deployed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)
