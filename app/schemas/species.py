"""Species — list/detail Pydantic schemas."""
from __future__ import annotations

from pydantic import BaseModel


class SpeciesList(BaseModel):
    id: int
    slug: str
    name: str
    latin: str = ""
    category: str
    icon_name: str = "leaf"
    color_class: str = ""
    summary: str = ""
    red_book: bool = False
    iucn_status: str = "NE"
    picture: str = ""

    model_config = {"from_attributes": True}


class SpeciesPhotoOut(BaseModel):
    url: str
    attribution: str = ""
    license_code: str = ""
    source: str = "inat"
    is_default: bool = False

    model_config = {"from_attributes": True}


class SpeciesDetail(SpeciesList):
    description: str = ""
    habitat: str = ""
    uses: str = ""
    warnings: str = ""
    first_aid: str = ""
    regions: str = ""
    external_ref: str = ""
    halal_status: str = "unknown"
    is_medicinal: bool = False
    is_honey_plant: bool = False
    livestock_danger: str = "safe"
    is_edible: bool = False
    bloom_months: str = ""
    harvest_months: str = ""
    fine_bhm_min: int = 0
    fine_bhm_max: int = 0
    law_article: str = ""
    photos: list[SpeciesPhotoOut] = []


class Paginated(BaseModel):
    count: int
    next: str | None = None
    previous: str | None = None
    results: list


class SpeciesListPage(Paginated):
    results: list[SpeciesList]


class SpeciesDetailPage(Paginated):
    results: list[SpeciesDetail]
