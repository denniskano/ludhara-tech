# Kafka, Flink, lakehouse y Databricks

Documentación de cómo integrar **eventos en tópicos Kafka** (Confluent Cloud Dedicated) con **Azure Databricks / lakehouse** (Delta Lake, Iceberg, Unity Catalog), y dónde entra **Apache Flink**.

No es una migración de los 20.000 procesos Databricks. Es un mapa de caminos: cuándo el dato se cura en el tópico (shift-left), cuándo se materializa en Delta, y cuándo el join se queda en Spark.

Consultado el 14 de octubre de 2026.

## Contenido

| Archivo | Qué cubre |
|---|---|
| [01-sabores-databricks-vs-flink.md](01-sabores-databricks-vs-flink.md) | Sabores de Azure Databricks, el 5% con origen Kafka, costos, shift-left |
| [02-kafka-hacia-lakehouse.md](02-kafka-hacia-lakehouse.md) | Todos los escenarios de integración Kafka → lakehouse / Databricks |
| [diagrams/](diagrams/) | Arquitecturas en SVG y PNG, con iconos de las tecnologías |
| [assets/](assets/) | Láminas de la presentación BADI (portada y cierre) |

## Diagramas

1. [Paisaje](diagrams/01-paisaje.png) — Confluent Dedicated vs Azure lakehouse
2. [Tableflow → Delta](diagrams/02-tableflow-delta.png) — camino recomendado de materialización
3. [Databricks lee Kafka](diagrams/03-databricks-kafka-directo.png) — Structured Streaming / Lakeflow Connect
4. [Enriquecimiento](diagrams/04-enriquecimiento.png) — lookup RDB, temporal join CDC, join pesado en Delta
5. [Delta Sharing](diagrams/05-delta-sharing.png) — no alimenta Flink; reparte el resultado analítico
6. [Shift-left vs shift-right](diagrams/06-shift-left.png) — un contrato de stream en vez de N jobs

Para regenerar: `python3 diagrams/build_diagrams.py`

## Cómo leerlo en 30 segundos

- **Lakehouse** = archivos en ADLS (Delta o Iceberg) + catálogo (Unity Catalog). Databricks es el motor que más se usa encima, no el lakehouse mismo.
- **Flink** escribe tópicos, no Delta. El último metro al lakehouse es Tableflow, Connect o un job Spark delgado.
- **Joins chicos** (PK, CDC) ocurren en Flink. **Joins contra historia** ocurren en Databricks.
- **Delta Sharing** no es un connector de Flink. Comparte tablas ya materializadas.
- El **5%** de procesos con origen Kafka Dedicated es el universo. El resto (archivos, JDBC, BI) se queda en Databricks.

## Fuentes principales

- [Tableflow](https://docs.confluent.io/cloud/current/topics/tableflow/overview.html)
- [Tableflow + Unity Catalog](https://docs.confluent.io/cloud/current/topics/tableflow/how-to-guides/catalog-integration/integrate-with-unity-catalog.html)
- [Tableflow en Azure Private Link](https://docs.confluent.io/cloud/current/topics/tableflow/operate/tableflow-private-networking-azure.html)
- [Flink joins / lookup](https://docs.confluent.io/cloud/current/flink/reference/queries/joins.html)
- [Flink external tables](https://docs.confluent.io/cloud/current/flink/concepts/external-tables.html)
- [Databricks Structured Streaming + Kafka](https://docs.databricks.com/aws/en/connect/streaming/kafka/)
- [Lakeflow Connect Kafka](https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/kafka)
