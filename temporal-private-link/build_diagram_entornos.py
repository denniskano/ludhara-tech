#!/usr/bin/env python3
"""Draw.io: Private Link de BCP por entorno, con HA multi-región en producción.

Workers y Private Endpoints viven en eastus2. El Private Link Service de Temporal
está en azure-centralus; la réplica de producción, en azure-australiaeast.
"""

from __future__ import annotations

from build_diagram import (
    AMBER,
    AMBER_FILL,
    AZ_BLUE,
    GREEN,
    GREEN_FILL,
    GREY,
    ROSE,
    ROSE_FILL,
    STEEL,
    STEEL_FILL,
    Diagram,
    html,
)

OUT_NAME = "temporal-cloud-azure-private-link-entornos.drawio"
PURPLE, PURPLE_FILL = "#5C4B8A", "#F3F0F8"

PAGE_W = 2420
WRAP_X, WRAP_Y, WRAP_W = 12, 108, 2396
CARD_Y, CARD_W, CARD_H, CARD_GAP = 72, 770, 830, 20
DNS_H = 330
BOT_H = 560
DNS_Y = WRAP_Y + CARD_Y + CARD_H + 14 + 18
BOT_Y = DNS_Y + DNS_H + 18
PAGE_H = BOT_Y + BOT_H + 20


def aks_box(d: Diagram, parent, x, y, w, h, title, lines, stroke) -> str:
    box = d.box(html(title, *lines), x, y, w, h, parent, stroke, pad=46)
    d.icon("aks", x + 10, y + 18, 28, parent)
    return box


def build() -> Diagram:
    d = Diagram("Private Link por entorno", PAGE_W, PAGE_H)

    d.text(
        html("", "<font style=\"font-size:20px\"><b>Temporal Cloud on Azure — Private Link por entorno (BCP)</b></font>"),
        16, 12, 1600, 30,
    )
    d.text(
        "Una cuenta Temporal. Un Private Endpoint por entorno. Cada aplicación tiene su propio AKS en eastus2 "
        "y tres namespaces (desarrollo, certificación, producción). Destino: azure-centralus.",
        16, 44, 1680, 28, size=12,
    )
    d.text(
        "Producción activa multi-región: segundo Private Endpoint hacia azure-australiaeast. "
        "HA multi-región todavía no está disponible en Azure; este escenario es la configuración objetivo de la guía.",
        16, 74, 2300, 24, size=11, color=AMBER,
    )

    bank = d.group("BCP · Azure eastus2", WRAP_X, WRAP_Y, WRAP_W, CARD_Y + CARD_H + 12, AZ_BLUE, "#F5F9FD")
    d.icon("subscription", 8, 6, 26, bank)
    d.text(
        "Los AKS y los Private Endpoints están en eastus2. El alias del Private Link Service es el de la región "
        "de Temporal, no el de la VNet. eastus2 → centralus queda en el backbone de Azure.",
        16, 36, 1800, 28, bank, size=11, color="#35556E",
    )

    x0 = 16
    dev = _environment(
        d, bank, x0, CARD_Y, GREEN, GREEN_FILL,
        "1  ·  Desarrollo",
        "dev", "10.8.0.4", "CR-DEV",
        "No se adjunta a namespaces de cert ni de prod.",
    )
    cert = _environment(
        d, bank, x0 + CARD_W + CARD_GAP, CARD_Y, AMBER, AMBER_FILL,
        "2  ·  Certificación",
        "cert", "10.16.0.4", "CR-CERT",
        "No se adjunta a namespaces de dev ni de prod.",
    )
    prod = _production(d, bank, x0 + 2 * (CARD_W + CARD_GAP), CARD_Y)

    for aks_a, aks_b, subnet in (dev, cert, prod):
        d.edge(aks_a, subnet, label="gRPC TLS :7233", color=GREEN, width=2, exit_=(0.5, 1), entry=(0.28, 0))
        d.edge(aks_b, subnet, color=GREEN, width=2, exit_=(0.5, 1), entry=(0.72, 0))

    _dns(d)
    _account(d)
    _prod_steps(d)
    return d


