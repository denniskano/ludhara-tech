#!/usr/bin/env python3
"""Cover slide: Databricks + Data Factory vs Apache Flink on Confluent Cloud (SVG + PNG)."""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ICONS = HERE / ".icons"
RESVG_TOOLS = HERE.parent / "docs" / "assets" / "_tools"
OUT_SVG = HERE / "portada-databricks-vs-flink-confluent.svg"
OUT_PNG = HERE / "portada-databricks-vs-flink-confluent.png"

W, H = 1920, 1080
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"
NAVY = "#0B1F3A"
INK = "#1A1A1A"
MUTED = "#5B6472"
CONFLUENT = "#0A6CFF"
FLINK = "#E6526F"
GOOD = "#0F8A5F"
BAD = "#B54848"
BEFORE_BG = "#F3F4F6"
BEFORE_STROKE = "#C9CDD4"


def img(name: str, x, y, w, h) -> str:
    data = base64.b64encode((ICONS / name).read_bytes()).decode("ascii")
    return (f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" '
            f'href="data:image/svg+xml;base64,{data}"/>')


def text(x, y, s, size=20, color=INK, weight=400, anchor="start", spacing=0) -> str:
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
            f'fill="{color}" text-anchor="{anchor}"{ls}>{s}</text>')


def rect(x, y, w, h, fill, stroke="none", r=16, sw=2, dash="", extra="") -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}"{d} {extra}/>')


def node(x, y, w, h, icon, title, sub, stroke, fill="#FFFFFF", icon_size=52) -> str:
    out = [rect(x, y, w, h, fill, stroke, r=14, sw=2, extra='filter="url(#shadow)"')]
    out.append(img(icon, x + 20, y + (h - icon_size) / 2, icon_size, icon_size))
    tx = x + 20 + icon_size + 16
    out.append(text(tx, y + h / 2 - 4, title, 22, INK, 700))
    out.append(text(tx, y + h / 2 + 22, sub, 16, MUTED))
    return "\n".join(out)


def arrow(points, color, width=4, dash="", marker="arrow") -> str:
    d = " ".join(("M" if i == 0 else "L") + f"{px},{py}" for i, (px, py) in enumerate(points))
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" '
            f'stroke-linejoin="round"{da} marker-end="url(#{marker})"/>')


def pill(x, y, label, color, fill) -> str:
    w = 16 + len(label) * 9.6
    return rect(x, y, w, 34, fill, color, r=17, sw=1.5) + text(x + w / 2, y + 23, label, 16, color, 600, "middle")


def bullet(x, y, ok: bool, s: str) -> str:
    c = GOOD if ok else BAD
    mark = "✓" if ok else "✕"
    return (f'<circle cx="{x + 13}" cy="{y - 7}" r="13" fill="{c}"/>'
            + text(x + 13, y - 1, mark, 16, "#FFFFFF", 700, "middle")
            + text(x + 40, y, s, 21, INK))


def logo_tile(cx, cy, icon, label, size=96, stroke="#D6E4FF", fill="#FFFFFF", label_color=INK, pad=28) -> str:
    w = size + pad * 2
    h = size + pad * 2
    x, y = cx - w / 2, cy - h / 2
    return "\n".join([
        rect(x, y, w, h, fill, stroke, r=24, sw=2, extra='filter="url(#shadow)"'),
        img(icon, cx - size / 2, cy - size / 2, size, size),
        text(cx, y + h + 34, label, 22, label_color, 600, "middle"),
    ])


