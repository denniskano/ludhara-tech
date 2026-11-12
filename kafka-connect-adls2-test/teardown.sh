#!/usr/bin/env bash
# Borra el resource group de prueba y la aplicación del conector.
set -euo pipefail

SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-b4f55447-636d-4d6a-bdb8-ed32bbc32d14}"
RG="${AZURE_RESOURCE_GROUP:-rg-kafka-connect-adls2-test}"
APP_NAME="${AZURE_APP_NAME:-sp-kafka-connect-adls2-test}"

az account set --subscription "$SUBSCRIPTION_ID"

APP_ID="$(az ad app list --display-name "$APP_NAME" --query '[0].appId' -o tsv)"
if [[ -n "$APP_ID" ]]; then
  az ad app delete --id "$APP_ID"
  echo "Aplicación $APP_NAME eliminada."
fi

if az group exists --name "$RG" | grep -q true; then
  az group delete --name "$RG" --yes --no-wait
  echo "Borrado de $RG en curso."
fi