def _environment(d, parent, x, y, stroke, fill, title, env, ip, rule, foot) -> tuple[str, str, str]:
    card = d.group(title, x, y, CARD_W, CARD_H, stroke, fill, parent)
    d.icon("vnet", 8, 6, 26, card)
    d.text(
        "VNet del entorno en eastus2. Sin ruta hacia la subnet del Private Endpoint de otro entorno.",
        14, 40, 742, 28, card, size=10, color="#555555",
    )
    aks_a = aks_box(
        d, card, 14, 74, 364, 124, f"AKS APOQ · espacio propio",
        (f"eastus2 · entorno {env}", f"apoq-{env}.&lt;account-id&gt;.tmprl.cloud:7233", "mTLS o API key de este namespace"),
        stroke,
    )
    aks_b = aks_box(
        d, card, 392, 74, 364, 124, f"AKS NREM · espacio propio",
        (f"eastus2 · entorno {env}", f"nrem-{env}.&lt;account-id&gt;.tmprl.cloud:7233", "mTLS o API key de este namespace"),
        stroke,
    )
    subnet = d.group("snet-privatelink", 14, 214, 742, 300, stroke, "#FFFFFF", card, dashed=True)
    d.icon("subnet", 8, 6, 24, subnet)
    pe = d.box(
        html(
            f"pe-temporal-{env}",
            f"IP de ejemplo {ip} · TCP 7233",
            "Alias: pl-…centralus.azure.privatelinkservice",
            "Región de la regla: azure-centralus",
            "El endpoint se crea en eastus2",
        ),
        14, 44, 714, 150, subnet, stroke, pad=46,
    )
    d.icon("pe", 26, 78, 30, subnet)
    nsg = d.box(
        html("NSG", f"Permitir TCP 7233 solo desde los AKS de {env}"),
        14, 208, 714, 48, subnet, stroke, pad=46,
    )
    d.icon("nsg", 26, 218, 26, subnet)
    d.text("Pending hasta la Connectivity Rule (máximo 24 h); después Approved.", 14, 264, 714, 24, subnet, size=10, color="#555555")

    d.box(
        html(
            f"{rule} · privada",
            f"azurePeResourceId = …/privateEndpoints/pe-temporal-{env}",
            "region = azure-centralus",
            f"Attach solo a apoq-{env} y nrem-{env}",
        ),
        14, 528, 742, 120, card, stroke, "#FFFFFF", size=11, pad=46,
    )
    d.icon("privatelink", 26, 556, 28, card)
    d.box(
        html(
            "Destino · PLS azure-centralus",
            "AKS eastus2 → PE eastus2 → backbone Azure → centralus. No sale a internet.",
            "Dev, cert y el PE primario de prod usan el mismo PLS; los separa el resource ID.",
            foot,
        ),
        14, 662, 742, 152, card, "#1A1A1A", pad=46,
    )
    d.icon("pls", 26, 700, 30, card)
    return aks_a, aks_b, subnet


