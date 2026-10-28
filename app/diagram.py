"""Gemensam diagramstil: dov färgskala i petrol, turkos, grönt och blått, typsnitt, rutnät och layout för alla Plotly-diagram.

Kategorifärgerna står i road2zero.konstanter.KATEGORIER. Intilliggande kategorier är kontrollerade för färgblindhet
(protanopi och deuteranopi, Machado m.fl. 2009) med minst ΔE 15 i OKLab, så att staplade staplar går att skilja åt.
"""
from __future__ import annotations

import plotly.graph_objects as go

INK = "#15211d"; INK2 = "#56635e"; GRID = "#e3e9e6"; SURF = "#fbfcfb"; LINJE = "#c9d4cf"
FONT = dict(family="Inter, system-ui, sans-serif", size=13, color=INK)
CONF = {"displaylogo": False, "locale": "sv", "toImageButtonOptions": {"format": "png", "scale": 2}}

# Färger för linjer som inte är klimatkategorier
PETROL, TURKOS, BLA, MELLANBLA, MOSSA, SKIFFER = "#1f5a6e", "#4fa8a0", "#2c6e9e", "#5a86b8", "#7aa65a", "#5c6f78"
BUDGET = "#2f6b3f"          # budget och negativa utsläpp: skogsgrön
VARNING = "#a4442c"         # budgeten förbrukad


def rgba(h: str, a: float) -> str:
    return f"rgba({int(h[1:3], 16)},{int(h[3:5], 16)},{int(h[5:7], 16)},{a})"


def layout(fig: go.Figure, titel: str, undertitel: str = "", hojd: int = 420, yt: str | None = "t CO2e") -> go.Figure:
    fig.update_layout(
        title=dict(text=f"<b>{titel}</b>" + (f"<br><span style='font-size:12px;color:{INK2}'>{undertitel}</span>" if undertitel else ""),
                   x=0, xanchor="left", font=dict(size=16, color=INK)),
        font=FONT, height=hojd, plot_bgcolor=SURF, paper_bgcolor=SURF, margin=dict(l=10, r=10, t=72, b=10),
        legend=dict(orientation="h", yanchor="top", y=-0.2, x=0, title=None, font=dict(size=12)),
        hoverlabel=dict(bgcolor="white", bordercolor=LINJE, font_size=12, font_color=INK), separators=", ",
    )
    fig.update_xaxes(showgrid=False, linecolor=LINJE, tickcolor=LINJE)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=INK2, zerolinewidth=1, title=yt, tickformat=",.0f")
    return fig
