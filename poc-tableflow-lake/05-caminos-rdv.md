# Caminos de un tópico a la capa RDV y a Databricks

RDV es la capa cruda del lake: un evento, una fila, con el origen al lado (tópico, partición, offset, timestamp). Nada se aplasta a "último estado". El cluster de partida es el Dedicated de eastus2, con Private Link de entrada. El storage es ADLS Gen2 en esa misma región.

Hay cuatro maneras de completar el recorrido. Las cuatro pueden dejar datos en el lake y una tabla consultable en Databricks. Cambian quién escribe, el formato y qué pieza de red hace falta. El mapa está en [diagramas/caminos-topico-rdv.drawio](diagramas/caminos-topico-rdv.drawio): la primera lámina los muestra juntos; las otras cuatro son el detalle.

Consultado el 19 de noviembre de 2026.

## Cómo elegir

```
¿El tópico tiene esquema y RDV debe ser una tabla, sin transformar el evento?
  sí → A. Tableflow escribe Delta
  no ↓
¿Hace falta aterrizar el crudo como archivo (sin esquema, carpeta propia, WORM)?
  sí → B. Connect ADLS Gen2, y Databricks lo convierte en Delta
  no ↓
¿Hay que filtrar, deduplicar o joinear durante la ingesta?
  sí → C. Databricks lee el tópico y escribe la Delta
       o Flink cura otro tópico y ese entra por A
  no ↓
¿El lector no es Databricks y el contrato tiene que ser Iceberg?
  sí, y el catálogo es alcanzable → D. Tableflow Iceberg
  sí, y el cluster es este Dedicated privado de Azure → D no cierra.
       La tabla de RDV sigue siendo la Delta de A o de C.
```

Flink no es un quinto camino al lake. Escribe otro tópico. El último metro lo hace A, B o C.

UPSERT de Tableflow (tópico compactado) guarda la última versión de cada clave. Eso es estado actual, no RDV. RDV usa APPEND: `cleanup.policy=delete` y `changelog.mode=append`.

## Los cuatro caminos

| | A. Tableflow Delta | B. Connect ADLS Gen2 | C. Databricks lee Kafka | D. Iceberg |
|---|---|---|---|---|
| Quién escribe el lake | Tableflow | El sink de Connect | Spark o Lakeflow | Tableflow, o Databricks si la Iceberg la escribe él |
| Qué queda en ADLS | Tabla Delta. Parquet + `_delta_log` | Archivos Avro, Parquet, JSON o Bytes | Tabla Delta (managed o external) | Tabla Iceberg, o una Delta que un cliente Iceberg lee después |
| Carpeta | La asigna Tableflow. Container vacío y exclusivo | La eliges: `topics/<tópico>/partition=…` o por tiempo | La de Unity Catalog, o el `LOCATION` que declares | La asigna Tableflow, o la managed de Databricks |
| Esquema obligatorio | Sí, key y value | No. Acepta JSON schemaless y Bytes | Lo define el job | Sí, si escribe Tableflow |
| Evolución | Backward-transitive. Un cambio incompatible suspende el tópico | `schema.compatibility=NONE` | La del job. Lakeflow solo agrega columnas | La de Tableflow, si escribe Tableflow |
| Metadata de RDV | Columnas `cflt_metadata_*` con naming `PORTABLE` | El nombre del archivo lleva tópico, partición y offset inicial | El `select` incluye topic, partition, offset, timestamp. Lakeflow las pone en un struct si se pide `source_metadata_column` | Igual que A, en columnas de la tabla Iceberg |
| Red privada del dato | Egress Private Link Gateway de Tableflow: access points `blob` y `dfs` | Egress Private Link Endpoint del network Dedicated. Subrecurso `dfs`. Con `blob` el conector responde 403 | Private Endpoint de entrada: el cómputo de Databricks hacia el cluster | La escritura BYOS usa el gateway de A. El catálogo no tiene Private Link en Azure |
| Cómo entra a Databricks | `CREATE EXTERNAL TABLE … USING DELTA LOCATION`, una vez. Solo lectura | Auto Loader (`cloudFiles`) escribe una Delta en Unity Catalog. El archivo también se puede registrar como external Avro, Parquet o JSON | La tabla nace en Unity Catalog. Structured Streaming elige managed o external. Lakeflow crea una streaming table | Si la escribe Databricks, Unity Catalog es el catálogo. Si la escribe Tableflow, el catálogo es el IRC de Tableflow o Polaris |
| Cierra en este privado | Sí | Sí | Sí en cómputo classic dentro de una VNet con Private Endpoint al cluster. Lakeflow es serverless y Beta | La escritura de archivos sí. Publicar o leer el catálogo de Tableflow, no |
| Cuándo es RDV | APPEND, sin transformar | El archivo es el crudo. La Delta de Auto Loader es la RDV consultable | APPEND, y el job no aplasta eventos | Igual que A, cuando el contrato pedido es Iceberg |

