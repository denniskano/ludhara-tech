#!/usr/bin/env python3
"""Generate drawio + PNG for plan-retiro diagrams."""

from __future__ import annotations

import io
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent
ICON_CACHE = ASSETS / ".icons"
ICON_CACHE.mkdir(exist_ok=True)

# Restrained palette (same family as grafana-temporal diagrams)
INK = (26, 26, 26)
MUTED = (85, 85, 85)
LINE = (102, 102, 102)
LANE_GREEN = (238, 242, 239)
LANE_GREEN_STROKE = (31, 78, 61)
LANE_STEEL = (240, 244, 248)
LANE_STEEL_STROKE = (61, 90, 115)
LANE_AMBER = (247, 243, 236)
LANE_AMBER_STROKE = (138, 90, 18)
LANE_ROSE = (248, 242, 242)
LANE_ROSE_STROKE = (120, 60, 60)
WHITE = (255, 255, 255)
BOX = (255, 255, 255)
BOX_STROKE = (102, 102, 102)
ACCENT_FILL = (243, 246, 244)

ICONS = {
    "kubernetes": "326CE5",
    "temporal": "000000",
    "microsoftazure": "0078D4",
    "postgresql": "4169E1",
    "elasticsearch": "005571",
    "opensearch": "005EB8",
    "dapr": "0D2192",
    "azurefunctions": "0062AD",
    "microsoft": "737373",
    "openjdk": "437291",
    "grafana": "F46800",
    "prometheus": "E6522C",
    "rabbitmq": "FF6600",
    "azurepipelines": "2560E0",
}


def _fallback_icon(name: str, color: str, size: int) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hexc = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
    d.rounded_rectangle((2, 2, size - 3, size - 3), radius=8, fill=hexc + (255,))
    return im


def fetch_icon(name: str, color: str, size: int = 48) -> Image.Image:
    dest_svg = ICON_CACHE / f"{name}-{color}.svg"
    dest_png = ICON_CACHE / f"{name}-{color}-{size}.png"
    if dest_png.exists():
        return Image.open(dest_png).convert("RGBA")
    urls = (
        f"https://cdn.simpleicons.org/{name}/{color}",
        f"https://cdn.jsdelivr.net/npm/simple-icons@13.21.0/icons/{name}.svg",
    )
    if not dest_svg.exists():
        data = b""
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "ludhara-tech-docs/1.0"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    data = r.read()
                if data and (b"<svg" in data or data.startswith(b"<?xml")):
                    if f"cdn.jsdelivr" in url:
                        svg = data.decode("utf-8")
                        svg = svg.replace("<svg", f'<svg fill="#{color}"', 1)
                        data = svg.encode("utf-8")
                    dest_svg.write_bytes(data)
                    break
            except Exception:
                continue
        if not dest_svg.exists():
            im = _fallback_icon(name, color, size)
            im.save(dest_png)
            return im
    # resvg if present; else qlmanage; else fallback
    if dest_png.exists():
        return Image.open(dest_png).convert("RGBA")
    try:
        from resvg import render  # type: ignore
    except Exception:
        pass
    # qlmanage
    try:
        subprocess.run(
            ["qlmanage", "-t", "-s", str(size * 2), "-o", str(ICON_CACHE), str(dest_svg)],
            check=True,
            capture_output=True,
        )
        ql = ICON_CACHE / f"{dest_svg.name}.png"
        if ql.exists():
            im = Image.open(ql).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
            im.save(dest_png)
            return im
    except Exception:
        pass
    # node resvg
    try:
        script = f"""
const fs = require('fs');
const {{ Resvg }} = require('@resvg/resvg-js');
const svg = fs.readFileSync({str(dest_svg)!r});
const r = new Resvg(svg, {{ fitTo: {{ mode: 'width', value: {size} }} }});
fs.writeFileSync({str(dest_png)!r}, r.render().asPng());
"""
        tmp = ICON_CACHE / "_raster.js"
        tmp.write_text(script)
        tools = ASSETS / "_tools"
        subprocess.run(
            ["node", str(tmp)],
            check=True,
            capture_output=True,
            cwd=str(tools if (tools / "node_modules" / "@resvg" / "resvg-js").exists() else ICON_CACHE),
        )
        if dest_png.exists():
            return Image.open(dest_png).convert("RGBA")
    except Exception:
        pass
    # fallback: tinted square
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hexc = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
    d.rounded_rectangle((2, 2, size - 3, size - 3), radius=8, fill=hexc + (255,))
    im.save(dest_png)
    return im


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def drawio_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "&#xa;")
    )


def icon_url(name: str) -> str:
    return f"https://cdn.simpleicons.org/{name}/{ICONS[name]}"


