"""Validerat, versionssatt dataformat. Alla mängder/faktorer använder SI-liknande enheter.

None betyder saknat underlag. Noll är ett uttryckligt numeriskt värde.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CATEGORIES = ["Byggnad", "Energi", "Anläggning", "Förändrad markanvändning",
              "Mobilitet och transport", "Matkonsumtion", "Övrig konsumtion",
              "Offentliga investeringar", "Negativa utsläpp"]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Source(Record):
    id: str
    title: str
    author: str = ""
    year: str = ""
    url: str = ""
    locator: str = ""
    kind: str = "Projektunderlag"
    note: str = ""


class Factor(Record):
    id: str
    name: str
    value: float | None = None
    unit: str
    source_id: str = "USER"
    locator: str = ""
    quality: str = "Ej verifierad"
    boundary: str = ""
    reference_year: int = Field(default=2026, ge=1900, le=2300)
    annual_change: float = Field(default=0, gt=-1, le=1)
    curve_id: str = ""
    uncertainty_pct: float | None = Field(default=None, ge=0, le=100)
    note: str = ""


class CurvePoint(Record):
    year: int = Field(ge=1900, le=2300)
    value: float


class Curve(Record):
    id: str
    name: str
    unit: str
    source_id: str = "USER"
    tail: Literal["error", "hold"] = "error"
    points: list[CurvePoint] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_years(self):
        if len({p.year for p in self.points}) != len(self.points):
            raise ValueError(f"Dubbla år i kurvan {self.id}")
        return self


class Phase(Record):
    id: str
    name: str
    start: int = Field(ge=1900, le=2200)
    end: int = Field(ge=1900, le=2200)
    share: float = Field(default=1, ge=0, le=1)
    population_override: float | None = Field(default=None, ge=0)
    source_id: str = "USER"

    @model_validator(mode="after")
    def dates(self):
        if self.end < self.start:
            raise ValueError("Byggslut måste vara tidigast byggstart")
        return self


class Project(Record):
    id: str = "NYTT-01"
    name: str = "Nytt scenario"
    source_id: str = "USER"
    area_m2: float | None = Field(default=None, ge=0)
    homes: int = Field(default=0, ge=0)
    total_bta_override: float | None = Field(default=None, ge=0)
    bta_per_home_factor_id: str = "bta_per_home"
    population_level: Literal["project", "phase"] = "project"
    population_method: Literal["homes", "bta"] = "homes"
    population_override: float | None = Field(default=None, ge=0)
    people_per_home_factor_id: str = "people_per_home"
    bta_per_person_factor_id: str = ""
    start_year: int = Field(default=2029, ge=1900, le=2200)
    end_year: int = Field(default=2078, ge=1900, le=2300)
    time_mode: Literal["calendar", "cohort"] = "calendar"
    build_start_year: int = Field(default=2029, ge=1900, le=2200)
    build_end_year: int = Field(default=2048, ge=1900, le=2200)
    phasing_enabled: bool = False
    operating_years: int = Field(default=50, ge=1, le=100)
    occupation: Literal["linear", "after"] = "linear"
    land_mode: Literal["full", "changed"] = "full"
    land_reference: str = "Fortsatt markanvändning utan projektet"
    transport_scope: Literal["unset", "residents", "all", "excluded"] = "unset"
    note: str = ""

    @model_validator(mode="after")
    def dates(self):
        if self.build_end_year < self.build_start_year:
            raise ValueError("Byggperiodens slutår måste vara tidigast dess startår")
        if self.end_year < self.start_year or self.end_year - self.start_year > 200:
            raise ValueError("Välj en gemensam period på högst 201 kalenderår")
        return self


class Building(Record):
    """Internt beräkningsobjekt för programrad × etapp, aldrig användarens indata."""
    id: str
    name: str
    phase_id: str
    source_id: str = "USER"
    status: Literal["planned", "existing"] = "planned"
    kind: str = "Flerbostadshus"
    material: str = "Ej valt"
    residential: bool = True
    bta_m2: float | None = Field(default=None, ge=0)
    project_bta_share: float | None = Field(default=None, ge=0, le=1)
    bya_m2: float | None = Field(default=None, ge=0)
    homes: float | None = Field(default=None, ge=0)
    population_override: float | None = Field(default=None, ge=0)
    construction_factor_id: str = ""
    construction_total_kg: float | None = Field(default=None, ge=0)
    energy_mode: Literal["area", "annual", "excluded"] = "area"
    energy_class: str = "Ej valt"
    atemp_m2: float | None = Field(default=None, ge=0)
    atemp_ratio_factor_id: str = ""
    electricity_specific: float | None = Field(default=None, ge=0)
    heat_specific: float | None = Field(default=None, ge=0)
    electricity_annual: float | None = Field(default=None, ge=0)
    heat_annual: float | None = Field(default=None, ge=0)
    electricity_factor_id: str = ""
    heat_factor_id: str = ""
    solar_kwh_year: float | None = Field(default=None, ge=0)
    solar_self_use: float | None = Field(default=None, ge=0, le=1)
    piling: Literal["unknown", "yes", "no"] = "unknown"
    piling_factor_id: str = "legacy_piling"
    sheet_piling: Literal["unknown", "yes", "no"] = "unknown"
    sheet_area_m2: float | None = Field(default=None, ge=0)
    sheet_factor_id: str = "legacy_sheet"
    note: str = ""


class Programme(Record):
    """Andel av projektets totala nybyggda BTA, inte en enskild byggnad."""
    id: str
    name: str
    source_id: str = "USER"
    share_bta: float = Field(default=1, ge=0, le=1)
    kind: str = "Flerbostadshus"
    material: str = "Ej valt"
    residential: bool = True
    construction_factor_id: str = ""
    construction_total_kg: float | None = Field(default=None, ge=0)
    energy_mode: Literal["area", "annual", "excluded"] = "area"
    energy_class: str = "Ej valt"
    atemp_m2: float | None = Field(default=None, ge=0)
    atemp_ratio_factor_id: str = ""
    electricity_specific: float | None = Field(default=None, ge=0)
    heat_specific: float | None = Field(default=None, ge=0)
    electricity_annual: float | None = Field(default=None, ge=0)
    heat_annual: float | None = Field(default=None, ge=0)
    electricity_factor_id: str = ""
    heat_factor_id: str = ""
    solar_kwh_year: float | None = Field(default=None, ge=0)
    solar_self_use: float | None = Field(default=None, ge=0, le=1)
    piling: Literal["unknown", "yes", "no"] = "unknown"
    piling_factor_id: str = "legacy_piling"
    sheet_piling: Literal["unknown", "yes", "no"] = "unknown"
    sheet_area_m2: float | None = Field(default=None, ge=0)
    sheet_factor_id: str = "legacy_sheet"
    note: str = ""


class Activity(Record):
    id: str
    name: str
    phase_id: str
    submodule: str = "Ytbeläggning"
    source_id: str = "USER"
    land_id: str = ""
    quantity: float | None = Field(default=None, ge=0)
    unit: Literal["m2", "m3", "tkm", "m", "t", "st"] = "m2"
    factor_id: str = ""
    total_kg: float | None = Field(default=None, ge=0)
    note: str = ""


class Land(Record):
    id: str
    name: str
    source_id: str = "USER"
    area_m2: float | None = Field(default=None, ge=0)
    before: str = "Ej klassificerad"
    after: str = "Ej klassificerad"
    soil: str = "Ej utrett"
    change_year: int = Field(default=2029, ge=1900, le=2300)
    release_years: int = Field(default=1, ge=1, le=100)
    soc_factor_id: str = ""
    dom_factor_id: str = ""
    biomass_factor_id: str = ""
    keep_soc: float | None = Field(default=None, ge=0, le=1)
    keep_dom: float | None = Field(default=None, ge=0, le=1)
    keep_biomass: float | None = Field(default=None, ge=0, le=1)
    after_flow_factor_id: str = ""
    reference_flow_factor_id: str = ""
    flow_mode: Literal["factor", "forest"] = "factor"
    growth_m3_ha_year: float | None = Field(default=None, ge=0)
    expansion_factor_id: str = ""
    wood_density_factor_id: str = ""
    carbon_fraction_factor_id: str = ""
    biomass_capacity_factor_id: str = ""
    note: str = ""


class Consumption(Record):
    id: str
    name: str
    category: Literal["Matkonsumtion", "Övrig konsumtion", "Offentliga investeringar"]
    source_id: str = "USER"
    mode: Literal["person", "quantity", "total"] = "person"
    quantity: float | None = Field(default=None, ge=0)
    unit: Literal["person/year", "kg", "SEK", "st", "kWh"] = "person/year"
    coverage: float = Field(default=1, ge=0, le=1)
    factor_id: str = ""
    overlaps_energy_transport: bool = False
    note: str = ""

    @model_validator(mode="after")
    def public_investment_unit(self):
        if self.category == "Offentliga investeringar" and (self.mode != "person" or self.unit != "person/year"):
            raise ValueError("Offentliga investeringar anges med årlig faktor per invånare (mode=person, unit=person/year)")
        return self


class Transport(Record):
    id: str
    year: int = Field(ge=1900, le=2300)
    perspective: Literal["residents", "all"]
    phase_id: str = ""
    tco2e: float = Field(ge=0)
    source_id: str = "USER"
    boundary: str = ""
    includes_building_electricity: bool = False
    includes_construction: bool = False


class Removal(Record):
    id: str
    name: str
    kind: Literal["biochar", "timber", "trees", "other"] = "biochar"
    source_id: str = "USER"
    year: int = Field(default=2029, ge=1900, le=2300)
    end_year: int | None = Field(default=None, ge=1900, le=2300)
    release_year: int | None = Field(default=None, ge=1900, le=2300)
    quantity: float | None = Field(default=None, ge=0)
    unit: Literal["t", "kg", "m3", "st"] = "t"
    factor_id: str = ""
    lifecycle_kg: float | None = Field(default=None, ge=0)
    include_in_total: bool = False
    eligibility_confirmed: bool = False
    epd_already_includes_storage: bool = False
    land_id: str = ""
    note: str = ""

    @model_validator(mode="after")
    def dates(self):
        if self.end_year is not None and self.end_year < self.year:
            raise ValueError("Upptagets slutår är före startåret")
        if self.release_year is not None and self.release_year < self.year:
            raise ValueError("Återföringen kan inte inträffa före inlagringen")
        if self.kind == "trees" and self.end_year is not None and self.release_year is not None and self.release_year < self.end_year:
            raise ValueError("Trädens återföring måste vara tidigast sista året med bokfört upptag")
        return self


class Scenario(Record):
    schema_version: Literal["1.0"] = "1.0"
    project: Project = Field(default_factory=Project)
    phases: list[Phase] = Field(default_factory=list)
    programme: list[Programme] = Field(default_factory=list)
    activities: list[Activity] = Field(default_factory=list)
    lands: list[Land] = Field(default_factory=list)
    consumption: list[Consumption] = Field(default_factory=list)
    transport: list[Transport] = Field(default_factory=list)
    removals: list[Removal] = Field(default_factory=list)
    factors: list[Factor] = Field(default_factory=list)
    curves: list[Curve] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    enabled: dict[str, bool] = Field(default_factory=lambda: dict.fromkeys(CATEGORIES, True))
    parameter_sources: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def identities(self):
        for name in ("phases", "programme", "activities", "lands", "consumption", "transport", "removals", "factors", "curves", "sources"):
            ids = [x.id for x in getattr(self, name)]
            if any(not x.strip() for x in ids) or len(ids) != len(set(ids)):
                raise ValueError(f"Tomma eller dubbla ID i {name}")
        if set(self.enabled) != set(CATEGORIES):
            raise ValueError("enabled måste innehålla exakt modellens nio klimatkategorier")
        return self
