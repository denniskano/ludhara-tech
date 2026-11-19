# PoC: tópicos Kafka a RDV con Tableflow

RDV es la capa raw del data lake: guarda cada evento tal cual llega, con su metadata de origen (tópico, partición, offset, timestamp). En esta PoC, Tableflow escribe cada tópico de Confluent Cloud como una tabla Delta directamente en la capa RDV del Azure Data Lake (ADLS Gen2). Databricks es opcional: solo registra esas tablas para consultarlas y no escribe en ellas.

Todo se configura a mano: Azure Portal o `az`, Confluent Cloud Console y SQL. No hay conectores, jobs ni código propio. Agregar un tópico a RDV es habilitarle Tableflow con el mismo storage.

```
Productor (owner) ─► tópico Avro ─► Tableflow ─► Azure Data Lake, capa RDV (Delta) ─► Unity Catalog (opcional, solo lectura)
                                        └─► registros que fallan ─► rdv-poc-tableflow-dlq
```

## Contenido

| Archivo | Qué hace |
|---|---|
| `flink/01-ddl-topicos.sql` | Crea 4 tópicos con esquemas distintos (tipos simples, decimal, record anidado, array, map) y registra sus subjects Avro |
| `flink/02-dml-eventos-prueba.sql` | Inserta 13 eventos de prueba, incluido un reenvío y dos versiones del mismo cliente |
| `tableflow/ajustar-config.sh` | Fija DLQ, nombres de metadata y retención en los 4 tópicos, y guarda la ruta de cada tabla |
| `databricks/01-ddl-unity-catalog.sql` | External location, catálogo, esquema y grants de lectura |
| `databricks/generar-ddl-tablas.sh` | Genera `02-ddl-tablas-rdv.sql` con la ruta real de cada tabla |
| `databricks/03-dml-validacion.sql` | Conteos, duplicados, tipos complejos, metadata, latencia e historia Delta |

## Prerrequisitos

- Cluster Kafka **Dedicated** en Azure, un compute pool de Flink en el mismo environment y Schema Registry habilitado.
- Roles en Confluent Cloud: `CloudClusterAdmin` sobre el cluster, `DeveloperWrite` sobre los subjects y `Assigner` sobre la provider integration.
- Una API key de **Tableflow** (Console: *API keys → Add API key → Tableflow*).
- En Azure: la cuenta ADLS Gen2 del data lake, permiso para crear un container y role assignments en ella, y permiso para dar admin consent a la aplicación multi-tenant de Confluent en el tenant.
- Solo para consultar con SQL: workspace de Databricks con Unity Catalog.
- `az`, `curl` y `jq`.

Variables usadas en los comandos:

```bash
export AZURE_SUBSCRIPTION_ID=<suscripción>
export AZURE_TENANT_ID=<tenant>
export RG=<resource-group-del-data-lake>
export ACCOUNT=<cuenta-adls-del-data-lake>
export CONTAINER=rdv               # container de la capa RDV; debe estar vacío (ver paso 2)
export CONFLUENT_ENV_ID=env-...
export KAFKA_CLUSTER_ID=lkc-...
export TABLEFLOW_API_KEY=... TABLEFLOW_API_SECRET=...
```

## Paso 1. Tópicos (Flink)

En el workspace de Flink (catálogo = environment, base de datos = cluster), ejecutar `flink/01-ddl-topicos.sql`. Los eventos se cargan en el paso 6, después de configurar Tableflow, para que se materialicen ya con los nombres de metadata y el manejo de errores definitivos.

## Paso 2. Capa RDV en el Azure Data Lake

Tableflow escribe en la cuenta ADLS Gen2 del data lake, no en una cuenta nueva. Primero hay que confirmar que esa cuenta cumple lo que pide Tableflow:

```bash
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
az storage account show --name "$ACCOUNT" --resource-group "$RG" \
  --query '{hns:isHnsEnabled, region:primaryLocation, redPublica:publicNetworkAccess}' -o table
```

- `hns` debe ser `True` (es ADLS Gen2).
- `region` debe coincidir con la del cluster Kafka.
- Si `redPublica` es `Disabled`, la sección *Red privada* deja de ser opcional: Tableflow solo llega al lake por Private Endpoint.

**El destino tiene que ser un container vacío y de uso exclusivo de Tableflow.** Tableflow crea su propia estructura debajo (`<container>/<n>/<n>/<org>/<env>/<cluster>/v1/<uuid-tabla>`) y no permite elegir una carpeta como `rdv/kafka/<dominio>/<tópico>`. Si el container encuentra objetos al iniciar, puede fallar o perderlos. Según cómo esté organizada la capa RDV:

| Cómo es la capa RDV hoy | Qué hacer |
|---|---|
| Un container `rdv` vacío o nuevo | Usarlo tal cual: `CONTAINER=rdv` |
| Un container `rdv` que ya tiene datos de otras ingestas | Crear un container hermano solo para Kafka, por ejemplo `CONTAINER=rdv-kafka` |
| Una carpeta `rdv/` dentro de un container compartido (`datalake/rdv/...`) | No se puede apuntar Tableflow a esa carpeta. Crear un container dedicado, por ejemplo `CONTAINER=rdv-kafka` |

