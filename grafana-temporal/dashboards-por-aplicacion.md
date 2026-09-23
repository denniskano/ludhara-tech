# Guía para equipos — overview de su aplicación

Documento para el equipo de APOQ, NREM, CPCA, etc. PEVE ya tiene la integración Temporal Cloud → Grafana (OpenMetrics + API key de plataforma). **Ustedes no crean API key, no piden certificado y no montan un scrape.**

Archivos: [dashboards/d01-aplicacion.json](./dashboards/d01-aplicacion.json) (Cloud) · [dashboards/temporal-sdk-java-otel-aplicacion.json](./dashboards/temporal-sdk-java-otel-aplicacion.json) (worker Java+OTel)

## Qué es esto

Cada equipo **baja este JSON, lo importa y escribe su código**. El dashboard queda de **esa** aplicación: solo namespaces que empiezan con ese prefijo. Los workflow types de esa app salen solos. **No hay combo de otras apps ni tablero por type nominado.**

D01 (mixin) es el overview del account (PEVE). D02 y D03 también son de plataforma.

## Qué no tienen que hacer

| No | Por qué |
|---|---|
| Crear API key en Temporal Cloud | La key es de PEVE. Un scrape, un Prometheus. |
| Pedir certificado mTLS de métricas | Eso era el PromQL v0. |
| Elegir “Aplicación” en un dropdown | El código se fija **al importar**. No se ven otras apps. |
| Configurar cada workflow | Aparecen solos (`temporal_workflow_type`). |

Si D01 de plataforma ya pinta `v1_*`, usen ese Prometheus. Si D01 está vacío: PEVE.

## Importar (10 minutos)

1. Grafana → Dashboards → Import → subir `d01-aplicacion.json`.
2. **Prometheus:** el mismo que el Temporal overview (D01).
3. **Código de aplicación:** solo el prefijo (`apoq`). Eso filtra namespaces (`apoq*`). **No** cambia el título.
4. **Name:** Grafana lo deja como `Temporal Cloud Overview — ${APP_CODE}`. **Hay que reemplazar `${APP_CODE}` a mano** (ej. `Temporal Cloud Overview — apoq`). El campo código no lo sustituye.
5. **UID:** si aparece `temporal-cloud-overview-${APP_CODE}`, reemplazar igual (`temporal-cloud-overview-apoq`). Si no, el segundo import pisa el primero.
6. Import. La fila de arriba dice `Resumen — apoq`. Solo combo **Namespace**.

NREM: Name `Temporal Cloud Overview — nrem`. APTI y TUPI: dos imports.

Worker Java+OTel: hay 3 Grafana Cloud (DESA / CERT / PROD). Importar `temporal-sdk-java-otel-aplicacion.json` en el stack **del entorno donde están los workers** (no PEVE / D01), mismo código. El tablero es **por aplicación** en ese entorno: todos sus AKS y namespaces `apoq*`. Name `Temporal Java SDK (OTel) — apoq`. UID `temporal-sdk-java-otel-apoq`. Detalle: [dashboards-sdk.md](./dashboards-sdk.md).

## Qué ven después

El filtro es el prefijo que escribieron. Entra todo namespace del scrape que empiece con ese código. No se exige `dev`/`cert`/`prod`.

| Namespace en Cloud | Código `apoq` |
|---|---|
| `apoq-desa`, `apoq-cert`, `apoq-prod`, `apoq-qa` | Sí |
| `nrem-prod` | No |

- **Namespace = All** → todos los de su código.
- **Un namespace** → un ambiente o variante.
- Workflows y task queues: solos.

Si no lista un namespace: no empieza por ese código, o no está en el scrape. Explore, mismo Prometheus:

```
label_values(temporal_cloud_v1_service_request_count, temporal_namespace)
```

Si se equivocaron de código: Dashboard settings → Variables → `aplicacion` (está oculta; tipo constant) → poner el prefijo correcto → Save.

## Día a día

1. Abrir *su* overview (`Temporal Cloud Overview — apoq`), no D01 ni el de otro equipo.
2. Namespace: All o el del incidente.
3. Stats de arriba, luego type o TQ. Icono **i** del panel = qué métrica es.

No editen queries. Los workflow types de esa app salen solos en Completions (`temporal_workflow_type`). No hay tablero aparte por type de negocio.

Explore al mismo Prometheus puede pedir otro namespace: este dashboard no es un firewall. Folder + Team Grafana si no deben ver el JSON de otra app.

## Checklist

- [ ] D01 de plataforma pinta v1.
- [ ] Import: Prometheus de D01 + **su** código. En **Name** (y UID) reemplazar `${APP_CODE}`. Sin API key.
- [ ] No hay combo Application con la lista del banco.
- [ ] Namespace solo muestra prefijos de su código.
- [ ] Completions muestra los workflow types que conocen.

## Dónde está cada cosa

| Quién | Documento |
|---|---|
| Equipo de aplicación (este) | `dashboards-por-aplicacion.md` |
| JSON Cloud | `dashboards/d01-aplicacion.json` |
| JSON worker | `dashboards/temporal-sdk-java-otel-aplicacion.json` · [dashboards-sdk.md](./dashboards-sdk.md) |
| PEVE: D01, scrape, v0 | `d01-siguiente.md`, `arquitectura-metricas.md` |
| PEVE: guardia / FinOps | `d02-importar.md`, `d03-importar.md` |
| Pack completo | `monitoreo-bcp.html` |
