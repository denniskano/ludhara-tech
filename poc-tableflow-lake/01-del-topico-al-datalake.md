# Del tópico al data lake

Tableflow materializa un tópico de Kafka como una tabla **Apache Iceberg** o **Delta Lake**. Se encarga de la esquematización, la conversión de tipos, la evolución de esquema compatible, la materialización de streams CDC y la publicación al catálogo. El motor analítico lee la tabla; no hace falta un conector ni un job de ingesta por tópico.

La frescura documentada es de unos 5 minutos para registros recién producidos. En tópicos de bajo volumen, donde el segmento de Kafka todavía no se llenó, Tableflow intenta publicar cada 5 minutos. Ese intento es best-effort.

## Qué se puede usar en un Dedicated privado

Un cluster con red privada **solo admite Bring Your Own Storage**. Confluent Managed Storage queda descartado: ese storage lo opera Confluent, solo existe para Iceberg, y las integraciones con catálogos externos no aplican sobre él.

En Azure el BYOS es una cuenta **ADLS Gen2** (hierarchical namespace habilitado) **en la misma región que el cluster**. Para este entorno, cuenta y cluster viven en **eastus2**. El cifrado en reposo de Azure (SSE) funciona sin configuración extra en Tableflow.

Condiciones del destino, tomadas de la guía de storage:

- El container tiene que estar **vacío** al habilitar Tableflow. Objetos previos pueden impedir el arranque o perderse en la inicialización.
- Varios tópicos comparten la misma provider integration y la misma cuenta. La integration se crea a nivel de environment.
- Tableflow asigna el prefijo de cada tabla. La guía de limpieza documenta esta forma: `<container>/<######>/<######>/<org>/<env>/<cluster>/v1/<table-id>`. No se elige una carpeta de negocio (`rdv/<dominio>/<tópico>`).
- Una vez habilitado el tópico sobre ese container, no se puede cambiar de container ni pasar a Confluent Managed Storage.
- Los objetos no se editan ni se borran a mano mientras la tabla está activa: se corrompe.

La provider integration de Azure crea un service principal multi-tenant de Confluent en el tenant. Sobre la cuenta hacen falta los roles **Reader** y **Storage Blob Data Contributor**. Limitar el segundo rol al container es una decisión de gobierno del lake; la documentación pide ambos roles sobre la cuenta. Si la validación falla con el scope reducido, el rol de datos vuelve a la cuenta.

## Delta o Iceberg

El CLI habilita **un** formato por tópico: `DELTA` o `ICEBERG` (`--table-formats`, default `ICEBERG`).

| | Delta Lake | Iceberg |
|---|---|---|
| Storage en este cluster | BYOS obligatorio (Delta nunca usa Confluent Managed Storage) | BYOS obligatorio, porque el cluster es privado |
| Cómo la descubre Databricks | Unity Catalog, como external table | Iceberg REST Catalog de Tableflow, o un catálogo externo sincronizado |
| Camino privado en Azure | Los archivos sí. El alta automática en Unity Catalog no | Los archivos sí. El catálogo REST de Tableflow no tiene Private Link en Azure |
| Encaje con este Databricks privado | El documentado | Queda a la espera de un catálogo alcanzable |

Para un consumidor que es Databricks sobre Unity Catalog, el formato que la documentación deja cerrado es **Delta**. Iceberg pasa a ser la opción cuando el lector es Trino, Spark genérico o Snowflake y puede hablar con un catálogo Iceberg. Ese caso es el de [04-polaris.md](04-polaris.md).

Los dos formatos conviven en el mismo cluster: cada tópico elige uno, y pueden compartir la provider integration. Un tópico no se publica en los dos formatos a la vez.

## Qué lee Tableflow del tópico

- Key y value tienen esquema (Avro, Protobuf o JSON Schema) en Schema Registry. Un tópico sin esquema no se habilita.
- Al habilitar Tableflow sobre un tópico que ya tiene datos, materializa **desde el principio del log**. El tópico tiene que ser legible desde el offset cero.
- Las tablas retract de Flink no están soportadas.
- El modo de escritura sale de `cleanup.policy` y `changelog.mode`, y no se cambia con Tableflow activo. Cambiarlo obliga a deshabilitar, reconfigurar y volver a habilitar, lo que crea una tabla nueva.

| cleanup.policy | changelog.mode | Modo Tableflow |
|---|---|---|
| `delete` | `append` | APPEND: cada registro es una fila nueva, exactly-once |
| `compact` | `upsert` | UPSERT: la clave más el número de partición son la primary key; queda la última versión |
| `delete,compact` | `upsert` | UPSERT |

En APPEND, los campos de la clave se agregan como columnas. Si el mismo campo viaja en key y en value, en UPSERT manda el value. En UPSERT la clave no evoluciona, y Tableflow mantiene una tabla de índice aparte.

La evolución que Tableflow aplica durante la materialización es la **backward-transitive**:

- Una columna nueva es opcional y su default es `null`. Otro default no está soportado en ese modo.
- Se puede ensanchar `int` → `long`, `float` → `double`, y subir la precisión de un `decimal`.

Un registro que no cumple esas reglas **suspende la materialización de ese tópico**. El overview también lista la eliminación de columnas entre los cambios que Tableflow absorbe cuando el Schema Registry los considera compatibles; la página de schemas es la que fija la lista operativa de evoluciones soportadas. Pasar el subject a compatibilidad `NONE` no abre la puerta a cambios que Tableflow no sepa materializar.

Los errores de un registro se configuran al habilitar el tópico: `SUSPEND` (default: para el tópico), `SKIP` o `LOG` (el registro va a un tópico destino y el resto sigue).

## Qué queda en el lake

Archivos Parquet más el log del formato (`_delta_log` en Delta, metadata de Iceberg en Iceberg). La retención por defecto de snapshots o versiones es 7 días (`retention_ms = 604800000`); controla historia para time travel, no borra la tabla. El overview añade que Tableflow conserva entre 10 y 100 snapshots y que ese conteo no lo configura el usuario.

Al deshabilitar Tableflow, los archivos se limpian en diferido según esa retención. En BYOS se pueden borrar antes, a mano, por el prefijo de la tabla.

## Flink delante, si hace falta

Flink en Confluent Cloud escribe tópicos, no el lake. Si el evento hay que filtrarlo, deduplicarlo o enriquecerlo antes de que exista como tabla, el tópico de salida de Flink es el que lleva Tableflow. eastus2 ofrece Flink con red pública y privada; un compute pool atado a un cluster Dedicated privado usa la red privada del environment. Si el tópico ya nace con el contrato definitivo, Tableflow se habilita directo sobre él.