En los dos últimos casos, la tabla sigue siendo parte de RDV aunque viva en otro container. Lo que la identifica como RDV es el catálogo (`poc_datos.rdv.*` en Unity Catalog) y la convención del lake, no la carpeta física.

Crear el container si no existe:

```bash
az storage container create \
  --name "$CONTAINER" --account-name "$ACCOUNT" --auth-mode login --output none
az storage fs file list -f "$CONTAINER" --account-name "$ACCOUNT" --auth-mode login -o tsv | head
```

El segundo comando no debe listar nada. Si `az` falla por permisos, el usuario necesita `Storage Blob Data Contributor` sobre la cuenta; el container también se puede crear desde el Portal (*Storage account → Containers → + Container*).

## Paso 3. Provider integration (Confluent Console y Azure)

1. En el Console: *Environment → Provider integrations → Add integration → Microsoft Azure*. Nombre: `tableflow-rdv-poc`.
2. El Console muestra el **ID de la aplicación multi-tenant** de Confluent. Crear su service principal en el tenant:

   ```bash
   az ad sp create --id <app-id-que-muestra-el-console>
   ```

   Si el tenant exige consentimiento de administrador, un admin abre `https://login.microsoftonline.com/$AZURE_TENANT_ID/adminconsent?client_id=<app-id>` y lo aprueba.
3. Dar al service principal los dos roles que pide Tableflow. Como la cuenta es el data lake compartido, la escritura se limita al container RDV, para que Confluent no pueda escribir en las demás capas:

   ```bash
   SP_ID="$(az ad sp show --id <app-id> --query id -o tsv)"
   STORAGE_ID="$(az storage account show --name "$ACCOUNT" --resource-group "$RG" --query id -o tsv)"

   az role assignment create --assignee-object-id "$SP_ID" --assignee-principal-type ServicePrincipal \
     --role "Reader" --scope "$STORAGE_ID" --output none
   az role assignment create --assignee-object-id "$SP_ID" --assignee-principal-type ServicePrincipal \
     --role "Storage Blob Data Contributor" \
     --scope "$STORAGE_ID/blobServices/default/containers/$CONTAINER" --output none
   ```

   La documentación de Tableflow pide los dos roles sobre la cuenta y no menciona el scope por container. Si la validación del paso 4 falla por permisos, mover `Storage Blob Data Contributor` a `--scope "$STORAGE_ID"` y registrar esa excepción con quien administra el lake.

   En el Portal es *Storage account → Access Control (IAM) → Add role assignment* (o *Containers → `$CONTAINER` → Access Control (IAM)* para el scope del container). El service principal se llama parecido a `cspi-xxxx`.
4. Volver al Console, ingresar el **tenant ID** de Azure y validar la integración.

Esperar unos 3 minutos antes del paso 4: Azure tarda en propagar los roles y Tableflow falla si valida el storage antes.

## Paso 4. Habilitar Tableflow (Confluent Console)

Para cada uno de los 4 tópicos `rdv-poc-*`:

1. *Topics → `<tópico>` → Enable Tableflow*.
2. Formato: **Delta**.
3. *Configure custom storage → Store in your storage*. Elegir la provider integration `tableflow-rdv-poc` y completar storage account (`$ACCOUNT`) y container (`$CONTAINER`).
4. Revisar y lanzar.

## Paso 5. Ajustes que el diálogo no pide (API de Tableflow)

```bash
./tableflow/ajustar-config.sh
```

El script actualiza cada tópico por la API REST de Tableflow con:

- `error_handling.mode = LOG` y destino `rdv-poc-tableflow-dlq`: un registro que falla va a la DLQ y el tópico sigue. El default (`SUSPEND`) detiene el tópico entero por un solo registro malo. Tableflow crea la DLQ si no existe.
- `metadata_column_naming_scheme = PORTABLE`: columnas `cflt_metadata_topic`, `cflt_metadata_partition`, `cflt_metadata_offset`, `cflt_metadata_timestamp`, etc. Con `DEFAULT` se llamarían `$$topic`, que es incómodo de consultar.
- `retention_ms = 604800000`: 7 días de snapshots Delta para time travel. No borra datos.

Luego lee el estado de cada tópico, imprime su fase y guarda en `tableflow/table-paths.json` la ruta que Tableflow asignó a cada tabla. Si algún tópico no tiene ruta todavía, esperar un par de minutos y volver a correrlo; es idempotente.

## Paso 6. Eventos (Flink)

Ejecutar `flink/02-dml-eventos-prueba.sql`. La consulta final confirma los eventos del lado de Kafka. Tableflow confirma commits cada pocos minutos en tópicos de bajo volumen.

## Paso 7. Verificar la capa RDV en el lake

Sin Databricks, desde Azure: cada tópico debe tener una carpeta de tabla con `_delta_log/` y archivos Parquet.