class Drawio:
    def __init__(self, name: str, width: int, height: int):
        self.name = name
        self.width = width
        self.height = height
        self.cells: list[str] = []
        self.n = 2

    def _id(self) -> str:
        i = f"c{self.n}"
        self.n += 1
        return i

    def add(self, xml: str) -> None:
        self.cells.append(xml)

    def lane(self, title: str, x, y, w, h, fill, stroke, font_c=None) -> str:
        i = self._id()
        self.add(
            f'<mxCell id="{i}" value="{drawio_escape(title)}" '
            f'style="swimlane;horizontal=1;startSize=32;fillColor={fill};strokeColor={stroke};'
            f'fontColor={stroke};fontStyle=1;fontSize=13;fontFamily=Helvetica;" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        return i

    def box(self, text: str, x, y, w, h, parent="1", fill="#FFFFFF", stroke="#666666", bold=False) -> str:
        i = self._id()
        fs = "1" if bold else "0"
        self.add(
            f'<mxCell id="{i}" value="{drawio_escape(text)}" '
            f'style="rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};'
            f'fontStyle={fs};fontSize=12;fontFamily=Helvetica;align=left;spacingLeft=10;verticalAlign=middle;" '
            f'vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        return i

    def icon(self, name: str, x, y, parent="1", size=22) -> str:
        i = self._id()
        self.add(
            f'<mxCell id="{i}" value="" style="shape=image;html=1;imageAspect=0;aspect=fixed;'
            f'image={icon_url(name)};" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{size}" height="{size}" as="geometry"/></mxCell>'
        )
        return i

    def label(self, text: str, x, y, w, h, parent="1", size=12, color="#1a1a1a", bold=False) -> str:
        i = self._id()
        fs = "1" if bold else "0"
        self.add(
            f'<mxCell id="{i}" value="{drawio_escape(text)}" '
            f'style="text;html=1;align=left;fontSize={size};fontColor={color};fontStyle={fs};'
            f'fontFamily=Helvetica;" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        return i

    def edge(self, src: str, tgt: str, parent="1", dashed=False, color="#555555", label="") -> str:
        i = self._id()
        dash = "dashed=1;" if dashed else ""
        lab = f'value="{drawio_escape(label)}";' if label else ""
        self.add(
            f'<mxCell id="{i}" {lab} style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;'
            f'endArrow=block;endFill=1;strokeColor={color};strokeWidth=2;{dash}'
            f'fontSize=10;fontColor=#555555;" edge="1" parent="{parent}" source="{src}" target="{tgt}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>'
        )
        return i

    def write(self, path: Path) -> None:
        body = "\n".join(self.cells)
        xml = f"""<mxfile host="app.diagrams.net" agent="Cursor" version="22.1.11">
  <diagram id="{path.stem}" name="{self.name}">
    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{self.width}" pageHeight="{self.height}" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{body}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
"""
        path.write_text(xml, encoding="utf-8")


class Canvas:
    def __init__(self, w: int, h: int, scale: int = 2):
        self.w, self.h, self.scale = w, h, scale
        self.im = Image.new("RGB", (w * scale, h * scale), WHITE)
        self.d = ImageDraw.Draw(self.im)
        self.boxes: dict[str, tuple[int, int, int, int]] = {}

    def _xy(self, *a):
        return tuple(int(x * self.scale) for x in a)

    def rect(self, x, y, w, h, fill, stroke, radius=8, width=2):
        self.d.rounded_rectangle(
            self._xy(x, y, x + w, y + h),
            radius=radius * self.scale,
            fill=fill,
            outline=stroke,
            width=width * self.scale,
        )

    def text(self, x, y, s, size=13, color=INK, bold=False, anchor="lt"):
        self.d.text(self._xy(x, y), s, font=font(size * self.scale, bold), fill=color, anchor=anchor)

    def icon(self, name: str, x, y, size=22):
        im = fetch_icon(name, ICONS[name], size=size * self.scale)
        self.im.paste(im, self._xy(x, y), im)

    def box(self, key, x, y, w, h, title, sub="", fill=BOX, stroke=BOX_STROKE, icons=()):
        self.rect(x, y, w, h, fill, stroke, radius=6)
        ix = x + 10
        for n in icons:
            self.icon(n, ix, y + (h - 22) / 2, 22)
            ix += 26
        tx = ix if icons else x + 12
        if sub:
            self.text(tx, y + 10, title, 13, INK, bold=True)
            self.text(tx, y + 30, sub, 11, MUTED)
        else:
            self.text(tx, y + h / 2, title, 13, INK, bold=True, anchor="lm")
        self.boxes[key] = (x, y, w, h)

    def lane(self, x, y, w, h, title, fill, stroke):
        self.rect(x, y, w, h, fill, stroke, radius=4)
        self.text(x + 12, y + 8, title, 13, stroke, bold=True)

    def arrow(self, a, b, dashed=False, color=LINE, label=""):
        ax, ay, aw, ah = self.boxes[a]
        bx, by, bw, bh = self.boxes[b]
        x1, y1 = ax + aw, ay + ah / 2
        x2, y2 = bx, by + bh / 2
        # vertical if roughly stacked
        if abs((ax + aw / 2) - (bx + bw / 2)) < 40 and by > ay:
            x1, y1 = ax + aw / 2, ay + ah
            x2, y2 = bx + bw / 2, by
        p1 = self._xy(x1, y1)
        p2 = self._xy(x2, y2)
        w = 2 * self.scale
        if dashed:
            self._dashed_line(p1, p2, color, w)
        else:
            self.d.line([p1, p2], fill=color, width=w)
        self._arrow_head(p2, p1, color)
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 10
            self.text(mx, my, label, 10, MUTED, anchor="mm")

    def _dashed_line(self, p1, p2, color, width):
        x1, y1 = p1
        x2, y2 = p2
        segs = 18
        for i in range(0, segs, 2):
            t0, t1 = i / segs, (i + 1) / segs
            self.d.line(
                [(x1 + (x2 - x1) * t0, y1 + (y2 - y1) * t0), (x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1)],
                fill=color,
                width=width,
            )

    def _arrow_head(self, tip, tail, color):
        import math

        tx, ty = tip
        ax, ay = tail
        ang = math.atan2(ty - ay, tx - ax)
        L = 9 * self.scale
        pts = [
            (tx, ty),
            (tx - L * math.cos(ang - 0.4), ty - L * math.sin(ang - 0.4)),
            (tx - L * math.cos(ang + 0.4), ty - L * math.sin(ang + 0.4)),
        ]
        self.d.polygon(pts, fill=color)

    def save(self, path: Path) -> None:
        path.write_bytes(b"")  # touch
        self.im.save(path, "PNG")


def build_04_1():
    W, H = 1600, 620
    d = Drawio("Arquitectura Self-Hosted", W, H)
    d.label("Temporal Self-Hosted en Azure AKS", 36, 16, 700, 26, size=18, bold=True)
    d.label("PEVE opera el control plane. Workers en el AKS de la aplicación. Sin internet público.", 36, 44, 900, 18, size=12, color="#555555")

    apps = d.lane("Application plane — BCP", 36, 76, 380, 500, "#EEF2EF", "#1F4E3D")
    d.icon("openjdk", 16, 42, apps)
    d.icon("kubernetes", 44, 42, apps)
    a1 = d.box("APOQ · NREM · demás", 24, 76, 332, 56, apps, bold=True)
    a2 = d.box("Workers AKS\nJava + Temporal SDK", 24, 168, 332, 56, apps)
    d.icon("temporal", 16, 156, apps, 18)
    a3 = d.box("Core · outbox · colas", 24, 260, 332, 56, apps)
    d.icon("rabbitmq", 16, 248, apps, 18)
    d.edge(a1, a2, apps, color="#1F4E3D")
    d.edge(a2, a3, apps, color="#1F4E3D")

    cp = d.lane("Control plane Temporal — AKS PEVE", 440, 76, 560, 500, "#F0F4F8", "#3D5A73")
    d.icon("temporal", 16, 42, cp)
    d.icon("kubernetes", 44, 42, cp)
    d.icon("microsoftazure", 72, 42, cp)
    b0 = d.box("Internal load balancer\nPrivate Link · no public IP", 24, 76, 512, 52, cp)
    b1 = d.box("Frontend  gRPC / mTLS", 24, 156, 512, 44, cp)
    b2 = d.box("History", 24, 228, 160, 44, cp)
    b3 = d.box("Matching", 200, 228, 160, 44, cp)
    b4 = d.box("Worker Service", 376, 228, 160, 44, cp)
    b5 = d.box("Admin UI", 24, 300, 512, 44, cp)
    d.edge(b0, b1, cp, color="#3D5A73")
    d.edge(b1, b2, cp, color="#3D5A73")
    d.edge(b1, b3, cp, color="#3D5A73")
    d.edge(b1, b4, cp, color="#3D5A73")
    d.edge(b5, b1, cp, dashed=True, color="#888888")

    az = d.lane("Azure privada", 1024, 76, 540, 500, "#F7F3EC", "#8A5A12")
    d.icon("microsoftazure", 16, 42, az)
    c1 = d.box("PostgreSQL\npersistence · Flexible Server", 24, 76, 492, 56, az)
    d.icon("postgresql", 16, 64, az, 18)
    c2 = d.box("Elasticsearch / OpenSearch\nvisibility", 24, 156, 492, 56, az)
    d.icon("elasticsearch", 16, 144, az, 18)
    d.icon("opensearch", 40, 144, az, 18)
    c3 = d.box("Blob\narchival / export", 24, 236, 492, 56, az)
    d.icon("microsoftazure", 16, 224, az, 18)
    c4 = d.box("Key Vault  ·  identidades", 24, 316, 492, 48, az)
    c5 = d.box("Monitor / alerts", 24, 388, 492, 48, az)
    d.icon("grafana", 16, 376, az, 18)

    d.edge(a2, b0, color="#1F4E3D", label="gRPC mTLS")
    d.edge(b2, c1, color="#8A5A12")
    d.edge(b3, c1, color="#8A5A12")
    d.edge(b1, c2, color="#8A5A12")
    d.edge(b4, c3, color="#8A5A12")
    d.edge(b1, c4, color="#8A5A12")

    d.write(ASSETS / "04-1-arquitectura-self-hosted.drawio")

    c = Canvas(W, H)
    c.text(36, 16, "Temporal Self-Hosted en Azure AKS", 18, bold=True)
    c.text(36, 44, "PEVE opera el control plane. Workers en el AKS de la aplicación. Sin internet público.", 12, MUTED)
    c.lane(36, 76, 380, 500, "Application plane — BCP", LANE_GREEN, LANE_GREEN_STROKE)
    c.icon("openjdk", 52, 118)
    c.icon("kubernetes", 80, 118)
    c.box("a1", 60, 152, 332, 56, "APOQ · NREM · demás", icons=("openjdk",))
    c.box("a2", 60, 244, 332, 64, "Workers AKS", "Java + Temporal SDK", icons=("kubernetes", "temporal"))
    c.box("a3", 60, 344, 332, 56, "Core · outbox · colas", icons=("rabbitmq",))
    c.arrow("a1", "a2", color=LANE_GREEN_STROKE)
    c.arrow("a2", "a3", color=LANE_GREEN_STROKE)

    c.lane(440, 76, 560, 500, "Control plane Temporal — AKS PEVE", LANE_STEEL, LANE_STEEL_STROKE)
    c.icon("temporal", 456, 118)
    c.icon("kubernetes", 484, 118)
    c.icon("microsoftazure", 512, 118)
    c.box("b0", 464, 152, 512, 52, "Internal load balancer", "Private Link · no public IP")
    c.box("b1", 464, 228, 512, 44, "Frontend  gRPC / mTLS", icons=("temporal",))
    c.box("b2", 464, 300, 160, 48, "History")
    c.box("b3", 640, 300, 160, 48, "Matching")
    c.box("b4", 816, 300, 160, 48, "Worker Service")
    c.box("b5", 464, 372, 512, 44, "Admin UI")
    c.arrow("b0", "b1", color=LANE_STEEL_STROKE)
    c.arrow("b1", "b2", color=LANE_STEEL_STROKE)
    c.arrow("b1", "b3", color=LANE_STEEL_STROKE)
    c.arrow("b1", "b4", color=LANE_STEEL_STROKE)
    c.arrow("b5", "b1", dashed=True, color=(136, 136, 136))

    c.lane(1024, 76, 540, 500, "Azure privada", LANE_AMBER, LANE_AMBER_STROKE)
    c.icon("microsoftazure", 1040, 118)
    c.box("c1", 1048, 152, 492, 56, "PostgreSQL", "persistence · Flexible Server", icons=("postgresql",))
    c.box("c2", 1048, 228, 492, 56, "Elasticsearch / OpenSearch", "visibility", icons=("elasticsearch", "opensearch"))
    c.box("c3", 1048, 304, 492, 56, "Blob", "archival / export", icons=("microsoftazure",))
    c.box("c4", 1048, 380, 492, 48, "Key Vault  ·  identidades", icons=("microsoftazure",))
    c.box("c5", 1048, 448, 492, 48, "Monitor / alerts", icons=("grafana",))
    c.arrow("a2", "b0", color=LANE_GREEN_STROKE, label="gRPC mTLS")
    c.arrow("b2", "c1", color=LANE_AMBER_STROKE)
    c.arrow("b1", "c2", color=LANE_AMBER_STROKE)
    c.arrow("b4", "c3", color=LANE_AMBER_STROKE)
    c.save(ASSETS / "04-1-arquitectura-self-hosted.png")


def build_04_4():
    W, H = 1400, 420
    d = Drawio("Transición dual", W, H)
    d.label("Conexión dual — mientras Cloud responde", 36, 16, 700, 26, size=18, bold=True)
    d.label("Un workflow o schedule no puede estar activo a la vez en Cloud y en Self-Hosted.", 36, 44, 900, 18, size=12, color="#555555")
    app = d.box("APOQ / NREM", 40, 160, 180, 64, bold=True)
    d.icon("openjdk", 48, 128)
    flag = d.box("Destination\nflag", 300, 160, 180, 64)
    sh = d.box("Self-Hosted AKS\nnew starts", 580, 80, 220, 64, fill="#F3F6F4", stroke="#1F4E3D")
    d.icon("temporal", 588, 48)
    d.icon("kubernetes", 616, 48)
    cloud = d.box("Temporal Cloud\ndrain open executions", 580, 240, 220, 64, fill="#F8F2F2", stroke="#783C3C")
    d.icon("temporal", 588, 208)
    core = d.box("Core / outbox", 880, 160, 180, 64)
    d.icon("rabbitmq", 888, 128)
    blob = d.box("Blob del Banco\nperiodic export", 1160, 240, 200, 64)
    d.icon("microsoftazure", 1168, 208)
    d.edge(app, flag, color="#555555")
    d.edge(flag, sh, color="#1F4E3D", label="new starts")
    d.edge(flag, cloud, color="#783C3C", label="drain")
    d.edge(app, core, color="#555555")
    d.edge(sh, core, color="#1F4E3D")
    d.edge(cloud, blob, dashed=True, color="#888888", label="export")
    d.write(ASSETS / "04-4-transicion-dual.drawio")

    c = Canvas(W, H)
    c.text(36, 16, "Conexión dual — mientras Cloud responde", 18, bold=True)
    c.text(36, 44, "Un workflow o schedule no puede estar activo a la vez en Cloud y en Self-Hosted.", 12, MUTED)
    c.icon("openjdk", 48, 128)
    c.box("app", 40, 160, 180, 64, "APOQ / NREM")
    c.box("flag", 300, 160, 180, 64, "Destination", "flag")
    c.icon("temporal", 588, 48)
    c.icon("kubernetes", 616, 48)
    c.box("sh", 580, 80, 220, 64, "Self-Hosted AKS", "new starts", fill=ACCENT_FILL, stroke=LANE_GREEN_STROKE)
    c.icon("temporal", 588, 208)
    c.box("cloud", 580, 240, 220, 64, "Temporal Cloud", "drain open executions", fill=LANE_ROSE, stroke=LANE_ROSE_STROKE)
    c.icon("rabbitmq", 888, 128)
    c.box("core", 880, 160, 180, 64, "Core / outbox")
    c.icon("microsoftazure", 1168, 208)
    c.box("blob", 1160, 240, 200, 64, "Blob del Banco", "periodic export", icons=("microsoftazure",))
    c.arrow("app", "flag")
    c.arrow("flag", "sh", color=LANE_GREEN_STROKE, label="new starts")
    c.arrow("flag", "cloud", color=LANE_ROSE_STROKE, label="drain")
    c.arrow("app", "core")
    c.arrow("sh", "core", color=LANE_GREEN_STROKE)
    c.arrow("cloud", "blob", dashed=True, label="export")
    c.save(ASSETS / "04-4-transicion-dual.png")


def build_04_5():
    W, H = 1400, 360
    d = Drawio("Modo estresado", W, H)
    d.label("Modo estresado — Temporal Cloud no responde", 36, 16, 800, 26, size=18, bold=True)
    d.label("Sin conexión dual ni exportación. Se reconstruye desde el core.", 36, 44, 800, 18, size=12, color="#555555")
    app = d.box("APOQ / NREM", 40, 140, 180, 64, bold=True)
    d.icon("openjdk", 48, 108)
    w = d.box("Workers AKS", 300, 140, 180, 64)
    d.icon("kubernetes", 308, 108)
    d.icon("temporal", 336, 108)
    sh = d.box("Self-Hosted AKS\nonly target", 560, 80, 220, 64, fill="#F3F6F4", stroke="#1F4E3D")
    core = d.box("Core / outbox / NREM\nrebuild", 560, 200, 220, 64)
    d.icon("rabbitmq", 568, 168)
    dead = d.box("Temporal Cloud\nunavailable", 900, 140, 220, 64, fill="#F8F2F2", stroke="#783C3C")
    x = d.box("no completion\nno export", 1180, 140, 180, 64, fill="#F8F2F2", stroke="#783C3C")
    d.edge(app, w, color="#555555")
    d.edge(w, sh, color="#1F4E3D")
    d.edge(w, core, color="#555555")
    d.edge(dead, x, dashed=True, color="#783C3C", label="sin API")
    d.write(ASSETS / "04-5-modo-estresado.drawio")

    c = Canvas(W, H)
    c.text(36, 16, "Modo estresado — Temporal Cloud no responde", 18, bold=True)
    c.text(36, 44, "Sin conexión dual ni exportación. Se reconstruye desde el core.", 12, MUTED)
    c.icon("openjdk", 48, 108)
    c.box("app", 40, 140, 180, 64, "APOQ / NREM")
    c.icon("kubernetes", 308, 108)
    c.icon("temporal", 336, 108)
    c.box("w", 300, 140, 180, 64, "Workers AKS")
    c.box("sh", 560, 80, 220, 64, "Self-Hosted AKS", "only target", fill=ACCENT_FILL, stroke=LANE_GREEN_STROKE)
    c.icon("rabbitmq", 568, 168)
    c.box("core", 560, 200, 220, 64, "Core / outbox / NREM", "rebuild")
    c.box("dead", 900, 140, 220, 64, "Temporal Cloud", "unavailable", fill=LANE_ROSE, stroke=LANE_ROSE_STROKE)
    c.box("x", 1180, 140, 180, 64, "no completion", "no export", fill=LANE_ROSE, stroke=LANE_ROSE_STROKE)
    c.arrow("app", "w")
    c.arrow("w", "sh", color=LANE_GREEN_STROKE)
    c.arrow("w", "core")
    c.arrow("dead", "x", dashed=True, color=LANE_ROSE_STROKE, label="sin API")
    c.save(ASSETS / "04-5-modo-estresado.png")


def build_04_6_df():
    W, H = 1400, 480
    d = Drawio("Durable Functions", W, H)
    d.label("Opción 1 — Azure Durable Functions", 36, 16, 700, 26, size=18, bold=True)
    d.label("Microsoft opera el control plane (Durable Task Scheduler). Reescritura de APOQ / NREM.", 36, 44, 1000, 18, size=12, color="#555555")
    apps = d.lane("Application plane — BCP", 36, 80, 520, 360, "#EEF2EF", "#1F4E3D")
    d.icon("openjdk", 16, 42, apps)
    a1 = d.box("APOQ / NREM", 24, 70, 472, 52, apps, bold=True)
    a2 = d.box("Activities / functions", 24, 160, 472, 52, apps)
    d.icon("azurefunctions", 16, 148, apps, 18)
    a3 = d.box("Core · outbox · colas", 24, 250, 472, 52, apps)
    d.icon("rabbitmq", 16, 238, apps, 18)
    d.edge(a1, a2, apps, color="#1F4E3D")
    d.edge(a2, a3, apps, color="#1F4E3D")
    az = d.lane("Azure Durable Task", 580, 80, 780, 360, "#F0F4F8", "#3D5A73")
    d.icon("microsoftazure", 16, 42, az)
    d.icon("azurefunctions", 44, 42, az)
    d.icon("microsoft", 72, 42, az)
    b1 = d.box("Durable Functions\no Durable Task SDK", 24, 70, 350, 64, az)
    b2 = d.box("Durable Task Scheduler\nMicrosoft control plane", 400, 70, 350, 64, az, fill="#F3F6F4", stroke="#3D5A73")
    b3 = d.box("Azure Monitor", 24, 200, 350, 52, az)
    d.icon("grafana", 16, 188, az, 18)
    b4 = d.box("Key Vault / Entra", 400, 200, 350, 52, az)
    d.icon("microsoftazure", 392, 188, az, 18)
    d.edge(a2, b1, color="#3D5A73", label="orchestration")
    d.edge(b1, b2, az, color="#3D5A73")
    d.edge(b2, b3, az, color="#3D5A73")
    d.edge(b2, b4, az, color="#3D5A73")
    d.write(ASSETS / "04-6-durable-functions.drawio")

    c = Canvas(W, H)
    c.text(36, 16, "Opción 1 — Azure Durable Functions", 18, bold=True)
    c.text(36, 44, "Microsoft opera el control plane (Durable Task Scheduler). Reescritura de APOQ / NREM.", 12, MUTED)
    c.lane(36, 80, 520, 360, "Application plane — BCP", LANE_GREEN, LANE_GREEN_STROKE)
    c.icon("openjdk", 52, 122)
    c.box("a1", 60, 150, 472, 52, "APOQ / NREM")
    c.icon("azurefunctions", 52, 214)
    c.box("a2", 60, 240, 472, 52, "Activities / functions", icons=("azurefunctions",))
    c.icon("rabbitmq", 52, 304)
    c.box("a3", 60, 330, 472, 52, "Core · outbox · colas", icons=("rabbitmq",))
    c.arrow("a1", "a2", color=LANE_GREEN_STROKE)
    c.arrow("a2", "a3", color=LANE_GREEN_STROKE)
    c.lane(580, 80, 780, 360, "Azure Durable Task", LANE_STEEL, LANE_STEEL_STROKE)
    c.icon("microsoftazure", 596, 122)
    c.icon("azurefunctions", 624, 122)
    c.icon("microsoft", 652, 122)
    c.box("b1", 604, 150, 350, 64, "Durable Functions", "o Durable Task SDK", icons=("azurefunctions",))
    c.box("b2", 980, 150, 350, 64, "Durable Task Scheduler", "Microsoft control plane", fill=ACCENT_FILL, stroke=LANE_STEEL_STROKE, icons=("microsoft",))
    c.box("b3", 604, 280, 350, 52, "Azure Monitor", icons=("grafana",))
    c.box("b4", 980, 280, 350, 52, "Key Vault / Entra", icons=("microsoftazure",))
    c.arrow("a2", "b1", color=LANE_STEEL_STROKE, label="orchestration")
    c.arrow("b1", "b2", color=LANE_STEEL_STROKE)
    c.arrow("b2", "b3", color=LANE_STEEL_STROKE)
    c.arrow("b2", "b4", color=LANE_STEEL_STROKE)
    c.save(ASSETS / "04-6-durable-functions.png")


def build_04_6_dapr():
    W, H = 1400, 480
    d = Drawio("Dapr Workflows", W, H)
    d.label("Opción 2 — Dapr Workflows en AKS", 36, 16, 700, 26, size=18, bold=True)
    d.label("Mismo Durable Task Framework. Cómputo en AKS. State store: PostgreSQL (no Cosmos DB).", 36, 44, 1000, 18, size=12, color="#555555")
    apps = d.lane("Application plane — BCP", 36, 80, 520, 360, "#EEF2EF", "#1F4E3D")
    d.icon("openjdk", 16, 42, apps)
    d.icon("kubernetes", 44, 42, apps)
    a1 = d.box("APOQ / NREM", 24, 70, 472, 52, apps, bold=True)
    a2 = d.box("App + activities en AKS", 24, 160, 472, 52, apps)
    a3 = d.box("Core · outbox · colas", 24, 250, 472, 52, apps)
    d.icon("rabbitmq", 16, 238, apps, 18)
    d.edge(a1, a2, apps, color="#1F4E3D")
    d.edge(a2, a3, apps, color="#1F4E3D")
    dp = d.lane("Dapr en AKS", 580, 80, 780, 360, "#F0F4F8", "#3D5A73")
    d.icon("dapr", 16, 42, dp)
    d.icon("kubernetes", 44, 42, dp)
    d.icon("microsoftazure", 72, 42, dp)
    b1 = d.box("Sidecar daprd", 24, 70, 350, 64, dp)
    b2 = d.box("Workflow engine\n/ scheduler", 400, 70, 350, 64, dp, fill="#F3F6F4", stroke="#3D5A73")
    b3 = d.box("PostgreSQL state store", 24, 200, 350, 52, dp)
    d.icon("postgresql", 16, 188, dp, 18)
    b4 = d.box("Monitor / alerts", 400, 200, 350, 52, dp)
    d.icon("grafana", 392, 188, dp, 18)
    d.edge(a2, b1, color="#3D5A73", label="SDK workflow")
    d.edge(b1, b2, dp, color="#3D5A73")
    d.edge(b2, b3, dp, color="#3D5A73")
    d.edge(b2, b4, dp, color="#3D5A73")
    d.write(ASSETS / "04-6-dapr-workflows.drawio")

    c = Canvas(W, H)
    c.text(36, 16, "Opción 2 — Dapr Workflows en AKS", 18, bold=True)
    c.text(36, 44, "Mismo Durable Task Framework. Cómputo en AKS. State store: PostgreSQL (no Cosmos DB).", 12, MUTED)
    c.lane(36, 80, 520, 360, "Application plane — BCP", LANE_GREEN, LANE_GREEN_STROKE)
    c.icon("openjdk", 52, 122)
    c.icon("kubernetes", 80, 122)
    c.box("a1", 60, 150, 472, 52, "APOQ / NREM")
    c.box("a2", 60, 240, 472, 52, "App + activities en AKS", icons=("kubernetes",))
    c.box("a3", 60, 330, 472, 52, "Core · outbox · colas", icons=("rabbitmq",))
    c.arrow("a1", "a2", color=LANE_GREEN_STROKE)
    c.arrow("a2", "a3", color=LANE_GREEN_STROKE)
    c.lane(580, 80, 780, 360, "Dapr en AKS", LANE_STEEL, LANE_STEEL_STROKE)
    c.icon("dapr", 596, 122)
    c.icon("kubernetes", 624, 122)
    c.icon("microsoftazure", 652, 122)
    c.box("b1", 604, 150, 350, 64, "Sidecar daprd", icons=("dapr",))
    c.box("b2", 980, 150, 350, 64, "Workflow engine", "/ scheduler", fill=ACCENT_FILL, stroke=LANE_STEEL_STROKE)
    c.box("b3", 604, 280, 350, 52, "PostgreSQL state store", icons=("postgresql",))
    c.box("b4", 980, 280, 350, 52, "Monitor / alerts", icons=("grafana",))
    c.arrow("a2", "b1", color=LANE_STEEL_STROKE, label="SDK workflow")
    c.arrow("b1", "b2", color=LANE_STEEL_STROKE)
    c.arrow("b2", "b3", color=LANE_STEEL_STROKE)
    c.arrow("b2", "b4", color=LANE_STEEL_STROKE)
    c.save(ASSETS / "04-6-dapr-workflows.png")


def build_04_6_restate():
    W, H = 1400, 480
    d = Drawio("Restate", W, H)
    d.label("Opción 3 — Restate (Self-Managed en AKS o Cloud Enterprise)", 36, 16, 900, 26, size=18, bold=True)
    d.label("Ejecución durable en código. Preferible Self-Managed + contrato Enterprise.", 36, 44, 900, 18, size=12, color="#555555")
    apps = d.lane("Application plane — BCP", 36, 80, 520, 360, "#EEF2EF", "#1F4E3D")
    d.icon("openjdk", 16, 42, apps)
    d.icon("kubernetes", 44, 42, apps)
    a1 = d.box("APOQ / NREM", 24, 70, 472, 52, apps, bold=True)
    a2 = d.box("Servicios / handlers AKS", 24, 160, 472, 52, apps)
    a3 = d.box("Core · outbox · colas", 24, 250, 472, 52, apps)
    d.icon("rabbitmq", 16, 238, apps, 18)
    d.edge(a1, a2, apps, color="#1F4E3D")
    d.edge(a2, a3, apps, color="#1F4E3D")
    rst = d.lane("Restate", 580, 80, 780, 360, "#F7F3EC", "#8A5A12")
    d.icon("kubernetes", 16, 42, rst)
    d.icon("microsoftazure", 44, 42, rst)
    b1 = d.box("Restate Server\nAKS o Restate Cloud", 24, 70, 350, 64, rst, fill="#F3F6F4", stroke="#8A5A12")
    b2 = d.box("Durable log", 400, 70, 350, 64, rst)
    b3 = d.box("Monitor / alerts", 24, 200, 350, 52, rst)
    d.icon("grafana", 16, 188, rst, 18)
    b4 = d.box("Key Vault", 400, 200, 350, 52, rst)
    d.icon("microsoftazure", 392, 188, rst, 18)
    d.edge(a2, b1, color="#8A5A12", label="SDK Restate")
    d.edge(b1, b2, rst, color="#8A5A12")
    d.edge(b1, b3, rst, color="#8A5A12")
    d.edge(b1, b4, rst, color="#8A5A12")
    d.write(ASSETS / "04-6-restate.drawio")

    c = Canvas(W, H)
    c.text(36, 16, "Opción 3 — Restate (Self-Managed en AKS o Cloud Enterprise)", 18, bold=True)
    c.text(36, 44, "Ejecución durable en código. Preferible Self-Managed + contrato Enterprise.", 12, MUTED)
    c.lane(36, 80, 520, 360, "Application plane — BCP", LANE_GREEN, LANE_GREEN_STROKE)
    c.icon("openjdk", 52, 122)
    c.icon("kubernetes", 80, 122)
    c.box("a1", 60, 150, 472, 52, "APOQ / NREM")
    c.box("a2", 60, 240, 472, 52, "Servicios / handlers AKS", icons=("kubernetes",))
    c.box("a3", 60, 330, 472, 52, "Core · outbox · colas", icons=("rabbitmq",))
    c.arrow("a1", "a2", color=LANE_GREEN_STROKE)
    c.arrow("a2", "a3", color=LANE_GREEN_STROKE)
    c.lane(580, 80, 780, 360, "Restate", LANE_AMBER, LANE_AMBER_STROKE)
    c.icon("kubernetes", 596, 122)
    c.icon("microsoftazure", 624, 122)
    c.box("b1", 604, 150, 350, 64, "Restate Server", "AKS o Restate Cloud", fill=ACCENT_FILL, stroke=LANE_AMBER_STROKE)
    c.box("b2", 980, 150, 350, 64, "Durable log")
    c.box("b3", 604, 280, 350, 52, "Monitor / alerts", icons=("grafana",))
    c.box("b4", 980, 280, 350, 52, "Key Vault", icons=("microsoftazure",))
    c.arrow("a2", "b1", color=LANE_AMBER_STROKE, label="SDK Restate")
    c.arrow("b1", "b2", color=LANE_AMBER_STROKE)
    c.arrow("b1", "b3", color=LANE_AMBER_STROKE)
    c.arrow("b1", "b4", color=LANE_AMBER_STROKE)
    c.save(ASSETS / "04-6-restate.png")


def main():
    # Prefetch icons
    for name, color in ICONS.items():
        try:
            fetch_icon(name, color, 48)
            print("icon", name)
        except Exception as e:
            print("icon fail", name, e)
    build_04_1()
    build_04_4()
    build_04_5()
    build_04_6_df()
    build_04_6_dapr()
    build_04_6_restate()
    print("ok")


if __name__ == "__main__":
    main()