## A. Tableflow escribe Delta

Es el camino corto cuando el tópico ya tiene contrato y Databricks es quien consulta. Tableflow materializa desde el inicio del log, hace commit del orden de cinco minutos y es el único writer. Databricks registra la external table y lee `dfs` por su propio private endpoint. El alta automática de Unity Catalog exige un workspace público; en este entorno el registro es manual. El detalle de red y de catálogo está en [02-red-privada-eastus2.md](02-red-privada-eastus2.md) y [03-databricks.md](03-databricks.md). El runbook está en [`tableflow-rdv-poc`](../tableflow-rdv-poc/README.md).

El gateway de egress de Tableflow es un recurso distinto del endpoint de egress de Connect. Hacen falta los dos subrecursos, `blob` y `dfs`. Uno por environment y región.

## B. Connect deja archivos, Databricks arma la Delta

El sink fully managed **Azure Data Lake Storage Gen2** de Confluent Cloud exporta el tópico a archivos. Formatos de salida: Avro, Parquet, JSON o Bytes. No escribe Delta ni Iceberg. Sirve para un tópico sin esquema, para un container con política WORM (ahí la entrega pasa a at-least-once) y cuando la carpeta tiene que seguir una convención del lake. Con un partitioner determinista y sin WORM, la entrega hacia el lector de esos archivos es exactly-once. `rotate.schedule.interval.ms` rompe esa garantía.

La red, en un Dedicated con network Private Link, es un **Egress Private Link Endpoint** apuntando a la cuenta con target Data Lake Storage Gen2 y subrecurso `dfs`. Lo usan los conectores del cluster. El storage debería estar en eastus2; otra región implica cargo de transferencia y hay que confirmarla con Confluent.

Databricks no consulta esos archivos como una tabla Delta hasta que un segundo paso los incorpora:

- **Auto Loader** (`cloudFiles`) lee Avro, Parquet o JSON del external location y escribe una tabla Delta de Unity Catalog. El checkpoint vive en otro path, también gobernado por Unity Catalog. Esa Delta es la RDV que se consulta.
- Una external table `USING PARQUET`, `AVRO` o `JSON` apunta al directorio y evita el segundo copy. No es transaccional y no es la RDV de largo plazo si el directorio sigue creciendo.

La misma forma de archivos la produce un Connect self-managed dentro de la VNet del banco. En ese caso el conector usa el private endpoint de la VNet hacia `dfs`, y no hace falta el egress de Confluent Cloud. El storage de prueba de ese conector está en [`kafka-connect-adls2-test`](../kafka-connect-adls2-test/README.md).

## C. Databricks lee el tópico y escribe la Delta

Aquí el writer de RDV es Databricks. El byte sale del Dedicated hacia el cómputo y vuelve a ADLS. Tiene sentido cuando la ingesta filtra, deduplica o joinea contra otra tabla Delta, o cuando el estándar de la plataforma es que toda tabla nazca como managed de Unity Catalog.

Dos herramientas:

- **Structured Streaming** (`spark.readStream.format("kafka")`) en cómputo classic, dentro de una VNet que tenga un Private Endpoint registrado en el Dedicated. El job elige las columnas de metadata y escribe Delta managed o external. En serverless, un notebook o job no puede usar `Trigger.ProcessingTime` ni `Trigger.Continuous`; el trigger admitido es `Trigger.AvailableNow`, o un pipeline de Lakeflow en modo continuo.
- **Lakeflow Connect Kafka**, en Beta. Corre solo en serverless y escribe streaming tables append-only, ya gobernadas por Unity Catalog. No filtra filas, no elige columnas y no hace SCD2. La metadata de Kafka entra como un struct si se configura `source_metadata_column`. Cada pipeline usa un solo cluster. Llegar desde serverless a un Dedicated sin endpoint público es un diseño de red aparte (NCC hacia el Private Link service); el patrón ya documentado de punta a punta es el cómputo classic con Private Endpoint en la VNet.

Este camino paga el cómputo de ingesta en cada tópico. Si el evento no se transforma, A escribe el lake una vez y Databricks solo consulta.

## D. Cuándo Iceberg, y dónde queda Polaris

