# Research: Tableflow al data lake y a Databricks en red privada

Cómo materializar tópicos de un cluster **Confluent Cloud Dedicated en Azure eastus2**, ya en red privada (Private Link de entrada), como tablas en un data lake de la misma región, y cómo consultarlas desde Databricks. Incluye el lugar de Apache Polaris en ese diseño.

Consultado el 19 de noviembre de 2026 contra la documentación vigente de Confluent Cloud. No es un runbook: el camino ejecutable de Delta hacia la capa RDV está en [`tableflow-rdv-poc`](../tableflow-rdv-poc/README.md). El mapa más amplio de Kafka hacia el lakehouse está en [`kafka-flink-lakehouse`](../kafka-flink-lakehouse/README.md).

## Decisión para este entorno

Tableflow escribe las tablas en **ADLS Gen2 de eastus2** (Bring Your Own Storage). El tráfico de datos no sale a internet: un Egress Private Link Gateway, con dos access points (`blob` y `dfs`), conecta Tableflow con la cuenta de storage.

Databricks, con el workspace en red privada, **no recibe el alta automática** de esas tablas. Unity Catalog las registra una vez con `CREATE EXTERNAL TABLE ... USING DELTA LOCATION`, y a partir de ahí lee los archivos por su propio acceso privado al lake. Tableflow sigue haciendo los commits.

**Apache Polaris no entra en este camino.** Polaris (y su producto gestionado, Snowflake Open Catalog) es un catálogo Iceberg REST. Confluent puede publicar ahí la metadata de tablas Iceberg, pero esa integración de catálogo no está soportada por red privada, y en Azure el Iceberg REST Catalog propio de Tableflow tampoco tiene Private Link. El catálogo que cierra el diseño es Unity Catalog, con registro manual.

```
Productores (VNet)
    │  Private Link de entrada
    ▼
Tópicos  ·  Dedicated eastus2
    │
    ▼
Tableflow  ·  formato Delta  ·  BYOS
    │  Egress Private Link  (blob + dfs)
    ▼
ADLS Gen2 eastus2  ·  container exclusivo
    │  Private Endpoint del workspace
    ▼
Databricks  ·  Unity Catalog  ·  external table, solo lectura
```

## Contenido

| Archivo | Qué responde |
|---|---|
| [01-del-topico-al-datalake.md](01-del-topico-al-datalake.md) | Qué mueve Tableflow, Delta frente a Iceberg, storage y reglas de esquema |
| [02-red-privada-eastus2.md](02-red-privada-eastus2.md) | Qué tráfico queda en Private Link y cuál no, en Dedicated eastus2 |
| [03-databricks.md](03-databricks.md) | Cómo llega la tabla a Unity Catalog con el workspace en red privada |
| [04-polaris.md](04-polaris.md) | Qué es Polaris en esta solución y por qué queda fuera del camino privado |
| [05-caminos-rdv.md](05-caminos-rdv.md) | Los cuatro caminos de un tópico a RDV y a Databricks, y cuándo es Delta o Iceberg |
| [demo-basic-eastus2.md](demo-basic-eastus2.md) | Qué aprovisionar y configurar para la demo A en un cluster Basic público de eastus2 |
| [demo-polaris-eastus2.md](demo-polaris-eastus2.md) | Segunda POC, separada: Tableflow en Iceberg y Apache Polaris en lugar de Unity Catalog |
| [manual-consolas.md](manual-consolas.md) | Los mismos pasos desde el portal de Azure y la consola de Confluent |
| [azure/desplegar.sh](azure/desplegar.sh) | Crea el ADLS Gen2 en la suscripción personal e imprime los datos para Confluent |
| [azure/databricks.sh](azure/databricks.sh) | Crea el workspace Premium, el Access Connector y el external location de solo lectura |
| [azure/desaprovisionar.sh](azure/desaprovisionar.sh) | Borra la tabla, el external location, la credencial, el resource group y el service principal de Confluent |
| [confluent/desplegar.sh](confluent/desplegar.sh) | Crea la provider integration, Datagen y Tableflow, e imprime el Application ID y el table location |
| [confluent/desaprovisionar.sh](confluent/desaprovisionar.sh) | Borra el conector, Tableflow, los tópicos, los subjects de la demo y la provider integration |
| [diagramas/arquitectura-tableflow-lake.drawio](diagramas/arquitectura-tableflow-lake.drawio) | Dos láminas: el camino Delta que cierra, y el lugar de Polaris |
| [diagramas/demo-publica-eastus2.drawio](diagramas/demo-publica-eastus2.drawio) | Dos láminas de la demo pública: el alto nivel que cerró el SELECT, y el detalle de lo que se creó |
| [diagramas/privado-databricks-polaris.drawio](diagramas/privado-databricks-polaris.drawio) | Logos y flujos en red privada: Flink estandariza el tópico, el dato llega a Databricks y a Polaris solo iría metadata, sin Private Link |
| [diagramas/caminos-topico-rdv.drawio](diagramas/caminos-topico-rdv.drawio) | Cinco láminas: el mapa y el detalle de cada camino |

## Premisa

| Pieza | Valor en este research |
|---|---|
| Cluster | Confluent Cloud Dedicated, red privada, Azure Private Link de entrada |
| Región | `eastus2` (Virginia). Dedicated, Tableflow, Flink y Schema Registry están disponibles ahí |
| Storage del lake | ADLS Gen2 con hierarchical namespace, en eastus2, acceso público deshabilitado |
| Consumidor analítico | Databricks con Unity Catalog, workspace en red privada |
| Formato propuesto | Delta Lake. Un tópico se habilita en un solo formato (`DELTA` o `ICEBERG`) |

## Fuentes

- [Tableflow overview](https://docs.confluent.io/cloud/current/topics/tableflow/overview.html)
- [Storage](https://docs.confluent.io/cloud/current/topics/tableflow/concepts/tableflow-storage.html)
- [Configurar storage, incluido ADLS](https://docs.confluent.io/cloud/current/topics/tableflow/how-to-guides/configure-storage.html)
- [Schemas](https://docs.confluent.io/cloud/current/topics/tableflow/concepts/tableflow-schemas.html)
- [Write modes](https://docs.confluent.io/cloud/current/topics/tableflow/concepts/write-modes.html)
- [Red privada de Tableflow](https://docs.confluent.io/cloud/current/topics/tableflow/operate/tableflow-private-networking.html)
- [Tableflow con Azure Private Networking](https://docs.confluent.io/cloud/current/topics/tableflow/operate/tableflow-private-networking-azure.html)
- [Catálogos](https://docs.confluent.io/cloud/current/topics/tableflow/how-to-guides/catalog-integration/overview.html)
- [Unity Catalog, incluido el workspace privado](https://docs.confluent.io/cloud/current/topics/tableflow/how-to-guides/catalog-integration/integrate-with-unity-catalog.html)
- [Snowflake Open Catalog / Apache Polaris](https://docs.confluent.io/cloud/current/topics/tableflow/how-to-guides/catalog-integration/integrate-with-snowflake-open-catalog-or-apache-polaris.html)
- [Regiones de Confluent Cloud](https://docs.confluent.io/cloud/current/get-started/regions.html)
