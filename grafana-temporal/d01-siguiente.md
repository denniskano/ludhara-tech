# D01 instalado — validación y siguiente paso

Estado: Grafana tiene **Temporal overview** (mixin OpenMetrics). Eso es D01. No importar `temporal_cloud_openmetrics.json` ni los JSON PromQL v0.

## Validar ahora (15 minutos)

En Grafana, Explore o un panel del overview:

1. Las queries usan `temporal_cloud_v1_*`. Si aparece `temporal_cloud_v0_*`, el datasource sigue en el endpoint PromQL que se apaga el **5 oct 2026**.
2. El scrape es ~60 s. Más frecuente no da más resolución (Cloud agrega a 1 minuto).
3. Variables del dashboard: `temporal_namespace` lista `apoq-prod` y `nrem-prod` (nombres reales del inventario). Si no salen, el job no filtra esos namespaces o el account no los tiene.
4. Con un namespace prod seleccionado, hay datos en: Open Workflows, Failed, Task backlog, Actions, Service requests. Paneles vacíos en **Activities** o **TRU** pueden ser normales (sin activities en la ventana, o namespace on-demand sin TRU).
5. Percentiles p95/p99 de Start/Signal: si el namespace tiene pocos requests/min, no usarlos como paging.

No hace falta un segundo overview. D01 queda como tablero de exploración de plataforma.

## Siguiente (este corte, solo Cloud)

| Orden | Qué | Dónde |
|---|---|---|
| 1 | D02 SLO | Importar [dashboards/d02-slo.json](./dashboards/d02-slo.json). Pasos: [d02-importar.md](./d02-importar.md). |
| 2 | Alertas P1 | [alertas-catalogo.yaml](./alertas-catalogo.yaml) sobre el mismo datasource. |
| 3 | D03 FinOps | Importar [dashboards/d03-finops.json](./dashboards/d03-finops.json). Pasos: [d03-importar.md](./d03-importar.md). |
| 4 | Overview por app | Importar [d01-aplicacion.json](./dashboards/d01-aplicacion.json) con el código de 4. Guía: [dashboards-por-aplicacion.md](./dashboards-por-aplicacion.md). |
| 5 | SDK Java+OTel | Plataforma o por app. Prometheus AKS. [dashboards-sdk.md](./dashboards-sdk.md). |

Detalle de paneles y SLI: [paquete-bcp-apoq-nrem.md](./paquete-bcp-apoq-nrem.md).