def build() -> str:
    s: list[str] = []
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    s.append(f"""<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#F3F6FB"/>
  </linearGradient>
  <linearGradient id="now" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#F2F7FF"/><stop offset="1" stop-color="#FDF2F5"/>
  </linearGradient>
  <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{CONFLUENT}"/><stop offset="1" stop-color="{FLINK}"/>
  </linearGradient>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="160%">
    <feDropShadow dx="0" dy="6" stdDeviation="10" flood-color="#0B1F3A" flood-opacity="0.12"/>
  </filter>
  <marker id="arrowBad" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
    <path d="M0,0 L10,5 L0,10 z" fill="#B9BEC7"/>
  </marker>
  <marker id="arrowNow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
    <path d="M0,0 L10,5 L0,10 z" fill="{CONFLUENT}"/>
  </marker>
  <marker id="arrowFlink" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
    <path d="M0,0 L10,5 L0,10 z" fill="{FLINK}"/>
  </marker>
</defs>""")
    s.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')
    s.append(f'<rect x="0" y="0" width="{W}" height="12" fill="url(#accent)"/>')

    # Title
    s.append(text(W / 2, 150, "Procesa los datos donde ya viven", 76, NAVY, 700, "middle"))
    s.append(text(W / 2, 206, "De Databricks + Data Factory a Apache Flink en Confluent Cloud", 30, MUTED, 400, "middle"))

    # ----- ANTES (muted, compact) -----
    y0 = 300
    s.append(rect(260, y0, 1400, 190, "#F1F2F4", "none", r=28))
    s.append(text(300, y0 + 50, "ANTES", 20, "#8A919C", 700, spacing=3))
    row = y0 + 108
    s.append(f'<g opacity="0.55">')
    s.append(img("kafka.svg", 520, row - 32, 64, 64))
    s.append(img("adf.svg", 840, row - 34, 68, 68))
    s.append(img("databricks.svg", 1012, row - 34, 68, 68))
    s.append(img("kafka.svg", 1336, row - 32, 64, 64))
    s.append("</g>")
    s.append(arrow([(608, row), (812, row)], "#B9BEC7", 5, "", "arrowBad"))
    s.append(arrow([(1108, row), (1312, row)], "#B9BEC7", 5, "", "arrowBad"))
    s.append(text(960, y0 + 168, "Los datos salen de Kafka, se procesan por lotes y vuelven", 22, "#8A919C", 400, "middle"))

    # ----- AHORA (hero) -----
    y1 = 540
    s.append(rect(257, y1 - 3, 1406, 336, "url(#accent)", r=33, extra='filter="url(#shadow)"'))
    s.append(rect(260, y1, 1400, 330, "url(#now)", r=30))
    s.append(text(300, y1 + 54, "AHORA", 20, CONFLUENT, 700, spacing=3))
    s.append(img("confluent-logo.svg", 1440, y1 + 28, 180, 35))
    hero = y1 + 170
    s.append(logo_tile(560, hero, "kafka.svg", "Tópicos Kafka", size=84))
    s.append(logo_tile(960, hero - 6, "flink.svg", "Apache Flink", size=130, stroke=FLINK, pad=30))
    s.append(logo_tile(1360, hero, "kafka.svg", "Tópicos Kafka", size=84))
    s.append(arrow([(640, hero), (848, hero)], CONFLUENT, 7, "", "arrowNow"))
    s.append(arrow([(1072, hero), (1270, hero)], FLINK, 7, "", "arrowFlink"))

    # Footer: three short promises
    fy = 960
    sep = f'<tspan fill="{FLINK}">&#160;&#160;&#160;•&#160;&#160;&#160;</tspan>'
    s.append(text(W / 2, fy, f"Tiempo real{sep}Los datos no salen{sep}Una sola plataforma", 36, NAVY, 700, "middle"))

    s.append("</svg>")
    return "\n".join(s)


def render_png() -> None:
    script = f"""
const fs = require('fs');
const {{ Resvg }} = require('@resvg/resvg-js');
const svg = fs.readFileSync({str(OUT_SVG)!r});
const r = new Resvg(svg, {{ fitTo: {{ mode: 'width', value: {W * 2} }}, font: {{ loadSystemFonts: true, defaultFontFamily: 'Helvetica' }} }});
fs.writeFileSync({str(OUT_PNG)!r}, r.render().asPng());
"""
    subprocess.run(["node", "-e", script], check=True, cwd=str(RESVG_TOOLS))


if __name__ == "__main__":
    OUT_SVG.write_text(build(), encoding="utf-8")
    render_png()
    print("ok", OUT_SVG.name, OUT_PNG.name)
