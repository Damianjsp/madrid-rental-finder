"""Pydantic response schemas for the API."""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class PortalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name: str
    tier: int
    base_url: Optional[str]
    last_scrape_status: Optional[str] = None
    last_scrape_at: Optional[datetime] = None
    total_listings: Optional[int] = None


class ListingImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    position: Optional[int]


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portal_id: int
    portal_key: Optional[str] = None
    source_listing_id: str
    url: str

    title: Optional[str]
    price_eur: Optional[int]
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    size_m2: Optional[float]
    property_type: Optional[str]
    furnished: Optional[bool]

    address_raw: Optional[str]
    neighborhood_raw: Optional[str]
    district_raw: Optional[str]
    municipality_raw: Optional[str]

    district_id: Optional[int]
    neighborhood_id: Optional[int]
    lat: Optional[float]
    lon: Optional[float]

    is_active: bool
    first_seen_at: datetime
    last_seen_at: datetime


class ListingDetailOut(ListingOut):
    description: Optional[str]
    deposit_eur: Optional[int]
    expenses_included: Optional[bool]
    elevator: Optional[bool]
    parking: Optional[bool]
    images: List[ListingImageOut] = []


class ListingsPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ListingOut]


class CostBenchmarkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scope_kind: str
    scope_name: str
    avg_rent_1bed: Optional[int]
    avg_rent_2bed: Optional[int]
    avg_rent_3bed: Optional[int]
    avg_house: Optional[int]
    avg_chalet: Optional[int]
    observed_at: date


class NeighborhoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    municipality: str
    zone: Optional[str]
    district_id: Optional[int]
    district_name: Optional[str] = None
    safety_score: Optional[int]
    transport_score: Optional[int]
    commute_to_sol_min: Optional[int]
    commute_to_sol_max: Optional[int]
    commute_to_atocha_min: Optional[int]
    commute_to_atocha_max: Optional[int]
    notes: Optional[str]
    cost_benchmark: Optional[CostBenchmarkOut] = None
    listing_count: Optional[int] = None


class DistrictStatsOut(BaseModel):
    district_id: Optional[int]
    district_name: str
    total_listings: int
    active_listings: int
    avg_price: Optional[float]
    min_price: Optional[int]
    max_price: Optional[int]


class NeighborhoodStatsOut(BaseModel):
    neighborhood_id: Optional[int]
    neighborhood_name: str
    district_name: Optional[str]
    total_listings: int
    active_listings: int
    avg_price: Optional[float]


class StatsOut(BaseModel):
    total_listings: int
    active_listings: int
    portals_active: int
    by_district: List[DistrictStatsOut]
    by_neighborhood: List[NeighborhoodStatsOut]
