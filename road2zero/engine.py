"""Ren beräkningsmotor utan Streamlit, filer, nätverk eller dold datahämtning.

Tidssteg: kalenderår. Beräkningsenhet: kg CO2e. Lager: kg C.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from math import isclose

from .schema import Building, CATEGORIES, Phase, Scenario

CO2_PER_C = 44 / 12


class DataGap(ValueError):
    pass


@dataclass
class Result:
    ledger: list[dict] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    population: list[dict] = field(default_factory=list)
    used_factors: set[str] = field(default_factory=set)
    categories: list[dict] = field(default_factory=list)
    project_bta: float | None = None
    full_population: float | None = None
    estimated_population: float | None = None
    total_kg: float | None = None
    known_subtotal_kg: float = 0
    person_years: float | None = None

    def issue(self, category, object_id, text, severity="error"):
        item = dict(category=category, object_id=object_id, severity=severity, message=str(text))
        if item not in self.issues:
            self.issues.append(item)


class Calculator:
    def __init__(self, scenario: Scenario):
        self.s = scenario
        self.p = scenario.project
        self.r = Result()
        self.factors = {f.id: f for f in scenario.factors}
        self.curves = {c.id: c for c in scenario.curves}
        self.sources = {s.id: s for s in scenario.sources}
        self.active_phases = scenario.phases if self.p.phasing_enabled else [Phase(
            id="TOTAL", name="Hela byggperioden", start=self.p.build_start_year,
            end=self.p.build_end_year, share=1, source_id=self.p.source_id)]
        self.phases = {p.id: p for p in self.active_phases}
        self.phase_pop = {}
        self.bta = {}
        self.cohorts = []

    @staticmethod
    def required(value, label):
        if value is None:
            raise DataGap(f"Saknas: {label}")
        return value

    def source(self, source_id):
        if source_id not in self.sources or not self.sources[source_id].title.strip():
            raise DataGap(f"Källan {source_id or '(tom)'} finns inte i referensregistret")

    def factor(self, factor_id, unit, year, signed=False):
        if factor_id not in self.factors:
            raise DataGap(f"Välj faktor ({unit}); {factor_id or 'inget val'}")
        f = self.factors[factor_id]
        self.source(f.source_id)
        if f.unit != unit:
            raise DataGap(f"{f.id}: enhet {f.unit}, förväntar {unit}")
        self.r.used_factors.add(f.id)
        if f.curve_id:
            if f.curve_id not in self.curves:
                raise DataGap(f"Kurvan {f.curve_id} saknas")
            c = self.curves[f.curve_id]
            self.source(c.source_id)
            if c.unit != f.unit or not c.points:
                raise DataGap(f"Kurvan {c.id} har fel enhet eller saknar årspunkter")
            pts = sorted(c.points, key=lambda p: p.year)
            if year < pts[0].year or year > pts[-1].year:
                if c.tail != "hold":
                    raise DataGap(f"{c.id} täcker inte år {year}. Komplettera kurvan eller välj konstant svans")
                value = pts[0].value if year < pts[0].year else pts[-1].value
            else:
                value = pts[0].value
                for a, b in zip(pts, pts[1:]):
                    if a.year <= year <= b.year:
                        value = a.value + (b.value - a.value) * (year - a.year) / (b.year - a.year)
                        break
        else:
            value = self.required(f.value, f"värde för {f.id}") * (1 + f.annual_change) ** (year - f.reference_year)
        if value < 0 and not signed:
            raise DataGap(f"{f.id}: negativ emissionsfaktor kan bara användas för markens nettoflöde")
        return value

    def phase(self, phase_id):
        if not self.p.phasing_enabled:
            return self.active_phases[0]
        if phase_id not in self.phases:
            raise DataGap(f"Etapp {phase_id or '(tom)'} saknas")
        return self.phases[phase_id]

    def fraction(self, phase, year):
        if self.p.occupation == "after":
            return float(year > phase.end)
        return max(0., min(1., (year - phase.start + .5) / (phase.end - phase.start + 1)))

    def in_window(self, year, phase=None, land=False):
        if land or self.p.time_mode == "calendar":
            return self.p.start_year <= year <= self.p.end_year
        phase = self.required(phase, "etapp för etappvis beräkningsperiod")
        return phase.start <= year <= phase.end + self.p.operating_years

    def add(self, category, submodule, obj, year, kg, quantity=None, unit="", factor_id="",
            factor_value=None, formula="", inputs=None, view="Projekt", included=True):
        self.r.ledger.append(dict(category=category, submodule=submodule, object_id=obj.id, record_type=type(obj).__name__,
            year=year, kgco2e=kg, quantity=quantity, unit=unit, factor_id=factor_id,
            factor_value=factor_value, source_id=obj.source_id, formula=formula,
            inputs=json.dumps(inputs or {}, ensure_ascii=False, sort_keys=True),
            view=view, in_total=included and self.s.enabled.get(category, False)))

    def guard(self, category, obj, fn):
        if not self.s.enabled[category]:
            return
        try:
            self.source(obj.source_id)
            fn()
        except DataGap as e:
            self.r.issue(category, obj.id, e)

    def setup(self):
        try:
            self.source(self.p.source_id)
        except DataGap as e:
            self.r.issue("Projekt", self.p.id, e)
        for path, sid in self.s.parameter_sources.items():
            if sid not in self.sources:
                self.r.issue("Projekt", path, f"Parameterkällan {sid} saknas i referensregistret")
        if not self.phases:
            self.r.issue("Projekt", self.p.id, "Lägg till minst en etapp")
        elif not isclose(sum(p.share for p in self.active_phases), 1., abs_tol=1e-8):
            self.r.issue("Projekt", self.p.id, "Etappernas fördelningsandelar måste summera till 100 %")
        if self.p.phasing_enabled and any(p.start < self.p.build_start_year or p.end > self.p.build_end_year for p in self.active_phases):
            self.r.issue("Projekt", self.p.id, "Samtliga etapper måste ligga inom projektets valda byggperiod")
        programme_share = sum(p.share_bta for p in self.s.programme)
        if not isclose(programme_share, 1., abs_tol=1e-8):
            self.r.issue("Projekt", self.p.id, "BTA-programmets andelar måste summera till 100 %; inga enskilda byggnader används")
        try:
            if self.p.total_bta_override is not None:
                self.r.project_bta = self.p.total_bta_override
            else:
                residential_share = sum(x.share_bta for x in self.s.programme if x.residential)
                if residential_share <= 0:
                    raise DataGap("Ange total nybyggd BTA när programmet saknar bostäder")
                self.r.project_bta = self.p.homes * self.factor(self.p.bta_per_home_factor_id, "m2/home", self.p.start_year) / residential_share
        except DataGap as e:
            self.r.issue("Projekt", self.p.id, e, "warning")
        # Programandel × etappandel fördelar total BTA exakt en gång. Detta är
        # interna kohorter för tidsberäkning, inte register över byggnadsobjekt.
        for group in self.s.programme:
            if group.share_bta == 0:
                continue
            for phase in self.active_phases:
                if phase.share == 0:
                    continue
                data = {k:v for k,v in group.model_dump().items() if k != "share_bta"}
                data.update(id=group.id+"@"+phase.id, name=group.name+" · "+phase.name, phase_id=phase.id)
                for key in ("construction_total_kg","atemp_m2","electricity_annual","heat_annual","solar_kwh_year","sheet_area_m2"):
                    if data.get(key) is not None:
                        data[key] *= phase.share
                b = Building.model_validate(data)
                self.cohorts.append(b)
                if self.r.project_bta is not None:
                    self.bta[b.id] = self.r.project_bta * group.share_bta * phase.share
        try:
            if self.p.population_method == "homes":
                estimate = self.p.homes * self.factor(self.p.people_per_home_factor_id, "person/home", self.p.start_year)
            else:
                bta = self.required(self.r.project_bta, "total BTA för invånarskattning") * sum(x.share_bta for x in self.s.programme if x.residential)
                factor = self.factor(self.p.bta_per_person_factor_id, "m2/person", self.p.start_year)
                if factor <= 0:
                    raise DataGap("BTA per invånare måste vara större än noll")
                estimate = bta / factor
            self.r.estimated_population = estimate
        except DataGap as e:
            estimate = None
            if self.p.population_override is None and self.p.population_level == "project":
                self.r.issue("Befolkning", self.p.id, e)
        if self.p.population_level == "project":
            active = self.p.population_override if self.p.population_override is not None else estimate
            if active is not None:
                self.phase_pop = {p.id: active * p.share for p in self.active_phases}
        else:
            for p in self.active_phases:
                if p.population_override is None:
                    self.r.issue("Befolkning", p.id, "Ange invånare i samtliga etapper när etappnivå är vald")
                else:
                    self.phase_pop[p.id] = p.population_override
        pop_error = any(x["category"] == "Befolkning" and x["severity"] == "error" for x in self.r.issues)
        if len(self.phase_pop) == len(self.phases) and self.phases and not pop_error:
            self.r.full_population = sum(self.phase_pop.values())
        starts = [self.p.start_year] + [p.start for p in self.active_phases]
        ends = [self.p.end_year] + [p.end + self.p.operating_years for p in self.active_phases]
        self.years = range(min(starts), max(ends) + 1)
        for year in self.years:
            physical = sum(self.phase_pop.get(p.id, 0) * self.fraction(p, year) for p in self.active_phases)
            reporting = sum(self.phase_pop.get(p.id, 0) * self.fraction(p, year)
                            for p in self.active_phases if self.in_window(year, p))
            self.r.population.append(dict(year=year, physical_population=physical if self.r.full_population is not None else None,
                                          reporting_population=reporting if self.r.full_population is not None else None))
        if self.r.full_population is not None:
            self.r.person_years = sum(x["reporting_population"] for x in self.r.population)

    def construction(self, b):
        if b.status == "existing":
            return  # Historisk byggnation ligger utanför framåtblickande scenario.
        p = self.phase(b.phase_id)
        if b.construction_total_kg is not None:
            total, q, f = b.construction_total_kg, None, None
        else:
            q = self.required(self.bta.get(b.id), "BTA")
            f = 0 if q == 0 else self.factor(b.construction_factor_id, "kgCO2e/m2", p.start)
            total = q * f
        for year in range(p.start, p.end + 1):
            if self.in_window(year, p):
                self.add("Byggnad", "Byggskede", b, year, total / (p.end-p.start+1), q, "m2", b.construction_factor_id if q is not None else "", f,
                         "BTA × faktor(byggstart) / antal byggår; manuell total ersätter byggnadsfaktorn",
                         {"total_kg": total, "start": p.start, "end": p.end, "material": b.material})

    def foundation(self, b, sheet=False):
        if b.status == "existing":
            return
        p = self.phase(b.phase_id)
        status = b.sheet_piling if sheet else b.piling
        label = "Spontning" if sheet else "Pålning"
        if status == "unknown":
            raise DataGap(f"{label}: välj Ja eller Nej")
        if status == "no":
            q, f = 0., 0.
        else:
            q = self.required(b.sheet_area_m2 if sheet else self.bta.get(b.id), f"mängd för {label}")
            f = self.factor(b.sheet_factor_id if sheet else b.piling_factor_id, "kgCO2e/m2", p.start) if q else 0.
        for year in range(p.start, p.end + 1):
            if self.in_window(year, p):
                self.add("Anläggning", label, b, year, q*f/(p.end-p.start+1), q, "m2", b.sheet_factor_id if sheet else b.piling_factor_id, f,
                         "Mängd × faktor / antal byggår; Nej ger uttryckligt 0",
                         {"quantity_basis": "spontyta" if sheet else "BTA", "decision": status})

    def energy(self, b):
        p = self.phase(b.phase_id)
        if b.energy_mode == "excluded":
            self.r.issue("Energi", b.id, "Byggnadens driftenergi är uttryckligen exkluderad", "warning")
            return
        if b.energy_mode == "annual":
            electricity = self.required(b.electricity_annual, "elanvändning, kWh/år (0 tillåts)")
            heat = self.required(b.heat_annual, "värmeanvändning, kWh/år (0 tillåts)")
            area = None
        else:
            area = b.atemp_m2
            if area is None:
                area = self.required(self.bta.get(b.id), "BTA för Atemp-skattning") * self.factor(b.atemp_ratio_factor_id, "Atemp/BTA", p.start)
            electricity = area * self.required(b.electricity_specific, "el, kWh/m² Atemp/år")
            heat = area * self.required(b.heat_specific, "värme, kWh/m² Atemp/år")
        solar = self.required(b.solar_kwh_year, "solelproduktion, kWh/år (ange 0 om ingen)")
        self_use = self.required(b.solar_self_use, "egenanvänd andel solel") if solar else 0
        purchased = max(0, electricity - solar * self_use)
        export = solar - min(electricity, solar * self_use)
        for year in self.years:
            if not self.in_window(year, p):
                continue
            occ = 1. if b.status == "existing" else self.fraction(p, year)
            if not occ:
                continue
            for name, kwh, fid in (("Köpt el", purchased, b.electricity_factor_id), ("Värme", heat, b.heat_factor_id)):
                ef = self.factor(fid, "gCO2e/kWh", year) if kwh else 0.
                self.add("Energi", name, b, year, kwh*occ*ef/1000, kwh*occ, "kWh", fid, ef,
                         "kWh vid full drift × driftandel × g CO2e/kWh / 1000",
                         {"Atemp": area, "full_year_kwh": kwh, "occupation": occ, "solar_kwh": solar, "self_use": self_use})
            if export:
                self.add("Energi", "Solelöverskott (kWh)", b, year, 0, export*occ, "kWh", formula="Export redovisas i kWh utan klimatkredit", included=False, view="Solelexport")

    def infrastructure(self, a):
        p = self.phase(a.phase_id)
        if a.land_id and a.land_id not in {l.id for l in self.s.lands}:
            raise DataGap(f"Mark-ID {a.land_id} saknas")
        if a.total_kg is not None:
            total, q, f = a.total_kg, None, None
        else:
            q = self.required(a.quantity, f"mängd för {a.name}")
            f = self.factor(a.factor_id, f"kgCO2e/{a.unit}", p.start) if q else 0.
            total = q * f
        for year in range(p.start, p.end+1):
            if self.in_window(year, p):
                self.add("Anläggning", a.submodule, a, year, total/(p.end-p.start+1), q, a.unit, a.factor_id if q is not None else "", f,
                         "Mängd × faktor / antal byggår; egen total ersätter denna aktivitetsrad",
                         {"land_id": a.land_id, "total_kg": total})

    def land(self, l):
        area = self.required(l.area_m2, "markarea")
        if "Ej" in l.before or "Ej" in l.after or l.soil == "Ej utrett":
            raise DataGap("Klassificera mark före, efter och jordtyp; välj även befintligt exploaterad mark uttryckligen")
        pools = []
        for pool in ("soc", "dom", "biomass"):
            keep = self.required(getattr(l, "keep_"+pool), f"bevarad andel {pool}")
            density = self.factor(getattr(l, pool+"_factor_id"), "kgC/m2", l.change_year) if area else 0.
            loss = area * density * (1-keep) * CO2_PER_C
            pools.append((pool, density, keep, loss))
            for year in range(l.change_year, l.change_year+l.release_years):
                if self.in_window(year, land=True):
                    self.add("Förändrad markanvändning", pool.upper(), l, year, loss/l.release_years, area, "m2",
                             getattr(l, pool+"_factor_id"), density, "Area × kg C/m² × (1 − bevarad andel) × 44/12 / utsläppsår",
                             {"keep_fraction": keep, "release_years": l.release_years, "CO2_per_C": CO2_PER_C})
        biomass = next(x[1]*x[2] for x in pools if x[0] == "biomass")
        state_start = min(l.change_year, self.p.start_year) if l.flow_mode == "forest" else self.p.start_year
        for year in range(state_start, self.p.end_year+1):
            ref = self.factor(l.reference_flow_factor_id, "kgCO2e/m2/year", year, signed=True) if area and self.in_window(year,land=True) else 0.
            if year < l.change_year:
                flow = ref
            elif l.flow_mode == "forest":
                growth = self.required(l.growth_m3_ha_year, "skogstillväxt, m³sk/ha/år")
                bef = self.factor(l.expansion_factor_id, "ratio", year)
                density = self.factor(l.wood_density_factor_id, "kg/m3", year)
                fraction = self.factor(l.carbon_fraction_factor_id, "ratio", year)
                if fraction > 1:
                    raise DataGap("Skogens kolfraktion måste ligga inom 0–1")
                capacity = self.factor(l.biomass_capacity_factor_id, "kgC/m2", year)
                gain = min(growth*bef*density*fraction/10000, max(0, capacity-biomass))
                biomass += gain
                flow = -gain * CO2_PER_C
            else:
                flow = self.factor(l.after_flow_factor_id, "kgCO2e/m2/year", year, signed=True) if area else 0.
            if not self.in_window(year, land=True):
                continue  # Skogens tillstånd uppdateras även före redovisningsperioden.
            category = "Negativa utsläpp" if flow < 0 else "Förändrad markanvändning"
            self.add(category, "Skogstillväxt" if l.flow_mode == "forest" and year >= l.change_year else "Markens årliga nettoflöde", l, year, area*flow, area, "m2",
                     l.after_flow_factor_id if year >= l.change_year and l.flow_mode != "forest" else l.reference_flow_factor_id if year < l.change_year else "", flow,
                     "Area × nettoflöde; skog: tillväxt × BEF × densitet × kolfraktion / 10000 × 44/12, begränsat av angivet kollager",
                     {"flow_kgco2e_m2_year": flow, "soil": l.soil}, included=self.s.enabled["Förändrad markanvändning"])
            self.add("Förändrad markanvändning", "Referensmarkens årliga nettoflöde", l, year, area*ref, area, "m2", l.reference_flow_factor_id, ref,
                     "Area × referensflöde; visas separat och dras aldrig av projektets inventering", view="Referensmark", included=False)
        if l.soil in ("Organisk jord", "Våtmark"):
            self.r.issue("Förändrad markanvändning", l.id, "Organisk jord/våtmark: ange projektspecifika CO2e-flöden inklusive CH4/N2O. Lager och flöde måste avse olika processer för att undvika dubbelräkning.", "warning")

    def consumption(self, c):
        if c.overlaps_energy_transport:
            raise DataGap("Avgränsa faktorn från energi/transport som redan ingår innan posten kan räknas")
        if c.mode in ("person", "quantity"):
            self.required(self.r.full_population, "fullständig befolkningsberäkning")
        if c.mode == "person":
            if c.unit != "person/year":
                raise DataGap("Per invånare kräver enheten person/year")
            base_unit = "tCO2e/person/year" if c.category == "Offentliga investeringar" else "kgCO2e/person/year"
            quantity = 1.
        else:
            if c.unit == "person/year":
                raise DataGap("Välj fysisk enhet för mängdbaserad konsumtion")
            quantity = self.required(c.quantity, "årsmängd")
            base_unit = f"kgCO2e/{c.unit}"
        for pop in self.r.population:
            year = pop["year"]
            if c.mode == "total":
                if self.p.time_mode != "calendar":
                    raise DataGap("En total årsmängd kräver gemensam kalenderperiod; välj per invånare för etappvis tid")
                if not self.in_window(year):
                    continue
                qty = quantity*c.coverage
            else:
                qty = quantity * pop["reporting_population"] * c.coverage
                if qty == 0:
                    continue
            ef = self.factor(c.factor_id, base_unit, year) if qty else 0.
            conversion = 1000 if base_unit == "tCO2e/person/year" else 1
            self.add(c.category, c.name, c, year, qty*ef*conversion, qty, c.unit, c.factor_id, ef,
                     "Årsmängd × täckningsandel × faktor; invånarbaserade mängder × årets invånare; ton → kg × 1000",
                     {"mode": c.mode, "coverage": c.coverage, "annual_quantity": quantity, "conversion_to_kg": conversion})
        # En uttrycklig nollbefolkning ger ett känt nollresultat.
        if c.mode != "total" and self.r.full_population == 0:
            self.add(c.category, c.name, c, self.p.start_year, 0, 0, c.unit, formula="Uttryckligt 0 invånare")

    def transport(self):
        cat = "Mobilitet och transport"
        if not self.s.enabled[cat] or self.p.transport_scope == "excluded":
            return
        if self.p.transport_scope == "unset":
            self.r.issue(cat, self.p.id, "Välj vilket transportperspektiv som ska ingå i totalen, eller exkludera transport")
        for perspective in ("residents", "all"):
            rows = [x for x in self.s.transport if x.perspective == perspective]
            chosen = self.p.transport_scope == perspective
            severity = "error" if chosen else "warning"
            if not rows:
                if chosen:
                    self.r.issue(cat, perspective, "Importera en årlig Vägvis-serie för valt perspektiv")
                continue
            seen = set()
            for t in rows:
                try:
                    self.source(t.source_id)
                    if not t.boundary.strip():
                        raise DataGap("Beskriv Vägvis-underlagets systemgräns")
                    if t.includes_construction or t.includes_building_electricity:
                        raise DataGap("Överlapp med byggtransporter/el: avgränsa importen före summering")
                    key = (t.year, t.phase_id)
                    if key in seen:
                        raise DataGap(f"Dubbel transportpost för år {t.year}, etapp {t.phase_id or 'hela projektet'}")
                    seen.add(key)
                    if self.p.time_mode == "cohort" and self.p.phasing_enabled and not t.phase_id:
                        raise DataGap("Etappvis tidsperiod kräver etapp-ID på varje Vägvis-årsvärde")
                    phase = self.phase(t.phase_id) if t.phase_id or not self.p.phasing_enabled else None
                    if self.in_window(t.year, phase):
                        self.add(cat, "Boendes resor" if perspective == "residents" else "All trafik i underlaget", t, t.year, t.tco2e*1000, t.tco2e, "tCO2e", formula="Importerat årligt tonvärde × 1000; ingen ytterligare skalning", inputs={"boundary": t.boundary, "phase_id": t.phase_id}, view=perspective, included=chosen)
                except DataGap as e:
                    self.r.issue(cat, t.id, e, severity)
            for year in self.years:
                total_rows = [t for t in rows if t.year == year and not t.phase_id]
                phase_rows = [t for t in rows if t.year == year and t.phase_id]
                if total_rows and phase_rows:
                    self.r.issue(cat, perspective, f"År {year}: projektets total och etapposter får inte blandas", severity)
                required_phases = [p for p in self.active_phases if self.in_window(year, p) and self.fraction(p, year) > 0]
                # Vägvis kan ange uttryckliga nollor. Ingen interpolation eller repetition sker här.
                if required_phases and not total_rows:
                    missing = [p.id for p in required_phases if not any(t.phase_id == p.id for t in phase_rows)]
                    if missing:
                        self.r.issue(cat, perspective, f"Vägvis saknar år {year} för etapp(er): {', '.join(missing)}", severity)

    def removal(self, x):
        if x.kind == "timber" and x.include_in_total:
            raise DataGap("Inbyggt virke redovisas som kollager. Verifierat upptag kräver separat post med full metodik; virkeslager räknas inte automatiskt som negativt utsläpp")
        if x.include_in_total and not x.eligibility_confirmed:
            raise DataGap("Bekräfta varaktighet, additionalitet, ägande och avgränsning före avdrag")
        if x.include_in_total and x.epd_already_includes_storage:
            raise DataGap("Kolinlagringen ingår redan i EPD/byggnadsfaktor och får inte dras av igen")
        if x.land_id and x.include_in_total:
            for l in self.s.lands:
                if l.id == x.land_id and (l.flow_mode == "forest" or l.after_flow_factor_id):
                    raise DataGap("Upptag på samma mark redovisas redan i markmodulen; välj en beräkningsväg")
        q = self.required(x.quantity, "mängd för kollager/upptag")
        annual = x.kind == "trees"
        if annual and x.end_year is None:
            raise DataGap("Ange slutår för trädens årliga upptag")
        life = self.required(x.lifecycle_kg, "livscykelutsläpp för åtgärden (0 tillåts med källa)")
        if self.in_window(x.year, land=True):
            self.add("Negativa utsläpp", "Åtgärdens livscykelutsläpp", x, x.year, life,
                     formula="Angivna livscykelutsläpp särredovisas med positivt tecken", included=x.include_in_total, view="Projekt" if x.include_in_total else "Kollager")
        total_stored = 0.
        for year in range(x.year, (x.end_year if annual else x.year) + 1):
            ef = self.factor(x.factor_id, f"kgCO2e/{x.unit}" + ("/year" if annual else ""), year) if q else 0.
            amount = q * ef
            total_stored += amount
            if self.in_window(year, land=True):
                self.add("Negativa utsläpp", x.name, x, year, -amount, q, x.unit, x.factor_id, ef,
                         "Mängd × faktor; tidsbundet kollager redovisas separat tills kriterierna är uppfyllda", included=x.include_in_total, view="Projekt" if x.include_in_total else "Kollager")
        if x.release_year is not None and self.in_window(x.release_year, land=True):
            self.add("Negativa utsläpp", "Återföring av kol", x, x.release_year, total_stored,
                     formula="Hela den bokförda kolmängden återförs i angivet år", included=x.include_in_total, view="Projekt" if x.include_in_total else "Kollager")

    def finish(self):
        for cat in CATEGORIES:
            enabled = self.s.enabled[cat]
            if cat == "Mobilitet och transport" and self.p.transport_scope == "excluded":
                enabled = False
            rows = [x for x in self.r.ledger if x["category"] == cat and x["in_total"]]
            # Upptag är valfritt, men avdrag som användaren försöker beräkna måste vara kompletta.
            if enabled and not rows and cat != "Negativa utsläpp":
                self.r.issue(cat, "", "Inga fullständiga poster. Komplettera indata eller exkludera klimatkategorin uttryckligen")
            errors = [x for x in self.r.issues if x["category"] == cat and x["severity"] == "error"]
            known = sum(x["kgco2e"] for x in rows)
            self.r.categories.append(dict(category=cat, enabled=enabled, status="Exkluderad" if not enabled else "Ofullständig" if errors else "Beräknad",
                                          kgco2e=None if errors or not enabled else known, known_subtotal_kg=known, missing=len(errors)))
        active = [x for x in self.r.ledger if x["in_total"]]
        self.r.known_subtotal_kg = sum(x["kgco2e"] for x in active)
        blocking = any(x["severity"] == "error" for x in self.r.issues)
        if not blocking:
            self.r.total_kg = self.r.known_subtotal_kg
        for fid in sorted(self.r.used_factors):
            f = self.factors[fid]
            if f.quality not in ("Verifierad", "Projektverifierad", "Matematisk konstant"):
                self.r.issue("Faktorer", fid, f"Använd faktor har status '{f.quality}': {f.note or 'källgranskning återstår'}", "warning")
        return self.r

    def run(self):
        self.setup()
        for b in self.cohorts:
            self.guard("Byggnad", b, lambda b=b: self.construction(b))
            self.guard("Anläggning", b, lambda b=b: self.foundation(b))
            self.guard("Anläggning", b, lambda b=b: self.foundation(b, sheet=True))
            self.guard("Energi", b, lambda b=b: self.energy(b))
        for a in self.s.activities:
            self.guard("Anläggning", a, lambda a=a: self.infrastructure(a))
        if self.s.enabled["Förändrad markanvändning"]:
            if self.p.land_mode == "full":
                total = sum(l.area_m2 or 0 for l in self.s.lands)
                if self.p.area_m2 is None or not isclose(total, self.p.area_m2, abs_tol=.01):
                    self.r.issue("Förändrad markanvändning", self.p.id, f"Areabalansen stämmer inte: register {total:g} m², projekt {self.p.area_m2} m²")
            for l in self.s.lands:
                self.guard("Förändrad markanvändning", l, lambda l=l: self.land(l))
        for c in self.s.consumption:
            self.guard(c.category, c, lambda c=c: self.consumption(c))
        self.transport()
        for x in self.s.removals:
            self.guard("Negativa utsläpp", x, lambda x=x: self.removal(x))
        return self.finish()


def calculate(scenario: Scenario) -> Result:
    return Calculator(scenario).run()


def parameter_audit(scenario: Scenario) -> list[dict]:
    """Alla ingivna parametrar med sökväg och ärvd/explicit källa, även exkluderade."""
    rows = []
    def visit(value, path, source):
        if isinstance(value, dict):
            source = value.get("source_id", source)
            for k, v in value.items():
                if k not in ("sources", "parameter_sources"):
                    visit(v, f"{path}.{k}" if path else k, source)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                tag = v.get("id", str(i)) if isinstance(v, dict) else str(i)
                visit(v, f"{path}[{tag}]", source)
        else:
            sid = scenario.parameter_sources.get(path, source)
            rows.append(dict(parameter=path, value=value, source_id=sid,
                             status="Saknas" if value is None or value == "" else "Angiven"))
    visit(scenario.model_dump(), "", scenario.project.source_id)
    rows.append(dict(parameter="constant.CO2_per_C", value=CO2_PER_C, source_id="IPCC2006", status="Matematisk konstant"))
    return rows
