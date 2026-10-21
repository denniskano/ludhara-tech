#!/usr/bin/env python3
"""Architecture diagrams: Kafka / Flink / lakehouse / Databricks."""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ICONS = ROOT / ".icons"
RESVG_TOOLS = ROOT.parent / "docs" / "assets" / "_tools"

W, H = 1600, 900
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"
NAVY = "#0B1F3A"
INK = "#1A1A1A"
MUTED = "#5B6472"
CONFLUENT = "#0A6CFF"
FLINK = "#E6526F"
GOOD = "#0F8A5F"
AMBER = "#8A5A12"


def img(name: str, x, y, w, h) -> str:
    data = base64.b64encode((ICONS / name).read_bytes()).decode("ascii")
    return (
        f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" '
        f'href="data:image/svg+xml;base64,{data}"/>'
    )


def text(x, y, s, size=18, color=INK, weight=400, anchor="start") -> str:
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
        f'fill="{color}" text-anchor="{anchor}">{s}</text>'
    )


def rect(x, y, w, h, fill, stroke="none", r=16, sw=1.5, extra="") -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{sw}" {extra}/>'
    )


def lane(x, y, w, h, title, stroke, fill) -> str:
    return rect(x, y, w, h, fill, stroke, r=18) + text(x + 24, y + 36, title, 18, stroke, 700)


def node(x, y, w, h, icon, title, sub, stroke=MUTED) -> str:
    out = [rect(x, y, w, h, "#FFFFFF", stroke, r=14, extra='filter="url(#shadow)"')]
    out.append(img(icon, x + 16, y + (h - 40) / 2, 40, 40))
    out.append(text(x + 68, y + h / 2 - 2, title, 16, INK, 700))
    out.append(text(x + 68, y + h / 2 + 20, sub, 13, MUTED))
    return "\n".join(out)


def arrow(x1, y1, x2, y2, color=MUTED, label="") -> str:
    out = [
        f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" stroke-width="3" '
        f'stroke-linecap="round" marker-end="url(#arrow)"/>'
    ]
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 10
        out.append(text(mx, my, label, 12, color, 600, "middle"))
    return "\n".join(out)


def defs() -> str:
    return f"""<defs>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="160%">
    <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#0B1F3A" flood-opacity="0.10"/>
  </filter>
  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
    <path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/>
  </marker>
  <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{CONFLUENT}"/><stop offset="1" stop-color="{FLINK}"/>
  </linearGradient>
</defs>"""


def header(title: str, subtitle: str) -> str:
    return (
        f'<rect width="{W}" height="{H}" fill="#F7F9FC"/>'
        f'<rect x="0" y="0" width="{W}" height="8" fill="url(#accent)"/>'
        + text(48, 52, title, 28, NAVY, 700)
        + text(48, 80, subtitle, 16, MUTED)
    )


def write_svg(name: str, body: str) -> Path:
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n{defs()}\n{body}\n</svg>'
    path = HERE / f"{name}.svg"
    path.write_text(svg, encoding="utf-8")
    script = f"""
const fs = require('fs');
const {{ Resvg }} = require('@resvg/resvg-js');
const svg = fs.readFileSync({str(path)!r});
const r = new Resvg(svg, {{ fitTo: {{ mode: 'width', value: {W * 2} }}, font: {{ loadSystemFonts: true, defaultFontFamily: 'Helvetica' }} }});
fs.writeFileSync({str(HERE / (name + '.png'))!r}, r.render().asPng());
"""
    subprocess.run(["node", "-e", script], check=True, cwd=str(RESVG_TOOLS))
    return path


