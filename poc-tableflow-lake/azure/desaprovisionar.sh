#!/usr/bin/env bash
# Borra lo que creó la demo en Azure. Primero, con el workspace todavía
# en pie, la tabla, el schema, el external location y la credencial de
# Unity Catalog. Después el resource group (storage, workspace, Access
# Connector y el grupo gestionado) y el service principal de Confluent
# en el tenant personal. No borra la cuenta de Databricks ni el metastore.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SALIDAS="$ROOT/salidas.env"

SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-b4f55447-636d-4d6a-bdb8-ed32bbc32d14}"
RG="${AZURE_RESOURCE_GROUP:-rg-tableflow-rdv-demo}"
APP_ID="${CONFLUENT_APP_ID:-}"

if [[ -f "$SALIDAS" ]]; then
  # shellcheck disable=SC1090
  source "$SALIDAS"
  SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-$SUBSCRIPTION_ID}"
  RG="${AZURE_RESOURCE_GROUP:-$RG}"
  APP_ID="${CONFLUENT_APP_ID:-$APP_ID}"
fi

WORKSPACE="${DATABRICKS_WORKSPACE:-dbw-tableflow-rdv-demo}"
MANAGED_RG="${DATABRICKS_MANAGED_RG:-rg-tableflow-rdv-demo-dbw}"
CREDENTIAL="${DATABRICKS_CREDENTIAL:-cred_rdv_demo}"
EXTERNAL_LOCATION="${DATABRICKS_EXTERNAL_LOCATION:-loc_rdv_demo}"
CATALOG="${WORKSPACE//-/_}"
SCHEMA="${CATALOG}.rdv"
TABLE="${SCHEMA}.transactions"

az account set --subscription "$SUBSCRIPTION_ID"

echo "Suscripción: $SUBSCRIPTION_ID"
echo "Resource group a borrar: $RG"
if [[ -n "$APP_ID" ]]; then
  echo "Service principal a quitar del tenant: $APP_ID"
fi

borrar_uc() {
  local host="${DATABRICKS_WORKSPACE_URL:-}" ws="${DATABRICKS_WORKSPACE_ID:-}"
  host="${host#https://}"
  host="${host%/}"
  if [[ -z "$host" || -z "$ws" ]]; then
    echo "No hay workspace en salidas.env. Se omite Unity Catalog."
    return 0
  fi
  if ! az databricks workspace show --name "$WORKSPACE" --resource-group "$RG" >/dev/null 2>&1; then
    echo "El workspace $WORKSPACE ya no está. Se omite Unity Catalog."
    return 0
  fi

  local token tmp code
  token="$(az account get-access-token --resource 2ff814a6-3304-4ab8-85cb-cd0e6f879c1d --query accessToken -o tsv)"
  tmp="$(mktemp)"

  uc_delete() {
    local path="$1" etiqueta="$2"
    code="$(curl -sS -o "$tmp" -w '%{http_code}' -X DELETE \
      -H "Authorization: Bearer ${token}" \
      -H "X-Databricks-Azure-Workspace-Resource-Id: ${ws}" \
      "https://${host}/api/2.1/unity-catalog/${path}")"
    case "$code" in
      200|204) echo "$etiqueta borrado." ;;
      404) echo "$etiqueta ya no estaba." ;;
      *)
        echo "No se pudo borrar $etiqueta (HTTP $code)." >&2
        cat "$tmp" >&2
        rm -f "$tmp"
        return 1
        ;;
    esac
  }

  echo "Quitando la tabla, el schema, el external location y la credencial..."
  uc_delete "tables/${TABLE}" "$TABLE"
  uc_delete "schemas/${SCHEMA}" "$SCHEMA"
  uc_delete "external-locations/${EXTERNAL_LOCATION}" "$EXTERNAL_LOCATION"
  uc_delete "storage-credentials/${CREDENTIAL}" "$CREDENTIAL"
  rm -f "$tmp"
}

borrar_uc

borrar_sp() {
  local host="${DATABRICKS_WORKSPACE_URL:-}" ws="${DATABRICKS_WORKSPACE_ID:-}" id="${DATABRICKS_SP_ID:-}"
  host="${host#https://}"
  host="${host%/}"
  if [[ -z "$id" || -z "$host" || -z "$ws" ]]; then
    return 0
  fi
  if ! az databricks workspace show --name "$WORKSPACE" --resource-group "$RG" >/dev/null 2>&1; then
    return 0
  fi
  local token tmp code
  token="$(az account get-access-token --resource 2ff814a6-3304-4ab8-85cb-cd0e6f879c1d --query accessToken -o tsv)"
  tmp="$(mktemp)"
  code="$(curl -sS -o "$tmp" -w '%{http_code}' -X DELETE \
    -H "Authorization: Bearer ${token}" \
    -H "X-Databricks-Azure-Workspace-Resource-Id: ${ws}" \
    "https://${host}/api/2.0/preview/scim/v2/ServicePrincipals/${id}")"
  rm -f "$tmp"
  case "$code" in
    200|204|404) echo "Service principal tableflow-rdv-sp borrado." ;;
    *) echo "No se pudo borrar el service principal de Databricks (HTTP $code)." >&2 ;;
  esac
}

borrar_sp

if az group exists --name "$RG" -o tsv | grep -qx true; then
  echo "Borrando $RG. Tarda varios minutos..."
  az group delete --name "$RG" --yes --output none
  echo "Resource group $RG borrado."
else
  echo "El resource group $RG no existe."
fi

if az group exists --name "$MANAGED_RG" -o tsv | grep -qx true; then
  echo "Borrando el resource group gestionado $MANAGED_RG..."
  if ! az group delete --name "$MANAGED_RG" --yes --output none; then
    echo "El resource group gestionado sigue ahí. Databricks lo retira al borrar el workspace; si permanece, bórralo en el portal."
  fi
fi

if [[ -n "$APP_ID" ]] && az ad sp show --id "$APP_ID" >/dev/null 2>&1; then
  az ad sp delete --id "$APP_ID"
  echo "Service principal $APP_ID eliminado del tenant."
fi

rm -f "$SALIDAS"
echo "Listo."