def _production(d, parent, x, y) -> tuple[str, str, str]:
    card = d.group("3  ·  Producción · multi-región", x, y, CARD_W, CARD_H, STEEL, STEEL_FILL, parent)
    d.icon("vnet", 8, 6, 26, card)
    d.text(
        "Dos Private Endpoints en la VNet prod de eastus2. Los AKS no se mueven en un failover.",
        14, 40, 742, 28, card, size=10, color="#555555",
    )
    aks_a = aks_box(
        d, card, 14, 74, 364, 124, "AKS APOQ · espacio propio",
        ("eastus2 · producción", "apoq-prod.&lt;account-id&gt;.tmprl.cloud:7233", "El target no cambia en el failover"),
        STEEL,
    )
    aks_b = aks_box(
        d, card, 392, 74, 364, 124, "AKS NREM · espacio propio",
        ("eastus2 · producción", "nrem-prod.&lt;account-id&gt;.tmprl.cloud:7233", "El target no cambia en el failover"),
        STEEL,
    )
    subnet = d.group("snet-privatelink", 14, 214, 742, 300, STEEL, "#FFFFFF", card, dashed=True)
    d.icon("subnet", 8, 6, 24, subnet)
    d.box(
        html(
            "pe-temporal-prod-centralus",
            "IP de ejemplo 10.24.0.4 · TCP 7233",
            "Alias PLS azure-centralus",
            "Regla CR-PROD-CUS",
            "region = azure-centralus",
        ),
        14, 42, 350, 168, subnet, STEEL, pad=44,
    )
    d.icon("pe", 24, 70, 28, subnet)
    d.box(
        html(
            "pe-temporal-prod-aue",
            "IP de ejemplo 10.24.0.5 · TCP 7233",
            "Alias PLS azure-australiaeast",
            "Regla CR-PROD-AUE",
            "region = azure-australiaeast",
        ),
        378, 42, 350, 168, subnet, PURPLE, PURPLE_FILL, pad=44,
    )
    d.icon("pe", 388, 70, 28, subnet)
    d.box(
        html("NSG", "TCP 7233 solo desde los AKS de producción, hacia las dos IP"),
        14, 222, 714, 48, subnet, STEEL, pad=46,
    )
    d.icon("nsg", 26, 232, 26, subnet)

    d.box(
        html(
            "CR-PROD-CUS + CR-PROD-AUE",
            "Cada regla lleva el resource ID de un PE.",
            "Attach de las dos a apoq-prod y a nrem-prod.",
            "No adjuntarlas a dev ni a cert. Cupo: 2 de 5 privadas.",
        ),
        14, 528, 742, 120, card, STEEL, pad=46,
    )
    d.icon("privatelink", 26, 556, 28, card)
    d.box(
        html(
            "Destino · dos Private Link Services",
            "Región activa: PE 10.24.0.4 → PLS azure-centralus.",
            "Failover: PE 10.24.0.5 → PLS azure-australiaeast.",
            "Ambos PE siguen en eastus2. Cambia el hostname regional, no el clúster.",
        ),
        14, 662, 742, 152, card, "#1A1A1A", pad=46,
    )
    d.icon("pls", 26, 700, 30, card)
    return aks_a, aks_b, subnet


def _dns(d: Diagram) -> None:
    zone = d.group("Private DNS · una sola cuenta", 12, DNS_Y, WRAP_W, DNS_H, AMBER, AMBER_FILL)
    d.icon("dns", 8, 6, 26, zone)
    d.text(
        "Cloud Account ID = sufijo de todos los namespaces. Dev y cert usan la zona de la cuenta. "
        "Producción no se vincula a esa zona: una zona privada es autoritativa y un nombre sin registro responde NXDOMAIN.",
        48, 36, 2200, 32, zone, size=11, color="#5C4310",
    )
    d.box(
        html(
            "&lt;account-id&gt;.tmprl.cloud",
            "VNet link: solo desarrollo y certificación. registration-enabled = false.",
            "A  apoq-dev   →  10.8.0.4",
            "A  nrem-dev   →  10.8.0.4",
            "A  apoq-cert  →  10.16.0.4",
            "A  nrem-cert  →  10.16.0.4",
            "Sin registros de los namespaces prod.",
        ),
        16, 78, 760, 230, zone, AMBER, pad=46,
    )
    d.icon("dns", 28, 100, 28, zone)
    d.box(
        html(
            "azure-centralus.region.tmprl.cloud",
            "VNet link: solo producción.",
            "A del apex → 10.24.0.4 (PE de centralus).",
            "La guía pide sobreescribir este nombre,",
            "no &lt;account-id&gt;.tmprl.cloud.",
            "Cubre la región activa.",
        ),
        796, 78, 760, 230, zone, STEEL, pad=46,
    )
    d.icon("dns", 808, 100, 28, zone)
    d.box(
        html(
            "azure-australiaeast.region.tmprl.cloud",
            "VNet link: solo producción.",
            "A del apex → 10.24.0.5 (PE réplica).",
            "En failover el cliente pasa a este nombre",
            "y llega al segundo PE, todavía en eastus2.",
            "Los workers no cambian de target ni de clúster.",
        ),
        1576, 78, 790, 230, zone, PURPLE, PURPLE_FILL, pad=46,
    )
    d.icon("dns", 1588, 100, 28, zone)