def d01_landscape():
    b = [header("Paisaje: eventos, lakehouse y analítica", "Confluent Cloud Dedicated  ·  Azure  ·  Databricks")]
    b.append(lane(40, 110, 740, 740, "Confluent Cloud Dedicated", CONFLUENT, "#F2F7FF"))
    b.append(lane(820, 110, 740, 740, "Azure lakehouse / Databricks", "#FF3621", "#FFF6F4"))
    b.append(node(80, 180, 320, 88, "kafka.svg", "Tópicos crudos", "eventos de negocio", CONFLUENT))
    b.append(node(80, 300, 320, 88, "flink.svg", "Apache Flink SQL", "cura, lookup, ventanas", FLINK))
    b.append(node(80, 420, 320, 88, "kafka.svg", "Tópicos curados / DLQ", "contrato + excepciones", CONFLUENT))
    b.append(node(80, 540, 320, 88, "confluent-logo.svg", "Tableflow / Connect", "materializa tablas", CONFLUENT))
    b.append(node(80, 660, 320, 88, "postgresql.svg", "Lookup RDB / CDC", "dimensiones chicas", GOOD))
    b.append(arrow(400, 224, 400, 300, CONFLUENT))
    b.append(arrow(400, 388, 400, 420, FLINK))
    b.append(arrow(400, 508, 400, 540, CONFLUENT))
    b.append(node(880, 180, 340, 88, "datalake.svg", "ADLS Gen2", "Delta / Iceberg files", AMBER))
    b.append(node(880, 300, 340, 88, "delta.svg", "Delta Lake", "external table", "#00ADD4"))
    b.append(node(880, 420, 340, 88, "databricks.svg", "Unity Catalog", "gobernanza, SQL, ML", "#FF3621"))
    b.append(node(880, 540, 340, 88, "databricks.svg", "SQL Warehouse / Jobs", "historia, joins pesados", "#FF3621"))
    b.append(node(880, 660, 340, 88, "iceberg.svg", "Iceberg (opcional)", "Trino / otros motores", NAVY))
    b.append(arrow(400, 584, 880, 224, MUTED, "Tableflow → storage"))
    b.append(arrow(1220, 224, 1220, 300, AMBER))
    b.append(arrow(1220, 388, 1220, 420, "#FF3621"))
    b.append(arrow(1220, 508, 1220, 540, "#FF3621"))
    write_svg("01-paisaje", "\n".join(b))


def d02_tableflow():
    b = [header("Escenario A — Tableflow a Delta Lake", "Flink cura el tópico; Tableflow materializa; Databricks lee")]
    b.append(node(60, 200, 280, 96, "kafka.svg", "Tópico crudo", "Schema Registry", CONFLUENT))
    b.append(node(420, 200, 280, 96, "flink.svg", "Flink SQL", "filtra · enriquece", FLINK))
    b.append(node(780, 200, 280, 96, "kafka.svg", "Tópico curado", "append o upsert", CONFLUENT))
    b.append(node(1140, 200, 360, 96, "confluent-logo.svg", "Tableflow", "Delta en ADLS Gen2", CONFLUENT))
    b.append(arrow(340, 248, 420, 248, CONFLUENT))
    b.append(arrow(700, 248, 780, 248, FLINK))
    b.append(arrow(1060, 248, 1140, 248, CONFLUENT))
    b.append(node(1140, 380, 360, 96, "datalake.svg", "ADLS Gen2", "BYOS, Private Endpoint", AMBER))
    b.append(node(1140, 560, 360, 96, "databricks.svg", "Unity Catalog", "external Delta (read-only)", "#FF3621"))
    b.append(node(60, 560, 640, 96, "databricks.svg", "SQL / ML / BI", "join con tablas nativas del lakehouse", "#FF3621"))
    b.append(arrow(1320, 296, 1320, 380, AMBER))
    b.append(arrow(1320, 476, 1320, 560, "#FF3621"))
    b.append(arrow(1140, 608, 700, 608, MUTED, "Databricks lee"))
    b.append(text(60, 760, "Red privada: Tableflow escribe ADLS por Private Endpoint. Unity Catalog automático exige workspace público;", 15, MUTED))
    b.append(text(60, 784, "si Databricks es privado, se registra CREATE EXTERNAL TABLE LOCATION una vez.", 15, MUTED))
    write_svg("02-tableflow-delta", "\n".join(b))


