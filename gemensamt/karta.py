"""Karta med DeSO-områden och OpenStreetMap i bakgrunden, gemensam för Road2Zero-Plan och Road2Zero-CityScenario.

Kartan är en Streamlit-komponent (st.components.v2) med Leaflet 1.9.4 inbäddat, så att den fungerar utan extra paket.
Bakgrundskartan hämtas från OpenStreetMap i användarens webbläsare. Ett klick på en DeSO skickas tillbaka till Python,
där sidan bestämmer vad klicket gör (till exempel lägger till eller tar bort DeSO i planområdet).
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from . import geodata

MAPP = Path(__file__).resolve().parent / "leaflet"
OSM = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OSM_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>-bidragsgivare'

_JS = r"""
export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const L = window.L;
  let rot = parentElement.querySelector('.r2z-karta');
  if (!rot) {
    rot = document.createElement('div');
    rot.className = 'r2z-karta';
    parentElement.appendChild(rot);
  }
  rot.style.height = data.hojd + 'px';
  let s = parentElement.__r2z;
  if (!s || s.sig !== data.sig) {
    if (s) { s.map.remove(); }
    const map = L.map(rot, { scrollWheelZoom: false, zoomSnap: 0.25 });
    L.tileLayer(data.osm, { maxZoom: 19, attribution: data.attr }).addTo(map);
    const lager = {};
    const grupp = L.featureGroup().addTo(map);
    for (const o of data.omraden) {
      const delar = o.ringar.map(r => [r.map(p => [p[1], p[0]])]);
      const poly = L.polygon(delar, { weight: 0.7, color: '#4b6b64', fillOpacity: 0.03, fillColor: '#ffffff' });
      poly.bindTooltip(o.tips, { sticky: true, direction: 'top', className: 'r2z-tips' });
      poly.on('click', () => { if (s && s.valbar) { setTriggerValue('klick', o.kod + '|' + Date.now()); } });
      poly.addTo(grupp);
      lager[o.kod] = poly;
    }
    const legend = L.control({ position: 'bottomleft' });
    legend.onAdd = () => { const d = L.DomUtil.create('div', 'r2z-legend'); return d; };
    legend.addTo(map);
    s = parentElement.__r2z = { sig: data.sig, map, lager, grupp, legend, anpassad: false };
    setTimeout(() => map.invalidateSize(), 50);
  }
  s.valbar = data.valbar;
  const farg = {};
  for (const g of data.lager) { for (const kod of g.koder) { (farg[kod] = farg[kod] || []).push(g.farg); } }
  const valda = [];
  for (const [kod, poly] of Object.entries(s.lager)) {
    const f = farg[kod];
    if (f) {
      poly.setStyle({ weight: 2.4, color: f[0], fillColor: f[0], fillOpacity: f.length > 1 ? 0.5 : 0.32,
                      dashArray: f.length > 1 ? '6 4' : null });
      poly.bringToFront();
      valda.push(poly);
    } else {
      poly.setStyle({ weight: 0.7, color: '#4b6b64', fillColor: '#ffffff', fillOpacity: 0.03, dashArray: null });
    }
  }
  const el = s.legend.getContainer();
  el.innerHTML = data.lager.filter(g => g.koder.length).map(g =>
    `<div><span style="background:${g.farg}"></span>${g.namn}</div>`).join('') +
    (data.valbar ? '<div class="r2z-hint">Klicka på en DeSO för att lägga till eller ta bort den.</div>' : '');
  el.style.display = el.innerHTML ? 'block' : 'none';
  if (!s.anpassad || s.fokus !== data.fokus) {
    const b = valda.length ? L.featureGroup(valda).getBounds() : s.grupp.getBounds();
    if (b.isValid()) { s.map.fitBounds(b, { padding: [24, 24], maxZoom: valda.length ? 15 : 13 }); }
    s.anpassad = true; s.fokus = data.fokus;
  }
  setTimeout(() => s.map.invalidateSize(), 50);
}
"""

_CSS = """
.r2z-karta {width: 100%; border-radius: 12px; border: 1px solid #dce3de; overflow: hidden; background: #eef2ef;}
.r2z-legend {background: rgba(255,255,255,.94); border-radius: 8px; padding: 8px 10px; font: 12px/1.45 system-ui, sans-serif;
  color: #283f44; box-shadow: 0 1px 4px rgba(0,0,0,.15); max-width: 260px;}
.r2z-legend span {display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 7px; vertical-align: -1px;}
.r2z-hint {color: #647579; margin-top: 3px;}
.r2z-tips {font: 12px/1.4 system-ui, sans-serif; color: #183b3b;}
"""


@st.cache_resource
def _komponent():
    js = (MAPP / "leaflet.js").read_text(encoding="utf-8") + "\n" + _JS
    css = (MAPP / "leaflet.css").read_text(encoding="utf-8") + _CSS
    return st.components.v2.component("road2zero_karta", js=js, css=css, isolate_styles=False)


def _sv(x: float, d: int = 0) -> str:
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


def _tips(d: dict) -> str:
    return (f"<b>{d['kod']}</b><br>{d['namn']}<br>{_sv(d['invanare'])} invånare · {_sv(d['hushall'])} hushåll<br>"
            f"{_sv(d['bilar_per_hushall'], 2)} bilar per hushåll · {_sv(d['km_per_bil'])} km per bil")


def karta(kommuner: list[str], lager: list[dict], *, nyckel: str, valbar: bool = False, on_klick=None, hojd: int = 540,
          fokus: str = "") -> str | None:
    """Ritar kommunernas DeSO med lagren ovanpå.

    lager: [{"namn": "Planområdet", "farg": "#167567", "koder": ["1280C1780", ...]}].
    valbar: klick på en DeSO anropar on_klick (som kan läsa DeSO-koden med klickad(nyckel)).
    fokus: ändras värdet zoomar kartan om till lagren.
    Returnerar koden för den DeSO som klickades i den här körningen, annars None."""
    kommuner = [k for k in dict.fromkeys(kommuner) if k]
    omraden = [{"kod": d["kod"], "ringar": d["ringar"], "tips": _tips(d)} for k in kommuner for d in geodata.deso(k)]
    data = {"omraden": omraden, "lager": [{**g, "koder": geodata.giltiga(g["koder"])} for g in lager], "valbar": valbar,
            "hojd": hojd, "sig": ",".join(kommuner), "fokus": fokus, "osm": OSM, "attr": OSM_ATTR}
    res = _komponent()(key=nyckel, data=data, height=hojd + 4, on_klick_change=on_klick or (lambda: None))
    return klickad(res)


def klickad(res_eller_nyckel) -> str | None:
    """DeSO-koden från det senaste klicket (komponentens resultat eller dess nyckel i sessionen)."""
    res = st.session_state.get(res_eller_nyckel) if isinstance(res_eller_nyckel, str) else res_eller_nyckel
    if res is None:
        return None
    v = res.get("klick") if hasattr(res, "get") else getattr(res, "klick", None)
    return str(v).split("|")[0] if v else None