def _account(d: Diagram) -> None:
    panel = d.group("Cuenta Temporal · namespaces y reglas adjuntas", 12, BOT_Y, 1188, BOT_H, "#1A1A1A", "#FAFAFA")
    d.icon("temporal", 8, 6, 24, panel)
    d.text(
        "Namespaces distintos, no cuentas distintas. Crear la regla solo aprueba el endpoint; hay que adjuntarla. "
        "Sin reglas, el namespace acepta tráfico autenticado por cualquier camino, internet incluido.",
        14, 40, 1160, 40, panel, size=11, color="#333333",
    )
    rows = [
        (GREEN, GREEN_FILL, "apoq-dev.&lt;account-id&gt;", "CR-DEV", "Solo el PE de desarrollo"),
        (GREEN, GREEN_FILL, "nrem-dev.&lt;account-id&gt;", "CR-DEV", "Comparte el PE con APOQ. Aislado por credencial y permisos"),
        (AMBER, AMBER_FILL, "apoq-cert.&lt;account-id&gt;", "CR-CERT", "Solo el PE de certificación"),
        (AMBER, AMBER_FILL, "nrem-cert.&lt;account-id&gt;", "CR-CERT", "Comparte el PE con APOQ en cert"),
        (STEEL, STEEL_FILL, "apoq-prod.&lt;account-id&gt;", "CR-PROD-CUS + CR-PROD-AUE", "Primaria centralus, réplica australiaeast"),
        (STEEL, STEEL_FILL, "nrem-prod.&lt;account-id&gt;", "CR-PROD-CUS + CR-PROD-AUE", "Las dos reglas. Ninguna regla de dev o cert"),
    ]
    y = 90
    for stroke, fill, name, rules, note in rows:
        d.box(html(f"{name}  ·  {rules}", note), 14, y, 1160, 58, panel, stroke, fill, size=11, pad=46)
        d.icon("temporal", 26, y + 14, 26, panel)
        y += 66
    d.text(
        "Un cliente de desarrollo con API key de producción, entrando por pe-temporal-dev, recibe Request unauthorized "
        "en apoq-prod y nrem-prod. Hasta 5 reglas privadas por namespace y 1 pública, sin costo. "
        "La pública solo durante el corte, y después se retira. Otra aplicación repite AKS y 3 namespaces, y comparte el PE del entorno.",
        14, 492, 1160, 56, panel, size=11, color="#333333",
    )


def _prod_steps(d: Diagram) -> None:
    panel = d.group("Configuración Private Link de producción (multi-región)", 1216, BOT_Y, 1192, BOT_H, STEEL, "#FFFFFF")
    d.icon("pe", 8, 6, 24, panel)
    steps = [
        "En la VNet de producción (eastus2), crear snet-privatelink. El NSG permite TCP 7233 solo desde los AKS prod.",
        "Crear pe-temporal-prod-centralus con el alias de azure-centralus. Copiar su resource ID y su IP privada.",
        "Crear la regla CR-PROD-CUS dentro de las 24 h: temporal cloud connectivity private create --azure-pe-resource-id <id del PE> --region azure-centralus.",
        "Crear pe-temporal-prod-aue en la misma subnet, con el alias de azure-australiaeast. El PE sigue en eastus2; el alias es el de la réplica.",
        "Crear CR-PROD-AUE con el resource ID de ese segundo PE y --region azure-australiaeast. Adjuntar las dos reglas a apoq-prod.<account-id> y a nrem-prod.<account-id>.",
        "DNS: zonas azure-centralus.region.tmprl.cloud → 10.24.0.4 y azure-australiaeast.region.tmprl.cloud → 10.24.0.5. VNet link solo a prod. No crear un A de apoq-prod ni nrem-prod en la zona de la cuenta.",
        "Corte desde internet: adjuntar también la regla pública (máximo una), mover los workers y después detach. Probar el failover: el target del worker no cambia; la resolución pasa de un hostname regional al otro.",
    ]
    y = 44
    for i, text in enumerate(steps, 1):
        d.badge(str(i), 14, y, panel, STEEL if i < 4 else PURPLE)
        d.text(text, 46, y - 4, 1130, 64, panel, size=11)
        y += 70


if __name__ == "__main__":
    from pathlib import Path

    out = Path(__file__).resolve().parent / OUT_NAME
    build().write(out)
    print("ok", out)