def d03_spark_direct():
    b = [header("Escenario B — Databricks lee Kafka directo", "Structured Streaming o Lakeflow Connect → Delta managed")]
    b.append(node(80, 220, 320, 100, "kafka.svg", "Tópico Kafka", "Dedicated + Private Link", CONFLUENT))
    b.append(node(520, 140, 420, 100, "databricks.svg", "Structured Streaming", "transforma, join, watermark", "#FF3621"))
    b.append(node(520, 300, 420, 100, "databricks.svg", "Lakeflow Connect Kafka", "ingesta gobernada, serverless", "#FF3621"))
    b.append(node(1080, 220, 420, 100, "delta.svg", "Delta managed", "Unity Catalog, OPTIMIZE", "#00ADD4"))
    b.append(arrow(400, 270, 520, 190, MUTED, "opción 1"))
    b.append(arrow(400, 270, 520, 350, MUTED, "opción 2"))
    b.append(arrow(940, 190, 1080, 270, "#FF3621"))
    b.append(arrow(940, 350, 1080, 270, "#FF3621"))
    b.append(text(80, 500, "Cuándo: necesitas lógica Spark (UDF, join pesado con Delta) o todavía no hay Tableflow.", 16, MUTED))
    b.append(text(80, 532, "Costo: DBU + VM o serverless + egress Dedicated → Azure. Es el patrón de los jobs actuales.", 16, MUTED))
    b.append(text(80, 564, "Lakeflow Connect: ingesta continua a streaming tables; sin SCD2, sin filtro de filas (límites 2026).", 16, MUTED))
    write_svg("03-databricks-kafka-directo", "\n".join(b))


def d04_enrich():
    b = [header("Escenario C — Enriquecimiento del stream", "Lookup RDB, temporal join CDC, o join pesado en Databricks")]
    b.append(lane(40, 120, 1520, 200, "C1  Lookup — dimensión en reposo (RDB)", GOOD, "#F3FBF7"))
    b.append(node(70, 170, 280, 88, "kafka.svg", "Stream", "orders", CONFLUENT))
    b.append(node(430, 170, 360, 88, "flink.svg", "Flink lookup join", "KEY_SEARCH_AGG", FLINK))
    b.append(node(870, 170, 300, 88, "postgresql.svg", "Postgres / SQL Server", "por PK", GOOD))
    b.append(node(1240, 170, 280, 88, "kafka.svg", "Tópico curado", "evento + dimensión", CONFLUENT))
    b.append(arrow(350, 214, 430, 214, CONFLUENT))
    b.append(arrow(790, 214, 870, 214, FLINK))
    b.append(arrow(1170, 214, 1240, 214, CONFLUENT))

    b.append(lane(40, 350, 1520, 200, "C2  Temporal join — dimensión versionada (CDC → Kafka)", CONFLUENT, "#F2F7FF"))
    b.append(node(70, 400, 260, 88, "sqlserver.svg", "Core / RDB", "Debezium CDC", MUTED))
    b.append(node(400, 400, 280, 88, "kafka.svg", "Tópico compactado", "PK + changelog", CONFLUENT))
    b.append(node(760, 400, 360, 88, "flink.svg", "FOR SYSTEM_TIME AS OF", "valor vigente al rowtime", FLINK))
    b.append(node(1200, 400, 320, 88, "kafka.svg", "Tópico curado", "as-of correcto", CONFLUENT))
    b.append(arrow(330, 444, 400, 444, MUTED))
    b.append(arrow(680, 444, 760, 444, CONFLUENT))
    b.append(arrow(1120, 444, 1200, 444, FLINK))

    b.append(lane(40, 580, 1520, 200, "C3  Join pesado — fact / historia en Delta (no es Flink)", "#FF3621", "#FFF6F4"))
    b.append(node(70, 630, 300, 88, "kafka.svg", "Tópico curado", "ya limpio", CONFLUENT))
    b.append(node(450, 630, 300, 88, "delta.svg", "Delta / Tableflow", "external o managed", "#00ADD4"))
    b.append(node(830, 630, 360, 88, "databricks.svg", "Spark / SQL Warehouse", "scan + shuffle", "#FF3621"))
    b.append(node(1260, 630, 260, 88, "delta.svg", "Tabla resultado", "historia", "#00ADD4"))
    b.append(arrow(370, 674, 450, 674, CONFLUENT))
    b.append(arrow(750, 674, 830, 674, MUTED))
    b.append(arrow(1190, 674, 1260, 674, "#FF3621"))
    write_svg("04-enriquecimiento", "\n".join(b))


