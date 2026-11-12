#!/usr/bin/env bash
# Crea un ADLS Gen2 de prueba y un service principal con permiso de escritura
# para el sink de Kafka Connect (io.confluent.connect.azure.datalake.gen2
# o el conector gestionado AzureDataLakeGen2Sink).
set -euo pipefail

SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-b4f55447-636d-4d6a-bdb8-ed32bbc32d14}"
TENANT_ID="${AZURE_TENANT_ID:-307f28c3-e152-49cf-9f55-bf842a1aa587}"
LOCATION="${AZURE_LOCATION:-eastus}"
RG="${AZURE_RESOURCE_GROUP:-rg-kafka-connect-adls2-test}"
# Nombre estable y válido (3-24, solo minúsculas y números). Derivado de la suscripción.
ACCOUNT="${AZURE_STORAGE_ACCOUNT:-stkadls2$(echo "$SUBSCRIPTION_ID" | tr -d '-' | cut -c1-8)}"
APP_NAME="${AZURE_APP_NAME:-sp-kafka-connect-adls2-test}"
CONTAINER="${AZURE_CONTAINER:-topics}"

ROOT="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$ROOT/.env"

echo "Suscripción: $SUBSCRIPTION_ID"
echo "Resource group: $RG ($LOCATION)"
echo "Storage account: $ACCOUNT"
echo "Contenedor: $CONTAINER"

az account set --subscription "$SUBSCRIPTION_ID"

az group create \
  --name "$RG" \
  --location "$LOCATION" \
  --tags purpose=kafka-connect-adls2-test \
  --output none

if az storage account show --name "$ACCOUNT" --resource-group "$RG" >/dev/null 2>&1; then
  echo "La cuenta $ACCOUNT ya existe."
else
  echo "Creando cuenta ADLS Gen2 (hierarchical namespace)..."
  az storage account create \
    --name "$ACCOUNT" \
    --resource-group "$RG" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --hns true \
    --min-tls-version TLS1_2 \
    --allow-blob-public-access false \
    --public-network-access Enabled \
    --https-only true \
    --tags purpose=kafka-connect-adls2-test \
    --output none
fi

HNS="$(az storage account show --name "$ACCOUNT" --resource-group "$RG" --query isHnsEnabled -o tsv)"
if [[ "$HNS" != "true" ]]; then
  echo "La cuenta $ACCOUNT no tiene hierarchical namespace. ADLS Gen2 exige crearla de nuevo con --hns true." >&2
  exit 1
fi

KEY="$(az storage account keys list --resource-group "$RG" --account-name "$ACCOUNT" --query '[0].value' -o tsv)"
az storage container create \
  --name "$CONTAINER" \
  --account-name "$ACCOUNT" \
  --account-key "$KEY" \
  --output none
echo "Contenedor '$CONTAINER' listo. El conector no lo crea solo."

APP_ID="$(az ad app list --display-name "$APP_NAME" --query '[0].appId' -o tsv)"
if [[ -z "$APP_ID" ]]; then
  echo "Creando aplicación $APP_NAME..."
  APP_ID="$(az ad app create \
    --display-name "$APP_NAME" \
    --sign-in-audience AzureADMyOrg \
    --query appId -o tsv)"
fi

SP_ID="$(az ad sp list --filter "appId eq '$APP_ID'" --query '[0].id' -o tsv)"
if [[ -z "$SP_ID" ]]; then
  echo "Creando service principal..."
  SP_ID="$(az ad sp create --id "$APP_ID" --query id -o tsv)"
fi

STORAGE_ID="$(az storage account show --name "$ACCOUNT" --resource-group "$RG" --query id -o tsv)"
EXISTING_ROLE="$(az role assignment list \
  --assignee-object-id "$SP_ID" \
  --scope "$STORAGE_ID" \
  --role "Storage Blob Data Contributor" \
  --query '[0].id' -o tsv)"
if [[ -z "$EXISTING_ROLE" ]]; then
  echo "Asignando Storage Blob Data Contributor..."
  az role assignment create \
    --assignee-object-id "$SP_ID" \
    --assignee-principal-type ServicePrincipal \
    --role "Storage Blob Data Contributor" \
    --scope "$STORAGE_ID" \
    --output none
fi

if [[ -f "$ENV_FILE" ]] && grep -Eq '^AZURE_CLIENT_SECRET=.+' "$ENV_FILE"; then
  echo "Ya hay un client secret en .env; no se rota."
  CLIENT_SECRET="$(grep '^AZURE_CLIENT_SECRET=' "$ENV_FILE" | cut -d= -f2-)"
else
  echo "Generando client secret (1 año)..."
  CLIENT_SECRET="$(az ad app credential reset \
    --id "$APP_ID" \
    --append \
    --display-name kafka-connect-adls2-test \
    --years 1 \
    --query password -o tsv)"
fi

TOKEN_ENDPOINT="https://login.microsoftonline.com/${TENANT_ID}/oauth2/token"

umask 077
cat >"$ENV_FILE" <<EOF
# Generado por provision.sh. No lo subas a git.
AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID
AZURE_TENANT_ID=$TENANT_ID
AZURE_RESOURCE_GROUP=$RG
AZURE_LOCATION=$LOCATION
AZURE_STORAGE_ACCOUNT=$ACCOUNT
AZURE_CONTAINER=$CONTAINER
AZURE_DFS_ENDPOINT=https://${ACCOUNT}.dfs.core.windows.net
AZURE_BLOB_ENDPOINT=https://${ACCOUNT}.blob.core.windows.net
AZURE_CLIENT_ID=$APP_ID
AZURE_CLIENT_SECRET=$CLIENT_SECRET
AZURE_TOKEN_ENDPOINT=$TOKEN_ENDPOINT
AZURE_STORAGE_ACCOUNT_KEY=$KEY
EOF

cat >"$ROOT/connector.properties" <<EOF
# Sink self-managed. Copia estos valores al entorno donde corre Kafka Connect.
# El secret está en .env; este archivo también está en .gitignore.
name=adls-gen2-sink-test
connector.class=io.confluent.connect.azure.datalake.gen2.AzureDataLakeGen2SinkConnector
tasks.max=1
topics=datalake_topic
flush.size=3
azure.datalake.gen2.client.id=$APP_ID
azure.datalake.gen2.client.key=$CLIENT_SECRET
azure.datalake.gen2.account.name=$ACCOUNT
azure.datalake.gen2.token.endpoint=$TOKEN_ENDPOINT
format.class=io.confluent.connect.azure.storage.format.avro.AvroFormat
EOF

echo
echo "Listo."
echo "  Cuenta:     $ACCOUNT"
echo "  Contenedor: $CONTAINER"
echo "  Client id:  $APP_ID"
echo "  Credenciales (secret y access key): $ENV_FILE"
echo "  Propiedades del conector: $ROOT/connector.properties"
echo "El rol puede tardar un par de minutos en propagarse antes de que el conector escriba."
