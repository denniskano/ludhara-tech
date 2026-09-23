# Libreto — diagrama de métricas Temporal Cloud

Para explicar `arquitectura-metricas.drawio`. Duración: **4 a 6 minutos**. Audiencia: PEVE, SRE, Arquitectura. No es una sesión de dashboards (D02/D05 se nombran al final, no se recorren).

Señalar las cajas de izquierda a derecha. No leer el pie de página entero.

---

## Apertura (20 s)

Este diagrama es solo el **plano de métricas**. Los workers en AKS y Temporal Cloud como orquestador **no cambian**. Lo que cambia es **cómo Grafana se autentica y cómo consume las series**.

Arriba, en rojo, es lo que teníamos: PromQL v0. Abajo, en verde, es lo que usamos ahora: OpenMetrics v1. Temporal apaga el camino de arriba el **5 de octubre de 2026**. Si el 6 de octubre un tablero sigue pidiendo `temporal_cloud_v0_*`, se queda en blanco.

---

## Franja roja — Antes (1,5 min)

Empiezo igual en las dos franjas: **Workers AKS** hablan por gRPC con **Temporal Cloud**. Eso es el negocio. No lo tocamos.

Lo que era frágil es lo que sigue a la derecha. Cloud exponía un **endpoint PromQL**. Las series se llamaban `temporal_cloud_v0_*` y eran **contadores que solo subían**. Por eso en Grafana teníamos que poner `rate()` o `increase()`. Si alguien copiaba esas queries a v1, las métricas quedan mal: v1 ya viene como tasa por segundo.

El recuadro amarillo es el punto de la historia: **para entrar a ese PromQL hacía falta un certificado de cliente, mTLS**. Emitirlo, instalarlo en el datasource o en el scrape, rotarlo, no dejarlo vencer. Eso era costo operativo y un secreto más que custodiar.

Con el certificado puesto, Grafana consultaba ese PromQL y pintaba `temporal_cloud.json` y el JSON de **action costs**. Las alertas del YAML oficial de Temporal también iban con `rate()`. FinOps era otro tablero, no el overview.

Pie de la franja: deprecado en abril de 2026, **corte el 5 de octubre**. No hay que “arreglar” v0. Hay que dejar de usarlo.

---

## Franja verde — Ahora (2 min)

Misma izquierda: workers, Cloud. A la derecha ya no hay PromQL.

Cloud publica **OpenMetrics** en `metrics.temporal.io/v1/metrics`. Las series son `temporal_cloud_v1_*`. Ya vienen agregadas a **un minuto**: o son rate por segundo, o son un gauge. **No se usa `rate()`.**

El recuadro verde es el reemplazo del certificado: **API key Bearer**, rol **Metrics Read-Only**. Se guarda en el secret del scrape, se rota como cualquier clave. **Ya no hay certificado de cliente para métricas.** El cert de v0 se retira con el endpoint viejo; no se “migra” a OpenMetrics.

Prometheus o el Agent **hacen pull cada 60 segundos**. Más frecuente no da más resolución: Cloud ya agregó a un minuto. Ese job alimenta **un solo datasource** de Grafana.

Sobre ese datasource:

- **D01** es el mixin, overview del account. Ya está instalado.
- **D02** es guardia SLO. **D05** es FinOps. Mismo account, no recortados por app.
- **D01-app** es el template para que cada aplicación vea solo `{código}-(dev|desa|cert|prod)`.
- Las alertas P1 a P3 del YAML van contra `v1_*`, sin `rate()`.

---

## Cierre — la barra de abajo (30 s)

La frase de la barra: **certificado cliente mTLS pasa a API key Bearer**. Eso es lo que hay que recordar si preguntan “qué cambió de seguridad”.

Cómo validar en 30 segundos: Explore. Si sale `v0_*`, el datasource sigue en el camino rojo. D02 y D05 no pintan contra v0. Si sale `v1_*` y D01 tiene datos, el scrape nuevo está hecho.

Lo que **no** está en este diagrama: métricas del SDK en el worker, Private Link, AKS. Eso es otro corte.

---

## Si preguntan

| Pregunta | Respuesta corta |
|---|---|
| ¿Los pagos dejan de usar Temporal Cloud? | No. Solo cambia el camino de métricas. |
| ¿Hay que renovar el certificado de métricas? | No. Se retira. Ahora es API key. |
| ¿Por qué 60 segundos? | Cloud publica ventanas de 1 min. Scrapear a 15 s no da más detalle y puede pegar el rate limit del endpoint. |
| ¿Por qué no copiar las queries viejas? | v0 era contador; v1 ya es rate. `rate()` sobre v1 está mal. |
| ¿D01 y el JSON OpenMetrics de Temporal? | Uno solo. Ya tenemos el mixin. No importar los dos. |
| ¿Y el JSON de costs? | v0. El gasto está en D05. |

---

## Versión de 60 segundos (ascensor)

Este dibujo no es Temporal Cloud en sí: es **cómo leemos sus métricas**. Arriba, Grafana llegaba por PromQL con **certificado mTLS** a series `v0_*` que había que derivar con `rate()`. Ese camino se apaga el 5 de octubre. Abajo, hacemos scrape OpenMetrics cada minuto con **API key de solo lectura**. Las series `v1_*` ya vienen listas. Encima armamos D01, D02, D05 y el template por aplicación. Workers y orquestación no se tocan.