def d05_sharing():
    b = [header("Escenario D — Delta Sharing no alimenta Flink", "Sharing reparte el resultado analítico; el join de Flink usa Kafka o JDBC")]
    b.append(lane(40, 130, 740, 620, "No: Sharing como fuente de Flink", "#B54848", "#FDF6F6"))
    b.append(node(90, 200, 300, 90, "delta.svg", "Delta en UC", "dimensión", "#00ADD4"))
    b.append(node(90, 360, 300, 90, "databricks.svg", "Delta Sharing", "token / OpenSharing", "#FF3621"))
    b.append(node(90, 520, 300, 90, "flink.svg", "Flink Cloud", "no hay connector", FLINK))
    b.append(arrow(240, 290, 240, 360, "#B54848"))
    b.append(arrow(240, 450, 240, 520, "#B54848", "no soportado"))

    b.append(lane(820, 130, 740, 620, "Sí: Sharing después del lakehouse", GOOD, "#F3FBF7"))
    b.append(node(870, 200, 320, 90, "flink.svg", "Flink + Tableflow", "tópico → Delta", FLINK))
    b.append(node(870, 360, 320, 90, "databricks.svg", "Unity Catalog", "join pesado aquí", "#FF3621"))
    b.append(node(870, 520, 320, 90, "databricks.svg", "Delta Sharing", "otro workspace / vendor", "#FF3621"))
    b.append(arrow(1030, 290, 1030, 360, GOOD))
    b.append(arrow(1030, 450, 1030, 520, GOOD, "compartir resultado"))
    write_svg("05-delta-sharing", "\n".join(b))


def d06_shift_left():
    b = [header("Shift-left vs shift-right", "El dato se cura una vez en el tópico, antes de salir al lakehouse")]
    b.append(lane(40, 120, 740, 680, "Hoy — shift-right", MUTED, "#F1F2F4"))
    b.append(node(80, 190, 300, 84, "kafka.svg", "Tópico crudo", "N consumidores", MUTED))
    b.append(node(80, 320, 300, 84, "databricks.svg", "N jobs Spark", "cada uno limpia", "#FF3621"))
    b.append(node(80, 450, 300, 84, "delta.svg", "N tablas Delta", "contratos distintos", "#00ADD4"))
    b.append(node(80, 580, 300, 84, "adf.svg", "Data Factory", "orquesta lotes", MUTED))
    b.append(arrow(230, 274, 230, 320, MUTED, "egress N veces"))
    b.append(arrow(230, 404, 230, 450, MUTED))
    b.append(arrow(230, 534, 230, 580, MUTED))

    b.append(lane(820, 120, 740, 680, "Objetivo — shift-left", CONFLUENT, "#F2F7FF"))
    b.append(node(860, 190, 300, 84, "kafka.svg", "Tópico crudo", "un contrato", CONFLUENT))
    b.append(node(860, 320, 300, 84, "flink.svg", "Flink una vez", "cura + DLQ", FLINK))
    b.append(node(860, 450, 300, 84, "kafka.svg", "Tópico curado", "operacional", CONFLUENT))
    b.append(node(860, 580, 300, 84, "delta.svg", "Un sink Delta", "Tableflow / job delgado", "#00ADD4"))
    b.append(arrow(1010, 274, 1010, 320, CONFLUENT))
    b.append(arrow(1010, 404, 1010, 450, FLINK))
    b.append(arrow(1010, 534, 1010, 580, CONFLUENT, "sin hop extra"))
    write_svg("06-shift-left", "\n".join(b))


if __name__ == "__main__":
    d01_landscape()
    d02_tableflow()
    d03_spark_direct()
    d04_enrich()
    d05_sharing()
    d06_shift_left()
    print("ok", HERE)
