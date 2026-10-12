#!/usr/bin/env python3
"""Generate the Temporal Cloud on Azure Private Link (per namespace) drawio diagram."""

from __future__ import annotations

import base64
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ICON_CACHE = HERE / ".icons"
ICON_CACHE.mkdir(exist_ok=True)
OUT = HERE / "temporal-cloud-azure-private-link.drawio"

AZURE = "https://raw.githubusercontent.com/jgraph/drawio/dev/src/main/webapp/img/lib/azure2/{}.svg"
SIMPLE = "https://cdn.simpleicons.org/{}/{}"

ICONS = {
    "vnet": AZURE.format("networking/Virtual_Networks"),
    "subnet": AZURE.format("networking/Subnet"),
    "pe": AZURE.format("networking/Private_Endpoint"),
    "pls": AZURE.format("networking/Private_Link_Service"),
    "privatelink": AZURE.format("networking/Private_Link"),
    "dns": AZURE.format("networking/DNS_Zones"),
    "nsg": AZURE.format("networking/Network_Security_Groups"),
    "expressroute": AZURE.format("networking/ExpressRoute_Circuits"),
    "vpngw": AZURE.format("networking/Virtual_Network_Gateways"),
    "aks": AZURE.format("containers/Kubernetes_Services"),
    "vm": AZURE.format("compute/Virtual_Machine"),
    "subscription": AZURE.format("general/Subscriptions"),
    "keyvault": AZURE.format("security/Key_Vaults"),
    "temporal": SIMPLE.format("temporal", "000000"),
    "terraform": SIMPLE.format("terraform", "844FBA"),
    "java": SIMPLE.format("openjdk", "437291"),
}

GREEN, GREEN_FILL = "#1F4E3D", "#EEF2EF"
STEEL, STEEL_FILL = "#3D5A73", "#F0F4F8"
AMBER, AMBER_FILL = "#8A5A12", "#F7F3EC"
ROSE, ROSE_FILL = "#783C3C", "#F8F2F2"
GREY = "#666666"
AZ_BLUE = "#0078D4"