Delta e Iceberg resuelven lo mismo en el archivo: Parquet con transacciones y evolución de esquema. Se elige por el catálogo y por el motor que lee.

**Delta**, en este entorno, cuando el lector es Databricks. Unity Catalog entiende la external table, el registro manual está documentado y la lectura privada de `dfs` no depende de Confluent.

**Iceberg**, cuando quien lee no es Databricks (Trino, Spark fuera del workspace, Snowflake) y ese motor habla Iceberg REST. Tableflow puede materializar el tópico como Iceberg en el mismo ADLS. El catálogo de esa tabla es el Iceberg REST Catalog de Tableflow, o una copia de la metadata en Apache Polaris / Snowflake Open Catalog. Polaris no guarda los archivos. Guarda el snapshot vigente para que esos motores lo encuentren. La guía de esa integración está escrita para S3, y Snowflake ya no abre Open Catalog a cuentas nuevas: para Snowflake nuevo, Confluent recomienda Horizon, que federá el IRC de Tableflow.

En el Dedicated privado de Azure ese catálogo no tiene camino:

- La catalog integration con Polaris / Open Catalog no está soportada por red privada.
- El IRC de Tableflow tiene Private Link solo en AWS. La página de Azure dice que no hay acceso privado al IRC.

Tableflow sí puede dejar los archivos Iceberg en ADLS por el gateway de egress. Sin un catálogo alcanzable desde la VNet, Databricks no tiene un `CREATE EXTERNAL TABLE` documentado para ese Iceberg, equivalente al de Delta. Por eso D no es un camino de RDV para este cluster.

La variante que sí deja una tabla Iceberg gobernada, sin Polaris, es que **Databricks la escriba**. Una tabla managed Iceberg de Unity Catalog se crea desde Databricks SQL o desde un job del camino C. Unity Catalog expone su propio Iceberg REST (`/api/2.1/unity-catalog/iceberg-rest`) para que Trino, Spark o Flink la lean, con credential vending. El workspace tiene que ser alcanzable por ese cliente. El catálogo, en ese caso, es Unity Catalog. Polaris no interviene.

Un cliente Iceberg también puede leer una Delta de Unity Catalog si esa tabla tiene Iceberg reads habilitado. Es una lectura Iceberg de una tabla Delta. Habilitarlo es una operación de escritura sobre la tabla; en la external de Tableflow, marcada de solo lectura, esa operación no forma parte del diseño.

## Qué no es un camino a RDV

- **Delta Sharing y OpenSharing.** Reparten una tabla que ya existe. No leen el tópico.
- **El sink JDBC de Connect.** Escribe un RDB, no el lake.
- **Un job de Databricks que publica a Kafka.** Es el sentido inverso: del lake hacia un tópico.

## Fuentes

- [Tableflow](https://docs.confluent.io/cloud/current/topics/tableflow/overview.html), [storage](https://docs.confluent.io/cloud/current/topics/tableflow/concepts/tableflow-storage.html), [write modes](https://docs.confluent.io/cloud/current/topics/tableflow/concepts/write-modes.html)
- [Tableflow en Azure Private Networking](https://docs.confluent.io/cloud/current/topics/tableflow/operate/tableflow-private-networking-azure.html) y [límites de red privada](https://docs.confluent.io/cloud/current/topics/tableflow/operate/tableflow-private-networking.html)
- [Unity Catalog](https://docs.confluent.io/cloud/current/topics/tableflow/how-to-guides/catalog-integration/integrate-with-unity-catalog.html) y [Polaris / Open Catalog](https://docs.confluent.io/cloud/current/topics/tableflow/how-to-guides/catalog-integration/integrate-with-snowflake-open-catalog-or-apache-polaris.html)
- [ADLS Gen2 Sink de Confluent Cloud](https://docs.confluent.io/cloud/current/connectors/cc-azure-datalakeGen2-storage-sink.html)
- [Egress Private Link de Connect en Dedicated](https://docs.confluent.io/cloud/current/networking/azure-egress-privatelink.html)
- [Lakeflow Connect Kafka](https://learn.microsoft.com/en-us/azure/databricks/ingestion/lakeflow-connect/kafka-limits) y [Auto Loader](https://learn.microsoft.com/en-us/azure/databricks/ingestion/cloud-object-storage/auto-loader/)
- [Iceberg REST de Unity Catalog](https://learn.microsoft.com/en-us/azure/databricks/external-access/iceberg)
- [Streaming en serverless](https://learn.microsoft.com/en-us/azure/databricks/compute/serverless/limitations)
