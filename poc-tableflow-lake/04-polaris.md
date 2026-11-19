# Dónde encaja Apache Polaris

Polaris es un **catálogo**. No mueve bytes y no sustituye a Tableflow ni a ADLS.

Apache Polaris es el catálogo REST open source de tablas Iceberg. Snowflake Open Catalog es el servicio gestionado construido sobre ese protocolo: la integración de Confluent pide un scope con forma de principal de Polaris (`PRINCIPAL_ROLE:…`), un warehouse, un client id y un client secret. La página vigente de Confluent titula esa integración como Snowflake Open Catalog y avisa que **Snowflake ya no da de alta Open Catalog a cuentas nuevas**; para Snowflake nuevo recomienda Horizon Catalog, que federá el Iceberg REST Catalog de Tableflow en lugar de recibir una copia de la metadata.

En el diseño abierto (cluster alcanzable, storage propio, catálogo con endpoint al que Tableflow puede llamar), el encaje es este:

```
Tópico
  → Tableflow escribe Iceberg en el bucket (BYOS)
  → el IRC de Tableflow queda como catálogo de origen
  → una catalog integration publica la metadata en Polaris / Open Catalog
  → Trino, Spark o Snowflake leen el catálogo y abren los archivos con sus propias credenciales
```

Detalles que la documentación fija para ese encaje:

- La integration es de **cluster**. Publica todos los tópicos Iceberg materializados. Hace falta al menos un tópico con Tableflow activo; si no, el sync se queda en `pending`.
- Un cluster admite varias integrations, pero **una por tipo** de catálogo.
- El IRC de Tableflow sigue siendo el origen. Polaris recibe la metadata; no es una segunda copia de los datos.
- Con BYOS, el IRC **no hace credential vending**. El motor que consulta tiene que poder leer el storage por su cuenta. Polaris tampoco entrega las credenciales del lake.
- Las tablas publicadas son de **solo lectura**.
- La guía paso a paso de la integration está escrita para **Amazon S3** (rol IAM, bucket, catálogo externo de Open Catalog). No hay una guía equivalente para ADLS.
- El sync de catálogo puede fallar sin frenar la escritura de los archivos.

Ese es el sitio de Polaris: un catálogo Iceberg compartido entre motores que no son Databricks, cuando Tableflow puede hablar con él.

## Por qué no entra en este Dedicated de eastus2

Tres límites se acumulan, y con uno solo ya se cae:

1. **Red privada.** La página de private networking lista Unity Catalog y Snowflake Open Catalog / Apache Polaris entre las integraciones de catálogo que no están soportadas por red privada. Tableflow, sentado en el cluster privado, no publica metadata hacia un Polaris del banco.
2. **Azure.** Aunque un motor quisiera saltarse Polaris y usar el IRC de Tableflow, ese catálogo no tiene Private Link en Azure. El ingress Private Link del IRC existe solo en AWS.
3. **El consumidor de este research es Databricks.** Unity Catalog gobierna las tablas Delta con el registro manual de [03-databricks.md](03-databricks.md). Poner Polaris al lado duplica el catálogo y deja las tablas en un formato (Iceberg) cuyo workaround privado no está documentado.

Horizon, el reemplazo que Confluent recomienda para Snowflake, también necesita alcanzar el IRC de Tableflow. En Azure privado ese alcance no existe. No es un sustituto de Polaris para este cluster.

## Cuándo valdría reabrirlo

Polaris vuelve a la mesa si aparece un lector que no puede usar Unity Catalog (Trino, un Spark fuera de Databricks, un Snowflake que exija Iceberg) **y** se cumple alguna de estas dos cosas:

- Confluent publica acceso privado al IRC en Azure, o admite la catalog integration hacia un endpoint privado. Hoy ninguna de las dos está en la documentación.
- Se acepta, de forma explícita y acotada, que la **metadata** del catálogo viaje por un endpoint alcanzable desde Confluent, mientras los archivos siguen en ADLS por Private Link. Eso relaja la premisa de red privada y hay que decidirlo como excepción de seguridad, no como detalle de implementación.

Hasta entonces, Polaris se queda documentado como el catálogo del camino Iceberg multi-motor, y fuera del diagrama que se puede construir hoy en eastus2.
