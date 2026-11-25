#!/usr/bin/env bash
# Crea el ADLS Gen2 de la demo Tableflow en la suscripción personal
# sub-denniskano, región eastus2 (la del cluster Basic lkc-2ryr1m).
#
#   ./desplegar.sh
#       Crea el resource group, la cuenta y el container vacío.
#       Imprime tenant, storage account y container para pegarlos en Confluent Cloud.
#
#   ./desplegar.sh --app-id <application-id>
#       Cuando la consola de Confluent muestra el id de su aplicación multi-tenant,
#       crea el service principal en este tenant y le asigna Reader y
#       Storage Blob Data Contributor sobre la cuenta.
set -euo pipefail

SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-b4f55447-636d-4d6a-bdb8-ed32bbc32d14}"
TENANT_ID="${AZURE_TENANT_ID:-307f28c3-e152-49cf-9f55-bf842a1aa587}"
LOCATION="${AZURE_LOCATION:-eastus2}"
RG="${AZURE_RESOURCE_GROUP:-rg-tableflow-rdv-demo}"
CONTAINER="${AZURE_CONTAINER:-rdv-demo}"
ACCOUNT="${AZURE_STORAGE_ACCOUNT:-sttfrdv$(echo "$SUBSCRIPTION_ID" | tr -d '-' | cut -c1-8)}"

APP_ID="${CONFLUENT_APP_ID:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --app-id)
      APP_ID="${2:-}"
      shift 2
      ;;
    *)
      echo "Uso: $0 [--app-id <application-id-de-confluent>]" >&2
      exit 1
      ;;
  esac
done

ROOT="$(cd "$(dirname "$0")" && pwd)"
SALIDAS="$ROOT/salidas.env"

az account set --subscription "$SUBSCRIPTION_ID"

echo "Suscripción: $SUBSCRIPTION_ID (sub-denniskano)"
echo "Resource group: $RG"
echo "Storage account: $ACCOUNT ($LOCATION)"
echo "Container: $CONTAINER"

az group create \
  --name "$RG" \
  --location "$LOCATION" \
  --tags purpose=tableflow-rdv-demo \
  --output none

if az storage account show --name "$ACCOUNT" --resource-group "$RG" >/dev/null 2>&1; then
  echo "La cuenta $ACCOUNT ya existe."
else
  echo "Creando ADLS Gen2..."
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
    --tags purpose=tableflow-rdv-demo \
    --output none
fi

# -o tsv de una lista escribe un valor por línea. read de una sola línea
# dejaba la región vacía.
{
  read -r HNS
  read -r REGION
  read -r PUBLICA
} < <(az storage account show --name "$ACCOUNT" --resource-group "$RG" \
  --query '[isHnsEnabled, location, publicNetworkAccess]' -o tsv)
HNS="$(printf '%s' "$HNS" | tr '[:upper:]' '[:lower:]')"

if [[ "$HNS" != "true" ]]; then
  echo "La cuenta $ACCOUNT no tiene hierarchical namespace. Hay que borrarla y crearla de nuevo." >&2
  exit 1
fi
if [[ "$REGION" != "eastus2" ]]; then
  echo "La cuenta está en $REGION y el cluster Kafka está en eastus2." >&2
  exit 1
fi
if [[ "$PUBLICA" != "Enabled" ]]; then
  echo "El acceso público está en $PUBLICA. Un cluster Basic no puede usar private endpoints." >&2
  exit 1
fi

KEY="$(az storage account keys list --resource-group "$RG" --account-name "$ACCOUNT" --query '[0].value' -o tsv)"
az storage container create \
  --name "$CONTAINER" \
  --account-name "$ACCOUNT" \
  --account-key "$KEY" \
  --output none

EXISTENTES="$(az storage blob list --account-name "$ACCOUNT" --account-key "$KEY" --container-name "$CONTAINER" --query 'length(@)' -o tsv)"
if [[ "$EXISTENTES" != "0" ]]; then
  echo "El container $CONTAINER ya tiene $EXISTENTES objetos. Tableflow exige que esté vacío al habilitarlo." >&2
  exit 1
fi

asignar_acceso() {
  local app_id="$1"
  echo "Creando el service principal de Confluent ($app_id) en el tenant..."
  if ! az ad sp show --id "$app_id" >/dev/null 2>&1; then
    if ! az ad sp create --id "$app_id" --output none; then
      echo "No se pudo crear el service principal. Si el tenant pide consentimiento, ábrelo con un administrador y vuelve a correr este comando:" >&2
      echo "  https://login.microsoftonline.com/${TENANT_ID}/adminconsent?client_id=${app_id}" >&2
      exit 1
    fi
  fi

  local sp_id storage_id
  sp_id="$(az ad sp show --id "$app_id" --query id -o tsv)"
  storage_id="$(az storage account show --name "$ACCOUNT" --resource-group "$RG" --query id -o tsv)"

  local rol
  for rol in "Reader" "Storage Blob Data Contributor"; do
    if [[ -z "$(az role assignment list --assignee-object-id "$sp_id" --scope "$storage_id" --role "$rol" --query '[0].id' -o tsv)" ]]; then
      az role assignment create \
        --assignee-object-id "$sp_id" \
        --assignee-principal-type ServicePrincipal \
        --role "$rol" \
        --scope "$storage_id" \
        --output none
      echo "Asignado $rol."
    else
      echo "$rol ya estaba asignado."
    fi
  done
  echo "Espera unos 3 minutos y valida la provider integration en Confluent Cloud."
}

if [[ -n "$APP_ID" ]]; then
  asignar_acceso "$APP_ID"
fi

cat >"$SALIDAS" <<EOF
AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID
AZURE_TENANT_ID=$TENANT_ID
AZURE_RESOURCE_GROUP=$RG
AZURE_STORAGE_ACCOUNT=$ACCOUNT
AZURE_CONTAINER=$CONTAINER
AZURE_LOCATION=$LOCATION
CONFLUENT_APP_ID=$APP_ID
EOF
chmod 600 "$SALIDAS"

echo
echo "Tenant ID:        $TENANT_ID"
echo "Storage account:  $ACCOUNT"
echo "Container:        $CONTAINER"
if [[ -z "$APP_ID" ]]; then
  echo
  echo "Siguiente paso, en Confluent Cloud:"
  echo "  $ROOT/../confluent/desplegar.sh"
  echo "Ese script lee esta copia e imprime el Application ID. Ciérralo aquí con:"
  echo "  $(basename "$0") --app-id <application-id>"
fi
echo
echo "Copia local: $SALIDAS"
