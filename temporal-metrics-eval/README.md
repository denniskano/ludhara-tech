# Evaluación de métricas Temporal Cloud (OpenMetrics)

Catálogo de las series `temporal_cloud_v1_*` publicadas en el endpoint OpenMetrics de Temporal Cloud. Sirve para decidir **qué métricas son candidatas a alerta**.

| Archivo | Uso |
|---|---|
| [metricas-temporal-cloud-openmetrics.xlsx](./metricas-temporal-cloud-openmetrics.xlsx) | Catálogo, importancia P1–P3, PromQL borrador |
| [build_excel.py](./build_excel.py) | Regenera el xlsx desde el catálogo embebido |

**Fuente oficial:** [OpenMetrics metrics reference](https://docs.temporal.io/cloud/metrics/openmetrics/metrics-reference) (octubre 2026). Endpoint: `https://metrics.temporal.io/v1/metrics` (API key, rol Metrics Read-Only).

Las series v1 ya son rate por segundo (ventana 1 min) o gauge. **No** envolver en `rate()`. PromQL v0 (`temporal_cloud_v0_*`) quedó apagado el 5 oct 2026.

Regenerar:

```bash
python3 -m venv .venv
.venv/bin/pip install openpyxl
.venv/bin/python build_excel.py
```
