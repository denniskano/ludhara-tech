# Databricks y Unity Catalog

Databricks no es el data lake. El lake es la cuenta ADLS más el formato de tabla. Databricks es el motor que registra esa tabla en Unity Catalog y la consulta. Tableflow es el único writer de esos archivos.

## Alta automática, y por qué no aplica

La integración de Unity Catalog es **por cluster** y publica todos los tópicos habilitados en **Delta** como external tables. Iceberg no entra por esta integración: la página de catálogos dice que las tablas Delta solo se exponen por Unity Catalog, y la de Unity Catalog opera sobre tópicos con formato Delta.

Tableflow crea un schema cuyo nombre es el id del cluster (`lkc-…`), salvo que la integración defina un namespace propio (entonces el schema es ese nombre de negocio). Hace falta, en el workspace:

- Un service principal con secret.
- Sobre el catálogo: Data Editor y el privilegio **EXTERNAL USE SCHEMA** (sin este, la integración no se crea).
- Sobre el external location: `CREATE EXTERNAL TABLE`, `READ FILES`, `WRITE FILES` y **EXTERNAL USE LOCATION**. Este último no viene dentro de `ALL PRIVILEGES`.

`WRITE FILES` en ese service principal permite a Tableflow **crear el objeto external table** por la API abierta de Unity Catalog. No convierte a Databricks en writer de los Parquet.

La página marca la integración como dependiente del Open Preview de Unity Catalog para crear external tables desde clientes externos, y deja la restricción que decide este research:

> Tableflow does not support integrating with Unity Catalogs that are deployed on private networks. The Databricks workspace used for Unity Catalog integration must be accessible over the public internet.

Un workspace del banco, sin endpoint público, no puede recibir ese sync. La misma limitación aparece en la página general de red privada, junto a Polaris.

## Camino que sí cierra: registro manual

La propia guía de Unity Catalog documenta el sustituto para workspace privado. Tableflow sigue escribiendo el Delta en el storage; Unity Catalog se entera por un `CREATE EXTERNAL TABLE` que se ejecuta **una vez**. Los commits posteriores los ve la tabla sin volver a registrarla.

1. Copiar el Table Location del tópico (consola, pestaña Tableflow, o `confluent kafka topic tableflow describe`). En ADLS tiene la forma `abfss://<container>@<cuenta>.dfs.core.windows.net/...`.
2. En el workspace, una storage credential (Access Connector de Databricks) con lectura sobre ese container, y un external location sobre ese path. En el quick start de Delta, el external location se marca **Limit to read-only use**. Así el motor no puede escribir encima de Tableflow.
3. Registrar:

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS `<catalog>`.`<schema>`.`<topic>`
USING DELTA
LOCATION 'abfss://<container>@<cuenta>.dfs.core.windows.net/<prefijo-que-asigna-tableflow>/';
```

4. `SELECT` de comprobación. El nombre del schema lo elige el equipo del lake; el registro manual no hereda el schema `lkc-…` de la integración automática.

El workspace llega a `dfs` por su Private Endpoint. El dato de la consulta no vuelve a entrar a Confluent.

Cada tópico nuevo es otro `CREATE EXTERNAL TABLE`, porque cada uno recibe su propio prefijo. Deshabilitar Tableflow no borra la fila del catálogo: el `DROP TABLE` es aparte, y en una external table no borra los archivos.

## Qué no pedir a este camino

- Que Tableflow cree solo las tablas dentro de un Unity Catalog privado.
- Que Databricks haga la ingesta desde Kafka (Structured Streaming o Lakeflow Connect) si el objetivo es solo materializar. Ese patrón lee el Dedicated desde el workspace, paga el cómputo de ingesta y duplica lo que Tableflow ya escribe. Sigue siendo válido cuando la transformación es un join pesado contra historia Delta durante la carga.
- Que la misma external table sea Iceberg. El workaround documentado es `USING DELTA`.
