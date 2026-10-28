"""Beräkningskontext: årsaxel, tidskurvor, parameteruppslag med spårning, resultatrader och mellanled."""
from __future__ import annotations

from dataclasses import dataclass, field

from .factlib import Faktabibliotek
from .utveckling import Utveckling


@dataclass
class Kontext:
    fb: Faktabibliotek
    scen: dict
    ar: list[int] = field(default_factory=list)
    rader: list[dict] = field(default_factory=list)       # resultat: ar, kategori, delpost, modul, t
    utanfor: list[dict] = field(default_factory=list)     # undvikna utsläpp (utanför nettot)
    spar: list[dict] = field(default_factory=list)        # mellanled för fliken Beräkningar
    anvanda: set = field(default_factory=set)             # parameter-id som använts
    anvanda_tabeller: set = field(default_factory=set)
    bta_i_drift_bostad: dict = field(default_factory=dict)

    def __post_init__(self):
        p = self.scen["projekt"]
        self.ar = list(range(int(p["startar"]), int(p["slutar"]) + 1))
        self.utv = Utveckling(self.fb, self.scen)
        self._el = self._bygg_elkurva()
        self._fjv = self._bygg_fjvkurva()

    # ---------- parametrar ----------
    def p(self, pid: str) -> float:
        self.anvanda.add(pid)
        egna = self.scen.get("parametrar", {})
        if pid in egna and egna[pid] not in (None, ""):
            return float(egna[pid])
        return self.fb.param(pid)

    def tabell(self, namn: str):
        self.anvanda_tabeller.add(namn)

    # ---------- tidskurvor ----------
    def _bygg_elkurva(self):
        self.tabell("utveckling")
        return self.p("el.startvarde")

    def _bygg_fjvkurva(self):
        self.anvanda.add("fjv.startvarde")
        return float(self.scen["fjarrvarme"]["startvarde"])

    def el(self, y: int) -> float:
        """Elens klimatfaktor, g CO2e/kWh: startvärdet 2026 gånger index för el."""
        return self._el * self.utv.index("el", y)

    def fjv(self, y: int) -> float:
        """Fjärrvärmens klimatfaktor, g CO2e/kWh: ortens startvärde gånger index för fjärrvärme."""
        return self._fjv * self.utv.index("fjv", y)

    def index(self, faktor: str, y: int) -> float:
        """Index relativt 2026 för en emissionsfaktor (fliken Emissionsfaktorer över tid)."""
        return self.utv.index(faktor, y)

    # ---------- resultat ----------
    def add(self, kategori: str, delpost: str, modul: str, y: int, t: float):
        if t and self.ar[0] <= y <= self.ar[-1]:
            self.rader.append({"ar": int(y), "kategori": kategori, "delpost": delpost, "modul": modul, "t": float(t)})

    def add_utanfor(self, delpost: str, modul: str, y: int, t: float):
        if t and self.ar[0] <= y <= self.ar[-1]:
            self.utanfor.append({"ar": int(y), "delpost": delpost, "modul": modul, "t": float(t)})

    def steg(self, modul: str, rubrik: str, varde, enhet: str = "", kommentar: str = ""):
        self.spar.append({"modul": modul, "rubrik": rubrik, "varde": varde, "enhet": enhet, "kommentar": kommentar})