def icon_data(key: str) -> str:
    dest = ICON_CACHE / f"{key}.svg"
    if not dest.exists():
        req = urllib.request.Request(ICONS[key], headers={"User-Agent": "ludhara-tech-docs/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            dest.write_bytes(r.read())
    # draw.io styles use ";" as separator, so the data URI omits ";base64".
    return "data:image/svg+xml," + base64.b64encode(dest.read_bytes()).decode("ascii")


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def html(title: str, *lines: str) -> str:
    parts = [f"<b>{title}</b>"] if title else []
    parts += list(lines)
    return "<br>".join(parts)


class Diagram:
    def __init__(self, name: str, width: int, height: int):
        self.name, self.width, self.height = name, width, height
        self.cells: list[str] = []
        self.icons: list[str] = []
        self.edges: list[str] = []
        self.n = 2

    def _id(self) -> str:
        self.n += 1
        return f"c{self.n}"

    def _vertex(self, value: str, style: str, x, y, w, h, parent="1") -> str:
        i = self._id()
        self.cells.append(
            f'<mxCell id="{i}" value="{esc(value)}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        return i

    def group(self, title: str, x, y, w, h, stroke, fill, parent="1", dashed=False) -> str:
        style = (
            f"rounded=1;arcSize=2;whiteSpace=wrap;html=1;container=1;collapsible=0;recursiveResize=0;"
            f"fillColor={fill};strokeColor={stroke};strokeWidth=1.5;{'dashed=1;' if dashed else ''}"
            f"verticalAlign=top;align=left;spacingLeft=40;spacingTop=8;fontStyle=1;fontSize=13;"
            f"fontColor={stroke};fontFamily=Helvetica;"
        )
        return self._vertex(title, style, x, y, w, h, parent)

    def box(self, value: str, x, y, w, h, parent="1", stroke=GREY, fill="#FFFFFF", size=11, align="left", pad=46) -> str:
        style = (
            f"rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
            f"fontSize={size};fontColor=#1A1A1A;fontFamily=Helvetica;align={align};verticalAlign=middle;"
            f"spacingLeft={pad if align == 'left' else 6};spacingRight=6;"
        )
        return self._vertex(value, style, x, y, w, h, parent)

    def text(self, value: str, x, y, w, h, parent="1", size=11, color="#1A1A1A", valign="top") -> str:
        style = (
            f"text;html=1;whiteSpace=wrap;align=left;verticalAlign={valign};fontSize={size};"
            f"fontColor={color};fontFamily=Helvetica;"
        )
        return self._vertex(value, style, x, y, w, h, parent)

    def icon(self, key: str, x, y, size=32, parent="1") -> str:
        # Icons are emitted after all boxes so they stay on top of them.
        style = f"shape=image;html=1;imageAspect=0;aspect=fixed;image={icon_data(key)};"
        i = self._vertex("", style, x, y, size, size, parent)
        self.icons.append(self.cells.pop())
        return i

    def badge(self, num: str, x, y, parent="1", color=AZ_BLUE) -> str:
        style = (
            f"ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor={color};strokeColor=none;"
            f"fontColor=#FFFFFF;fontStyle=1;fontSize=12;fontFamily=Helvetica;"
        )
        return self._vertex(num, style, x, y, 24, 24, parent)

    def edge(self, src: str, tgt: str, label="", color=GREY, dashed=False, end="block", width=2,
             exit_=None, entry=None, points=()) -> str:
        i = self._id()
        style = (
            f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow={end};endFill=1;"
            f"strokeColor={color};strokeWidth={width};{'dashed=1;' if dashed else ''}"
            f"fontSize=10;fontColor={color};fontFamily=Helvetica;labelBackgroundColor=#FFFFFF;"
        )
        for prefix, pt in (("exit", exit_), ("entry", entry)):
            if pt:
                style += f"{prefix}X={pt[0]};{prefix}Y={pt[1]};{prefix}Dx=0;{prefix}Dy=0;"
        pts = ""
        if points:
            pts = "<Array as=\"points\">" + "".join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in points) + "</Array>"
        self.edges.append(
            f'<mxCell id="{i}" value="{esc(label)}" style="{style}" edge="1" parent="1" source="{src}" target="{tgt}">'
            f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>'
        )
        return i

    def write(self, path: Path) -> None:
        body = "\n".join(self.cells + self.edges + self.icons)
        xml = (
            '<mxfile host="app.diagrams.net" agent="Cursor" version="24.7.0">\n'
            f'  <diagram id="{path.stem}" name="{esc(self.name)}">\n'
            f'    <mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
            f'arrows="1" fold="1" page="1" pageScale="1" pageWidth="{self.width}" pageHeight="{self.height}" '
            'math="0" shadow="0">\n'
            '      <root>\n        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n'
            f"{body}\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n"
        )
        path.write_text(xml, encoding="utf-8")
        ET.parse(path)


def build() -> None:
    d = Diagram("Private Link por namespace", 1970, 1330)

    d.text(html("", "<font style=\"font-size:20px\"><b>Temporal Cloud on Azure — Private Link por namespace</b></font>"),
           30, 14, 1200, 30)
    d.text("Pre-release (invite-only): solo desarrollo y evaluación, sin SLA ni producción. "
           "Public Preview objetivo: noviembre 2026 · GA objetivo: Q1 2027. Regiones: centralus, australiaeast.",
           30, 46, 1500, 20, color="#8A5A12")

    # --- Azure: suscripción del Banco -------------------------------------------------------
    az = d.group("Azure — suscripción BCP (región recomendada: la misma del namespace)", 30, 80, 930, 650, AZ_BLUE, "#F5F9FD")
    d.icon("subscription", 8, 6, 26, az)

    spoke = d.group("VNet de aplicaciones (spoke)", 20, 46, 420, 330, GREEN, GREEN_FILL, az)
    d.icon("vnet", 8, 6, 26, spoke)
    d.icon("aks", 20, 52, 32, spoke)
    workers = d.box(html("Workers AKS — APOQ / NREM", "Temporal SDK (Java) · mTLS o API key",
                         "Endpoint: &lt;ns&gt;.&lt;account&gt;.tmprl.cloud:7233"), 12, 44, 396, 70, spoke, GREEN)
    d.icon("java", 26, 140, 26, spoke)
    clients = d.box(html("Clients / starters", "Inician workflows, signals y queries"), 12, 128, 396, 52, spoke, GREEN)
    d.icon("vm", 22, 210, 30, spoke)
    probe = d.box(html("VM / pod de prueba", "nslookup + temporal workflow list"), 12, 198, 396, 52, spoke, GREEN)
    d.text("Workers y Clients deben enrutar hacia la IP del Private Endpoint. Pueden estar en la misma VNet del "
           "PE o en otra VNet conectada por Peering, VPN o ExpressRoute.", 12, 262, 396, 56, spoke, size=10, color="#555555")

    hub = d.group("VNet del Private Endpoint (hub)", 490, 46, 420, 330, STEEL, STEEL_FILL, az)
    d.icon("vnet", 8, 6, 26, hub)
    snet = d.group("snet-privatelink", 12, 40, 396, 200, STEEL, "#FFFFFF", hub, dashed=True)
    d.icon("subnet", 8, 6, 24, snet)
    d.icon("pe", 18, 50, 34, snet)
    pe = d.box(html("Private Endpoint · pe-temporal-centralus",
                    "IP privada: 10.1.2.3 (puerto 7233)",
                    "Resource: alias del Private Link Service",
                    "pl-…centralus.azure.privatelinkservice",
                    "Estado: Pending → Approved"), 10, 36, 376, 100, snet, STEEL)
    d.icon("nsg", 20, 156, 28, snet)
    d.box(html("Network Security Group", "Permitir TCP 7233 desde las VNets de workers"), 10, 148, 376, 44, snet, STEEL)
    conn = d.box(html("Peering · VPN · ExpressRoute", "Conecta spoke ↔ hub (u on-premises)"), 12, 250, 396, 48, hub, STEEL,
                 size=11, pad=80)
    d.icon("expressroute", 18, 260, 28, hub)
    d.icon("vpngw", 50, 260, 28, hub)

    dns = d.group("Private DNS zone", 20, 400, 890, 230, AMBER, AMBER_FILL, az)
    d.icon("dns", 8, 6, 26, dns)
    zone = d.box(html("&lt;account-id&gt;.tmprl.cloud",
                      "A  apoq.&lt;account-id&gt;  → 10.1.2.3",
                      "A  nrem.&lt;account-id&gt;  → 10.1.2.3",
                      "Un registro A por namespace, todos hacia la IP del PE"), 12, 40, 430, 100, dns, AMBER)
    d.icon("dns", 22, 74, 30, dns)
    links = d.box(html("VNet links (registration-enabled = false)",
                       "Vincular la zona a toda VNet con Workers o Clients",
                       "Sin zona privada, el hostname resuelve por DNS público",
                       "y el tráfico sale por internet"), 460, 40, 418, 100, dns, AMBER)
    d.text(html("Alternativa sin DNS privado",
                "address = 10.1.2.3:7233 y tls_server_name (o server_name) = &lt;ns&gt;.&lt;account-id&gt;.tmprl.cloud. "
                "Se recomienda DNS privado: mantiene los hostnames estándar, evita el override de SNI y permite "
                "recrear el PE cambiando solo DNS."), 12, 150, 866, 70, dns, size=10, color="#555555")

    # --- Temporal Cloud ----------------------------------------------------------------------
    tc = d.group("Temporal Cloud — región azure-centralus (cuenta &lt;account-id&gt;)", 1010, 80, 680, 650, "#1A1A1A", "#FAFAFA")
    d.icon("temporal", 10, 7, 24, tc)

    pls = d.box(html("Private Link Service", "de Temporal Cloud",
                     "Aprueba el PE cuando existe una",
                     "Connectivity Rule con su resource ID"), 12, 140, 290, 100, tc, "#1A1A1A")
    d.icon("pls", 20, 172, 34, tc)

    cr = d.group("Connectivity Rules (nivel cuenta)", 316, 40, 352, 224, STEEL, STEEL_FILL, tc)
    d.icon("privatelink", 8, 5, 26, cr)
    cr_pub = d.box(html("CR-PUB · pública", "Permite internet. Solo durante la transición",
                        "(Workers que aún no usan Private Link)"), 10, 38, 332, 70, cr, ROSE, ROSE_FILL, size=10)
    d.icon("temporal", 18, 58, 26, cr)
    cr_az = d.box(html("CR-AZ · privada",
                       "privateRule.azurePeResourceId =",
                       "/subscriptions/…/privateEndpoints/pe-temporal-centralus",
                       "privateRule.region = azure-centralus"), 10, 124, 332, 88, cr, STEEL, size=10)
    d.icon("pe", 18, 150, 28, cr)

    ns = d.group("Namespaces — las reglas se adjuntan a cada namespace", 12, 282, 656, 354, "#1A1A1A", "#FFFFFF", tc)
    ns_apoq = d.box(html("apoq.&lt;account-id&gt;  ·  reglas: [CR-AZ]",
                         "Solo acepta tráfico de ese Private Link.",
                         "Internet u otro Private Link: rechazado aun con credenciales válidas"),
                    10, 40, 636, 76, ns, GREEN, GREEN_FILL)
    d.icon("temporal", 18, 64, 28, ns)
    ns_nrem = d.box(html("nrem.&lt;account-id&gt;  ·  reglas: [CR-AZ] + [CR-PUB]",
                         "Acepta tráfico autenticado desde Private Link e internet.",
                         "Migración: detach de CR-PUB cuando todos los Workers usen Private Link"),
                    10, 132, 636, 76, ns, AMBER, AMBER_FILL)
    d.icon("temporal", 18, 156, 28, ns)
    ns_dev = d.box(html("dev.&lt;account-id&gt;  ·  sin reglas (default)",
                        "No bloquea tráfico entrante: sirve toda solicitud autenticada"),
                   10, 224, 636, 60, ns, GREY, "#F4F4F4")
    d.icon("temporal", 18, 240, 28, ns)
    d.text("Muchos a muchos: un PE accede a cualquier namespace de la región; un namespace acepta varios PE. "
           "HA multi-región aún no disponible en Azure.", 10, 296, 636, 40, ns, size=10, color="#555555")

    # --- Internet ----------------------------------------------------------------------------
    inet = d.box(html("Internet público", "Worker o client fuera", "de la red privada"), 1760, 440, 190, 76,
                 stroke=ROSE, fill=ROSE_FILL, align="center")

    # --- Administración ---------------------------------------------------------------------
    adm = d.group("Administración (Platform / PEVE)", 30, 760, 1660, 110, "#555555", "#FFFFFF")
    d.box(html("Azure portal / Azure CLI", "az network private-endpoint · private-dns  —  pasos 1, 2, 4, 5"),
          12, 40, 400, 56, adm)
    d.icon("pe", 22, 52, 30, adm)
    d.box(html("temporal cloud CLI", "connectivity private create · namespace connectivity attach  —  pasos 3, 6, 7"),
          424, 40, 470, 56, adm)
    d.icon("temporal", 436, 54, 26, adm)
    d.box(html("Cloud Ops API — saas-api.tmprl.cloud", "HTTP / gRPC · Bearer API key  —  pasos 3, 6"),
          906, 40, 380, 56, adm)
    d.icon("temporal", 918, 54, 26, adm)
    d.box(html("Terraform provider", "Temporal Cloud (julio 2026)  —  pasos 3, 6"), 1298, 40, 350, 56, adm)
    d.icon("terraform", 1310, 54, 26, adm)

    # --- Flujos ------------------------------------------------------------------------------
    d.edge(spoke, zone, label="DNS: &lt;ns&gt;.&lt;account-id&gt;.tmprl.cloud → 10.1.2.3", color=AMBER, dashed=True,
           exit_=(0.55, 1), entry=(0.53, 0))
    d.edge(workers, pe, label="gRPC TLS :7233", color=GREEN, exit_=(1, 0.5), entry=(0, 0.25))
    d.edge(links, hub, label="VNet link", color=AMBER, dashed=True, end="none", width=1, exit_=(0.5, 0), entry=(0.5, 1))
    d.edge(links, spoke, label="VNet link", color=AMBER, dashed=True, end="none", width=1, exit_=(0.1, 0), entry=(0.9, 1))
    d.edge(pe, pls, label="Azure Private Link", color=STEEL, width=3, exit_=(1, 0.5), entry=(0, 0.5))
    d.edge(cr_az, pls, label="aprueba", color=STEEL, dashed=True, exit_=(0, 0.5), entry=(1, 0.5))
    d.edge(pls, ns, label="tráfico privado", color="#1A1A1A", exit_=(0.5, 1), entry=(0.22, 0))
    d.edge(cr, ns, label="attach por namespace", color=STEEL, dashed=True, exit_=(0.5, 1), entry=(0.75, 0))
    d.edge(inet, ns_apoq, label="✕ Request unauthorized", color=ROSE, dashed=True, exit_=(0, 0.25), entry=(1, 0.5))
    d.edge(inet, ns_nrem, label="✓ permitido por CR-PUB", color=AMBER, dashed=True, exit_=(0, 0.75), entry=(1, 0.5))

    # --- Pasos y reglas ----------------------------------------------------------------------
    steps = d.group("Pasos de configuración", 30, 890, 1020, 420, AZ_BLUE, "#FFFFFF")
    items = [
        ("1", "Crear el Private Endpoint en la VNet, con “resource alias” = Private Link Service alias de la región del "
              "namespace (centralus o australiaeast). El PE puede estar en otra región, pero se recomienda la misma."),
        ("2", "Verificar Provisioning State = Succeeded, Connection status = Pending, Awaiting Approval. Copiar el "
              "resource ID del PE (az network private-endpoint show --query id)."),
        ("3", "Crear la Connectivity Rule privada dentro de las 24 h (si no, el PE se rechaza y hay que recrearlo): "
              "temporal cloud connectivity private create --azure-pe-resource-id … --region azure-centralus. "
              "Temporal aprueba el PE. Guardar el connectivityRuleId."),
        ("4", "Obtener la IP privada del PE (customDnsConfigs[0].ipAddresses[0])."),
        ("5", "Crear la Private DNS zone &lt;account-id&gt;.tmprl.cloud, un registro A por namespace hacia la IP del PE y "
              "vincularla a las VNets de Workers (registration-enabled false). Verificar con nslookup."),
        ("6", "Adjuntar la regla a cada namespace: temporal cloud namespace connectivity attach --namespace … "
              "--connectivity-rule-id …. Si hay Workers por internet, adjuntar también la regla pública, migrar y luego detach."),
        ("7", "Probar: desde la VNet, temporal workflow list --address &lt;ns&gt;.&lt;account-id&gt;.tmprl.cloud:7233 "
              "responde; desde fuera falla con “Request unauthorized”."),
    ]
    y = 38
    for num, txt in items:
        d.badge(num, 14, y, steps)
        d.text(txt, 48, y - 2, 956, 52, steps, size=11)
        y += 54

    rules = d.group("Comportamiento de las reglas y advertencias", 1070, 890, 620, 420, ROSE, "#FFFFFF")
    d.text(html("Reglas por namespace",
                "• Sin reglas: no bloquea tráfico; sirve toda solicitud autenticada.",
                "• Solo reglas privadas: únicamente desde esos Private Link.",
                "• Privadas + pública: Private Link e internet.",
                "",
                "<b>Advertencias</b>",
                "• Adjuntar solo la regla privada corta el tráfico vivo por internet.",
                "• La API UpdateNamespace es declarativa: enviar el spec completo con resourceVersion; "
                "un campo omitido se borra.",
                "• En la API el namespace va sin “.tmprl.cloud” (ej.: payments.abcde).",
                "• La API key solo se usa al crear la regla; deshabilitarla no afecta la regla.",
                "• tcld no está soportado en Azure: usar temporal cloud CLI, Cloud Ops API o Terraform.",
                "• La guía muestra dos alias distintos para centralus: confirmar con Temporal antes de crear el PE.",
                "",
                "<b>Troubleshooting: el PE sigue en Pending</b>",
                "• No existe una Connectivity Rule con ese resource ID (listar reglas: temporal cloud connectivity list).",
                "• La regla se creó con otro resource ID: falla con “private endpoint connection not found”.",
                "• El PE apunta a un alias de otra región que la del namespace: mismo error.",
                "• Pasaron más de 24 h sin regla: el PE se rechaza y hay que recrearlo."),
           14, 36, 592, 376, rules, size=11)

    d.write(OUT)


if __name__ == "__main__":
    build()
    print("ok", OUT)
