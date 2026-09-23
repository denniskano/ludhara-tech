# Worker / SDK — BCP: Java + OpenTelemetry

Copia local: [dashboards/temporal-sdk-java-otel.json](./dashboards/temporal-sdk-java-otel.json)

**Origen:** https://github.com/tsurdilo/temporal-server-operations/blob/main/observability/dashboards/sdk/temporal-sdk-java-otel.json  
Repo: `tsurdilo/temporal-server-operations` · path `observability/dashboards/sdk/temporal-sdk-java-otel.json` · **v1.4.0** (2026-06-17) · Tihomir Surdilovic (`@temporal.io`)  
Readme: https://github.com/tsurdilo/temporal-server-operations/blob/main/observability/dashboards/sdk/temporal-sdk-java-otel-readme.md

No usar el de Micrometer: los histograms no se llaman igual.

## Importar

1. Prometheus que scrapea el `/metrics` OTel de los pods (AKS). **No** el datasource de D01.
2. Grafana → Import → `dashboards/temporal-sdk-java-otel.json`.
3. Namespace / task queue de la app.

D01/D02: Cloud (`no_poller`). Este tablero: pollers, slots, cache sticky, schedule-to-start, workflow/activity task del proceso Java.

## Qué no sirve

| Fuente | Por qué no |
|---|---|
| Mixin D01 (`temporal-overview.json`) | Solo Cloud (`temporal_cloud_v1_*`). |
| `temporal-sdk-java-micrometer.json` | Otro reporter. |
| [temporalio/dashboards/sdk](https://github.com/temporalio/dashboards/tree/master/sdk) | Mayo 2025. [Issue #75](https://github.com/temporalio/dashboards/issues/75): nombres viejos. No hay JSON Java OTel ahí. |
