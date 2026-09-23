# Guía para equipos — overview de su aplicación

Documento para el equipo de APOQ, NREM, CPCA, etc. PEVE ya tiene la integración Temporal Cloud → Grafana (OpenMetrics + API key de plataforma). **Ustedes no crean API key, no piden certificado y no montan un scrape.**

Archivo a importar: [dashboards/d01-aplicacion.json](./dashboards/d01-aplicacion.json)

## Qué es esto

Un **template** del overview (las mismas preguntas que D01), recortado a los namespaces de **su** código de aplicación.

D01 (el mixin que ya está en Grafana) es del account entero: lo usa PEVE. D02 y D05 también son de plataforma. Este JSON es el que el equipo *Save as* y deja con su código.

## Qué no tienen que hacer

| No | Por qué |
|---|---|
| Crear API key en Temporal Cloud | La key (rol Metrics Read-Only) es de PEVE. Un scrape, un Prometheus. |
| Pedir certificado mTLS de métricas | Eso era el PromQL v0. Ya no aplica. |
| Configurar cada workflow a mano | Los paneles agrupan por `temporal_workflow_type`. Si Cloud emite la serie, aparece. |
| Duplicar el JSON en git por ambiente | Un dashboard. Namespace lista **todos** los que empiezan con su código. |
| Importar D02 o D05 “para su app” | Esos son de guardia y FinOps de account. |

Si D01 (overview de plataforma) ya pinta `temporal_cloud_v1_*`, el datasource sirve. Si D01 está vacío, no es un tema del equipo: avisar a PEVE.

## Qué sí hacen (15 minutos)

1. Grafana → Dashboards → Import → subir `d01-aplicacion.json`.
2. Datasource: el **mismo Prometheus** que pinta el Temporal overview (D01). No crear otro.
3. *Save as* → título `Temporal Cloud Overview — APOQ` (o NREM, CPCA…). Grafana asigna otro uid; no pisen el template.
4. Dashboard settings → Variables → **Aplicación**:
   - Valor por defecto = su código de 4 caracteres en minúsculas (`apoq`, `nrem`, `cpca`…).
   - *Include All*: desactivado (así no ven el resto del banco).
   - *Hide*: Variable (el dropdown Aplicación desaparece; queda Namespace).
5. Save. Star / folder del equipo.

Listo. No hay un paso 6 de “registrar workflows”.

## Varios namespaces y varios workflows

El filtro es solo el **prefijo de 4 caracteres**. No se exige `dev`, `cert` ni `prod`. Entra todo namespace del scrape que empiece con ese código: `apoq-prod`, `apoq-qa`, `apoq-prod-b`, `apoqalgo`.

Ejemplo:

| Namespace en Cloud | ¿Lo ve Aplicación = `apoq`? |
|---|---|
| `apoq-desa`, `apoq-cert`, `apoq-prod` | Sí |
| `apoq-qa`, `apoq-prod-dr` | Sí |
| `nrem-prod` | No |

- **Aplicación = `apoq`** → Namespace lista todos los `apoq*`.
- **Namespace = All** → suma esos, no NREM.
- **Namespace = uno solo** → un ambiente o variante.
- Los **workflow types** y **task queues** salen solos. No se configuran.

Dos códigos (`apti` y `tupi`) = dos copias del template. Un dashboard = un prefijo de 4.

Si un namespace no aparece: no empieza por esos 4 caracteres (mayúsculas, otro código) o no está en el scrape. En Explore, mismo Prometheus:

```
label_values(temporal_cloud_v1_service_request_count, temporal_namespace)
```

Si el nombre está en Explore y no en el dropdown, avisar a PEVE para ajustar la regex. Si no está en Explore, Cloud no está scrapeando ese namespace (filtro del job o el namespace no existe).

## Cómo lo usan el día a día

1. Abrir *su* overview (la copia, no el template ni D01).
2. Elegir en Namespace el o los namespaces del incidente (All = todos los de su código).
3. Lectura: stats de arriba (open, fail+timeout, error rate Start/Signal, no poller, throttle, Actions). Luego el type o la TQ que se movió.
4. El icono **i** de cada panel dice qué métrica es.

No editen queries. Si falta un type de negocio *nominado* (fila “débito” en vez del nombre crudo), eso es D03/D04: lo arma PEVE con el inventario que firme el PO. Este template no lo sustituye.

## Permisos (opcional, PEVE)

El dropdown no es un control de acceso. Quien tenga el template original puede elegir otra aplicación.

Si el equipo no debe ver series de otra app: folder Grafana del equipo + Team Viewer solo ahí, con *su* copia (Aplicación fija y oculta). Explore al mismo Prometheus igual puede pedir otro namespace: el aislamiento fuerte de métricas no es este dashboard.

## Checklist

- [ ] D01 de plataforma ya pinta v1 (si no: PEVE, no el equipo).
- [ ] Import con el Prometheus de D01. Sin API key nueva.
- [ ] *Save as* con el nombre de la app.
- [ ] `aplicacion` = código de 4, All off, variable oculta.
- [ ] Namespace lista todos los que empiezan con ese código (sin filtrar ambiente).
- [ ] En prod hay open / requests / actions (o se entiende por qué está vacío).
- [ ] Los workflow types que el equipo conoce aparecen en completions.

## Dónde está cada cosa

| Quién | Documento |
|---|---|
| Equipo de aplicación (este) | `dashboards-por-aplicacion.md` |
| JSON | `dashboards/d01-aplicacion.json` |
| PEVE: D01, scrape, v0 | `d01-siguiente.md`, `arquitectura-metricas.md` |
| PEVE: guardia / FinOps | `d02-importar.md`, `d05-importar.md` |
| Pack completo | `monitoreo-bcp.html` |
