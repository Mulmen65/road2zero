"""Klimatbudget: stadsdelens andel av den globala kvarvarande koldioxidbudgeten (Forster m.fl. 2026).

1. En global utsläppsbana E(t) som exakt förbrukar budgeten B från 2026: E(t) = E0·(1−r)^(t−2026) med r = E0/B,
   eller en linjär bana ned till noll om B är mindre än ett års utsläpp.
2. Påslag för andra växthusgaser: k = 56,8/43,2, så att budgeten kan jämföras med CO2e.
3. Andel per person och år: k·E(t) delat med världsbefolkningen (UN WPP 2024, medelvariant).
4. Stadsdelens budget per år: faktiska invånare det året gånger andelen per person.
"""
from __future__ import annotations

import pandas as pd

from ..factlib import Kurva
from ..kontext import Kontext

MODUL = "Klimatbudget"


def global_budget(k: Kontext) -> float:
    b = k.scen["budget"]
    d = k.fb.budget
    r = d[(d["temperatur"] == str(b["temperatur"])) & (d["sannolikhet"].astype(int) == int(b["sannolikhet"]))]
    k.tabell("budget_forster2026")
    return float(r.iloc[0]["gt_co2"])


def bana(B: float, E0: float, n: int, y0: int = 2026) -> tuple[list[float], str]:
    if B > E0:
        r = E0 / B
        return [E0 * (1 - r) ** i for i in range(n)], f"Minskar {r*100:.1f} % per år".replace(".", ",")
    T = 2 * B / E0
    out = []
    for i in range(n):
        a, b = min(i, T), min(i + 1, T)
        out.append(E0 * ((b - a) - (b * b - a * a) / (2 * T)))
    return out, f"Linjärt till noll på {T:.1f} år".replace(".", ",")


def berakna(k: Kontext, invanare: dict[int, float], netto: pd.DataFrame) -> dict:
    """netto: DataFrame med kolumnerna ar, niva1, niva2, niva3 (t CO2e per år)."""
    B = global_budget(k)
    E0 = k.p("budget.e0"); kf = k.p("budget.k")
    k.tabell("befolkning_unwpp2024")
    pop = Kurva({float(a): float(v) for a, v in zip(k.fb.befolkning["ar"], k.fb.befolkning["miljarder"])})
    # banan börjar 2026 enligt Forster; år före 2026 får ingen budget
    ar_bana = [y for y in k.ar if y >= 2026]
    E, text = bana(B, E0, len(ar_bana))
    per_person = {y: E[i] * kf / pop(y) for i, y in enumerate(ar_bana)}
    rows = []
    kum_b = 0.0; kum = {1: 0.0, 2: 0.0, 3: 0.0}
    for y in k.ar:
        bud = invanare.get(y, 0.0) * per_person.get(y, 0.0)
        kum_b += bud
        r = netto[netto["ar"] == y]
        rad = {"ar": y, "invanare": invanare.get(y, 0.0), "andel_per_person_t": per_person.get(y, 0.0), "budget_t": bud, "budget_kum_t": kum_b}
        for L in (1, 2, 3):
            v = float(r[f"niva{L}"].iloc[0]) if not r.empty else 0.0
            kum[L] += v
            rad[f"netto_kum_niva{L}"] = kum[L]
        rows.append(rad)
    df = pd.DataFrame(rows)
    total = kum_b
    slut = {}
    for L in (1, 2, 3):
        over = df[df[f"netto_kum_niva{L}"] > total]
        slut[L] = int(over["ar"].iloc[0]) if not over.empty else None
    k.steg(MODUL, "Global budget B", B, "Gt CO2", f"{k.scen['budget']['temperatur']} °C, {k.scen['budget']['sannolikhet']} % sannolikhet")
    k.steg(MODUL, "Global utsläppsbana", text, "", f"E0 = {E0} Gt CO2 år 2025")
    k.steg(MODUL, "Andel per person, hela perioden", round(sum(per_person.values()), 2), "t CO2e", f"med påslag k = {kf:.3f}")
    k.steg(MODUL, "Stadsdelens budget", round(total, 0), "t CO2e", "faktiska invånare år för år")
    for L in (1, 2, 3):
        k.steg(MODUL, f"Budgeten förbrukad, nivå {L}", slut[L] or "inte under perioden", "år")
    return {"tabell": df, "global_gt": B, "bana": text, "per_person_total": sum(per_person.values()), "stadsdel_t": total, "slutar": slut}