```bash
for ruta in $(jq -r '.[]' tableflow/table-paths.json); do
  carpeta="${ruta#*.core.windows.net/}"; carpeta="${carpeta#"$CONTAINER"/}"
  echo "== $carpeta"
  az storage fs file list -f "$CONTAINER" --account-name "$ACCOUNT" --auth-mode login \
    --path "$carpeta" --query "[].name" -o tsv | rg -c '_delta_log/.*\.json$|\.parquet$'
done
```

Cada tópico debe mostrar un número mayor que cero. Si da cero, Tableflow todavía no hizo el primer commit: esperar unos minutos.

## Paso 8. Unity Catalog (Databricks, opcional)

Solo si la capa RDV se consulta con SQL desde Databricks.

1. Crear un **Access Connector for Azure Databricks** y darle a su managed identity solo `Storage Blob Data Reader` sobre la cuenta. Así Azure bloquea cualquier escritura de Databricks en RDV.
2. En *Catalog → External data → Credentials*, crear la storage credential `cred_rdv_poc` con ese Access Connector. La credencial no se puede crear por SQL.
3. Reemplazar `<storage_account>` en `databricks/01-ddl-unity-catalog.sql` y ejecutarlo. En la external location, marcar **Limit to read-only use**.
4. Generar y ejecutar el DDL de tablas:

   ```bash
   ./databricks/generar-ddl-tablas.sh
   ```

   Luego ejecutar `databricks/02-ddl-tablas-rdv.sql` en Databricks.

## Paso 9. Validación con SQL (Databricks, opcional)

Ejecutar `databricks/03-dml-validacion.sql`. Si los conteos salen bajos, esperar el siguiente commit de Tableflow y repetir.

| Tabla | Filas esperadas |
|---|---|
| `cuenta_abierta` | 3 |
| `movimiento_registrado` | 5 (el reenvío de `evt-mv-0002` aparece dos veces, con offsets distintos) |
| `cliente_actualizado` | 3 (dos versiones de `CLI-0001`) |
| `pago_servicio_realizado` | 2 |

Además, ninguna combinación de (partición, offset) debe repetirse, y el `INSERT` comentado al final debe fallar; si funciona, Databricks tiene permisos de escritura que no debería tener.

Desde Flink, `SELECT * FROM \`rdv-poc-tableflow-dlq\`;` debe estar vacío. Antes del primer error el tópico puede no existir.

## Reglas que impone Tableflow

Estas reglas condicionan cómo los equipos owner evolucionan sus esquemas.

- **Compatibilidad `BACKWARD_TRANSITIVE` en el subject del value.** No sirve `FORWARD` ni `FULL`. Los campos nuevos deben ser opcionales con default `null`. Se permite ensanchar tipos (`int`→`long`, `float`→`double`, más precisión en `decimal`). No se permite borrar columnas ni agregar campos dentro de un record anidado existente. Un cambio incompatible suspende la materialización de ese tópico.
- **Tableflow decide la ruta de cada tabla** (`.../<org>/<env>/<cluster>/v1/<uuid>`). No se puede elegir una ruta como `rdv/<dominio>/<tópico>`. La organización por dominio va en Unity Catalog (esquemas y nombres de tabla), no en el path.
- **Tipos.** `timestamp-millis` se materializa como timestamp, pero `timestamp-micros` queda como `bigint`. Por eso los DDL usan `TIMESTAMP_LTZ(3)`.
- **Clave del mensaje.** En modo append, los campos de la clave se agregan como columnas. Por eso los tópicos usan `'value.fields-include' = 'except-key'`, para que la clave no aparezca dos veces.
- **Retención.** `retention_ms` controla los snapshots, no los datos. La retención de datos (`data_retention_ms`, mínimo 30 días) está en Limited Availability y no se usa aquí.

## Red privada

Un data lake corporativo suele tener el acceso público deshabilitado (`redPublica = Disabled` en el paso 2). En ese caso, esto es obligatorio y va antes del paso 4:

- **Storage:** con clusters Dedicated, Tableflow llega al storage por Private Endpoint. En el Console se crea un *Egress Private Link Gateway* en la región, con dos access points sobre la cuenta (subrecursos `blob` y `dfs`), y luego se aprueban los dos private endpoints `plap-xxxxxx` en *Storage account → Networking → Private endpoints* y se crean los registros DNS que indica el Console. Sin private endpoints, Tableflow usa Service Endpoints de Azure.
- **Flink** sobre un cluster privado requiere private networking para Flink en el environment.
- **Unity Catalog:** la integración automática de Tableflow exige un workspace público. Por eso esta PoC registra las tablas a mano con `CREATE TABLE ... LOCATION`, que funciona igual con un workspace privado.

## Limpieza

La cuenta es el data lake compartido: no borrar la cuenta ni su resource group.

1. En el Console, *Disable Tableflow* en cada tópico. Tableflow borra los archivos según la retención de snapshots; para borrarlos antes, eliminar la carpeta de cada tabla en el container.
2. `DROP TABLE` de las tablas en Databricks, y de los tópicos desde Flink.
3. Quitar los dos role assignments del service principal de Confluent y borrar la provider integration.
4. Si el container se creó solo para esta PoC (por ejemplo `rdv-kafka`), borrarlo con `az storage container delete --name "$CONTAINER" --account-name "$ACCOUNT" --auth-mode login`.
