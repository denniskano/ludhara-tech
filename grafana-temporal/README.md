# Observabilidad Temporal Cloud — BCP

Corte actual: **solo Temporal Cloud** (`temporal_cloud_v1_*` vía OpenMetrics). Workers/SDK, AKS y Private Link quedan para un corte siguiente.

**Estado:** D01 instalado. Listos para importar: [D02 SLO](./dashboards/d02-slo.json) y [D05 FinOps](./dashboards/d05-finops.json). Alertas P1 con D02; P3 de gasto con D05. PromQL v0 se apaga el **5 oct 2026**.

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
| [d01-siguiente.md](./d01-siguiente.md) | Overview: validar v1 y namespaces |
| [d02-importar.md](./d02-importar.md) | Cómo importar D02 y crear alertas P1 |
| [dashboards/d02-slo.json](./dashboards/d02-slo.json) | Grafana: SLO (cualquier namespace) |
| [d05-importar.md](./d05-importar.md) | Cómo importar D05 y alertas P3 de gasto |
| [dashboards/d05-finops.json](./dashboards/d05-finops.json) | Grafana: FinOps Actions / TRU |
| [inventario-dashboards.md](./inventario-dashboards.md) | Qué cubre cada JSON publicado (solo Cloud) |
| [paquete-bcp-apoq-nrem.md](./paquete-bcp-apoq-nrem.md) | Cinco dashboards Cloud, SLO, scrape, alertas |
| [monitoreo-bcp.html](./monitoreo-bcp.html) | Guía completa: D01/D02/D05, importar, alertas, runbook (abrir en el navegador) |
| [alertas-catalogo.yaml](./alertas-catalogo.yaml) | Alertas P1–P3 sobre `temporal_cloud_v1_*` |

## Decisión de importación

1. Un scrape a `https://metrics.temporal.io/v1/metrics` (API key, rol Metrics Read-Only). **Hecho** si el overview pinta `temporal_cloud_v1_*`.
2. Un solo overview OpenMetrics (el mixin). **Hecho.** No importar también `temporal_cloud_openmetrics.json`.
3. Retirar `temporal_cloud.json` (v0) si existe, antes del 5 oct 2026. No copiar queries `rate()` de v0.
4. Encima de D01: **D02 + alertas P1** y/o **D05 FinOps** (no hace falta D03/D04 primero). Luego D03–D04.
