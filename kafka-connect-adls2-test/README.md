# ADLS Gen2 de prueba para el sink de Kafka Connect

Storage de prueba en la suscripción personal `sub-denniskano` (`dennispaitan@outlook.com`) para un conector que corre en otro entorno. El conector no se despliega aquí: solo el lago y la identidad con la que escribe.

## Qué queda creado

| Recurso | Valor |
| --- | --- |
| Suscripción | `sub-denniskano` |
| Resource group | `rg-kafka-connect-adls2-test` |
| Región | `eastus` |
| Cuenta | ADLS Gen2 (`StorageV2` + hierarchical namespace), `Standard_LRS`, solo HTTPS |
| Contenedor | `topics` |
| Identidad | App `sp-kafka-connect-adls2-test` con rol **Storage Blob Data Contributor** sobre la cuenta |
| Red | Acceso público habilitado, para que el Connect del otro entorno llegue por HTTPS |

El conector no crea el contenedor. Con el default `topics.dir=topics` el primer segmento es el nombre del contenedor, así que el filesystem se llama `topics`. Los objetos quedan en:

```text
topics/<tópico>/partition=<n>/<tópico>+<n>+<offset>.avro
```

La cuenta rechaza acceso anónimo al blob. El conector entra con OAuth (client id + client secret) o, si esa versión solo acepta clave, con la access key de la cuenta.

## Crear

Hace falta una sesión de Azure CLI en el tenant personal `307f28c3-e152-49cf-9f55-bf842a1aa587`:

```bash
az login --tenant 307f28c3-e152-49cf-9f55-bf842a1aa587
./provision.sh
```

`provision.sh` es idempotente. El client secret se genera una vez y se guarda en `.env` (permisos 600, ignorado por git). Si `.env` ya tiene secret, no lo rota. `connector.properties` queda al lado, también ignorado, listo para copiar al otro entorno.

El endpoint de token es el v1, que es el que pide el conector:

```text
https://login.microsoftonline.com/<tenant>/oauth2/token
```

No mezclar en la misma config `azure.datalake.gen2.client.*` y la access key: el conector trata las dos vías como excluyentes.

## Qué copiar al otro entorno

Conector self-managed (`AzureDataLakeGen2SinkConnector`): los valores de `connector.properties`.

Conector de Confluent Cloud (`AzureDataLakeGen2Sink`), autenticación con Azure AD:

- Account name: el de `.env`
- Client id / client key: `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET`
- Token endpoint: `AZURE_TOKEN_ENDPOINT`

Si el otro entorno usa access key en lugar de Azure AD: `AZURE_STORAGE_ACCOUNT_KEY`.

El proceso de Connect necesita salida HTTPS hacia `login.microsoftonline.com` y hacia `<cuenta>.dfs.core.windows.net`.

El rol puede tardar unos minutos en verse en el data plane. Un 403 justo después de crearlo suele ser eso.

## Comprobar que escribió

```bash
source .env
az storage blob list \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --container-name "$AZURE_CONTAINER" \
  --account-key "$AZURE_STORAGE_ACCOUNT_KEY" \
  --output table
```

## Borrar

```bash
./teardown.sh
```

Borra la aplicación y el resource group (la cuenta se va con el grupo). El secret deja de servir en cuanto se elimina la app.
