# Observabilidad Temporal Cloud — BCP

Corte actual: **solo Temporal Cloud** (`temporal_cloud_v1_*` vía OpenMetrics). Worker Java+OTel: [dashboards-sdk.md](./dashboards-sdk.md). AKS scrape y Private Link: corte siguiente.

**Estado:** D01 instalado. Listos para importar: [D02 SLO](./dashboards/d02-slo.json) y [D03 FinOps](./dashboards/d03-finops.json). Alertas P1 con D02; P3 de gasto con D03. PromQL v0 se apaga el **5 oct 2026**.

El repo [temporalio/dashboards/cloud](https://github.com/temporalio/dashboards/tree/master/cloud) mezcla dos generaciones:

| Archivo | Endpoint | Usar ahora |
|---|---|---|
| `temporal_cloud.json` | PromQL `temporal_cloud_v0_*` | No. Deprecado 2 abr 2026; **apagado 5 oct 2026**. |
| `temporal_cloud_action_costs.json` + alerts YAML | PromQL v0 | No. El mixin OpenMetrics ya trae billable actions y TRU. |
| `temporal_cloud_openmetrics.json` | OpenMetrics `temporal_cloud_v1_*` | Alternativa al mixin. Un solo tablero Cloud canónico, no los dos. |

Referencia: [OpenMetrics](https://docs.temporal.io/cloud/metrics/openmetrics), [catálogo v1](https://docs.temporal.io/cloud/metrics/openmetrics/metrics-reference), [migración v0 → v1](https://docs.temporal.io/cloud/metrics/openmetrics/migration-guide).

## Esta carpeta

| Archivo | Contenido |
|---|---|
| [arquitectura-metricas.drawio](./arquitectura-metricas.drawio) | Diagrama Draw.io: v0 + certificado vs v1 + API key |
| [arquitectura-metricas-libreto.md](./arquitectura-metricas-libreto.md) | Libreto para explicar el diagrama |
| [arquitectura-metricas.md](./arquitectura-metricas.md) | Misma historia en texto / Mermaid |
| [d01-siguiente.md](./d01-siguiente.md) | Overview: validar v1 y namespaces |
| [dashboards/d01-aplicacion.json](./dashboards/d01-aplicacion.json) | Overview de una app: al importar se pide el código |
| [dashboards-por-aplicacion.md](./dashboards-por-aplicacion.md) | Guía para equipos: importar, sin API key ni combo de otras apps |
| [dashboards-sdk.md](./dashboards-sdk.md) | Worker Java + OTel: origen y cómo importar |
| [dashboards/temporal-sdk-java-otel.json](./dashboards/temporal-sdk-java-otel.json) | Copia v1.4.0 de `tsurdilo/temporal-server-operations` (`observability/dashboards/sdk/`) |
| [dashboards/temporal-sdk-java-otel-aplicacion.json](./dashboards/temporal-sdk-java-otel-aplicacion.json) | Mismo SDK, recortado por código de aplicación |
| [d02-importar.md](./d02-importar.md) | Importar D02, alertas P1 y detalle de métricas |
| [dashboards/d02-slo.json](./dashboards/d02-slo.json) | Grafana: SLO (cualquier namespace) |
| [d03-importar.md](./d03-importar.md) | Importar D03, alertas P3 y detalle de métricas |
| [dashboards/d03-finops.json](./dashboards/d03-finops.json) | Grafana: FinOps Actions / TRU |
| [inventario-dashboards.md](./inventario-dashboards.md) | Qué cubre cada JSON publicado (solo Cloud) |
| [paquete-bcp-apoq-nrem.md](./paquete-bcp-apoq-nrem.md) | Pack Cloud (D01 / D01-app / D02 / D03), scrape, SLI, alertas |
| [monitoreo-bcp.html](./monitoreo-bcp.html) | Guía completa: D01/D02/D03, importar, alertas, runbook (abrir en el navegador) |
| [alertas-catalogo.yaml](./alertas-catalogo.yaml) | Alertas P1–P3 sobre `temporal_cloud_v1_*` |

## Decisión de importación

1. Un scrape a `https://metrics.temporal.io/v1/metrics` (API key, rol Metrics Read-Only). **Hecho** si el overview pinta `temporal_cloud_v1_*`.
2. Un solo overview OpenMetrics (el mixin). **Hecho.** No importar también `temporal_cloud_openmetrics.json`.
3. Retirar `temporal_cloud.json` (v0) si existe, antes del 5 oct 2026. No copiar queries `rate()` de v0.
4. Encima de D01: **D02 + alertas P1** y/o **D03 FinOps**. Cada equipo importa [D01-app](./dashboards/d01-aplicacion.json) y, si hay scrape AKS, [SDK-app](./dashboards/temporal-sdk-java-otel-aplicacion.json) con su código.
