#!/usr/bin/env bash
# Crea lo que la demo necesita para consultar la tabla Delta:
# workspace Premium (Unity Catalog), Access Connector y el rol de lectura
# sobre la cuenta de storage. Si el workspace ya tiene metastore, también
# deja la credencial y el external location de solo lectura.
#
# Corre después de ./desplegar.sh. El workspace queda en el mismo resource group.
set -euo pipefail

SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-b4f55447-636d-4d6a-bdb8-ed32bbc32d14}"
LOCATION="${AZURE_LOCATION:-eastus2}"
RG="${AZURE_RESOURCE_GROUP:-rg-tableflow-rdv-demo}"
ACCOUNT="${AZURE_STORAGE_ACCOUNT:-}"
CONTAINER="${AZURE_CONTAINER:-rdv-demo}"
WORKSPACE="${DATABRICKS_WORKSPACE:-dbw-tableflow-rdv-demo}"
CONNECTOR="${DATABRICKS_ACCESS_CONNECTOR:-ac-tableflow-rdv-demo}"
MANAGED_RG="${DATABRICKS_MANAGED_RG:-rg-tableflow-rdv-demo-dbw}"
CREDENTIAL="${DATABRICKS_CREDENTIAL:-cred_rdv_demo}"
EXTERNAL_LOCATION="${DATABRICKS_EXTERNAL_LOCATION:-loc_rdv_demo}"

ROOT="$(cd "$(dirname "$0")" && pwd)"
SALIDAS="$ROOT/salidas.env"

if [[ ! -f "$SALIDAS" ]]; then
  echo "No está $SALIDAS. Primero corre ./desplegar.sh." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$SALIDAS"
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-$SUBSCRIPTION_ID}"
LOCATION="${AZURE_LOCATION:-$LOCATION}"
RG="${AZURE_RESOURCE_GROUP:-$RG}"
ACCOUNT="${AZURE_STORAGE_ACCOUNT:?Falta AZURE_STORAGE_ACCOUNT en salidas.env}"
CONTAINER="${AZURE_CONTAINER:-$CONTAINER}"

az account set --subscription "$SUBSCRIPTION_ID"

poner() {
  local clave="$1" valor="$2" tmp
  tmp="$(mktemp)"
  grep -v "^${clave}=" "$SALIDAS" >"$tmp" || true
  printf '%s=%s\n' "$clave" "$valor" >>"$tmp"
  mv "$tmp" "$SALIDAS"
  chmod 600 "$SALIDAS"
}

echo "Suscripción: $SUBSCRIPTION_ID"
echo "Workspace: $WORKSPACE ($LOCATION, SKU premium)"
echo "Access Connector: $CONNECTOR"

if az databricks access-connector show --name "$CONNECTOR" --resource-group "$RG" >/dev/null 2>&1; then
  echo "El Access Connector $CONNECTOR ya existe."
else
  echo "Creando el Access Connector..."
  az databricks access-connector create \
    --name "$CONNECTOR" \
    --resource-group "$RG" \
    --location "$LOCATION" \
    --identity-type SystemAssigned \
    --tags purpose=tableflow-rdv-demo \
    --output none
fi

PRINCIPAL=""
for _ in 1 2 3 4 5 6; do
  PRINCIPAL="$(az databricks access-connector show --name "$CONNECTOR" --resource-group "$RG" --query identity.principalId -o tsv)"
  [[ -n "$PRINCIPAL" && "$PRINCIPAL" != "None" ]] && break
  sleep 10
done
if [[ -z "$PRINCIPAL" || "$PRINCIPAL" == "None" ]]; then
  echo "El Access Connector no tiene managed identity todavía." >&2
  exit 1
fi

STORAGE_ID="$(az storage account show --name "$ACCOUNT" --resource-group "$RG" --query id -o tsv)"
CONNECTOR_ID="$(az databricks access-connector show --name "$CONNECTOR" --resource-group "$RG" --query id -o tsv)"
if [[ -z "$(az role assignment list --assignee-object-id "$PRINCIPAL" --scope "$STORAGE_ID" --role "Storage Blob Data Reader" --query '[0].id' -o tsv)" ]]; then
  echo "Asignando Storage Blob Data Reader al Access Connector..."
  az role assignment create \
    --assignee-object-id "$PRINCIPAL" \
    --assignee-principal-type ServicePrincipal \
    --role "Storage Blob Data Reader" \
    --scope "$STORAGE_ID" \
    --output none
else
  echo "Storage Blob Data Reader ya estaba asignado."
fi

if az databricks workspace show --name "$WORKSPACE" --resource-group "$RG" >/dev/null 2>&1; then
  echo "El workspace $WORKSPACE ya existe."
else
  echo "Creando el workspace Premium. Tarda varios minutos..."
  az databricks workspace create \
    --name "$WORKSPACE" \
    --resource-group "$RG" \
    --location "$LOCATION" \
    --sku premium \
    --compute-mode Hybrid \
    --public-network-access Enabled \
    --managed-resource-group "$MANAGED_RG" \
    --tags purpose=tableflow-rdv-demo \
    --output none
fi

HOST="$(az databricks workspace show --name "$WORKSPACE" --resource-group "$RG" --query workspaceUrl -o tsv)"
HOST="${HOST#https://}"
HOST="${HOST%/}"
WS_ID="$(az databricks workspace show --name "$WORKSPACE" --resource-group "$RG" --query id -o tsv)"

poner DATABRICKS_WORKSPACE "$WORKSPACE"
poner DATABRICKS_WORKSPACE_URL "https://${HOST}"
poner DATABRICKS_WORKSPACE_ID "$WS_ID"
poner DATABRICKS_ACCESS_CONNECTOR "$CONNECTOR"
poner DATABRICKS_ACCESS_CONNECTOR_ID "$CONNECTOR_ID"
poner DATABRICKS_MANAGED_RG "$MANAGED_RG"
chmod 600 "$SALIDAS"

registrar_uc() {
  local token tmp code
  token="$(az account get-access-token --resource 2ff814a6-3304-4ab8-85cb-cd0e6f879c1d --query accessToken -o tsv)"
  tmp="$(mktemp)"
  code="$(curl -sS -o "$tmp" -w '%{http_code}' \
    -H "Authorization: Bearer ${token}" \
    -H "X-Databricks-Azure-Workspace-Resource-Id: ${WS_ID}" \
    "https://${HOST}/api/2.1/unity-catalog/current-metastore-assignment")"
  if [[ "$code" != "200" ]]; then
    rm -f "$tmp"
    echo "El workspace todavía no tiene un metastore de Unity Catalog."
    echo "Ábrelo en https://${HOST}, asigna el metastore y vuelve a correr este script."
    return 0
  fi
  rm -f "$tmp"

  local body
  body="$(jq -n --arg name "$CREDENTIAL" --arg id "$CONNECTOR_ID" \
    '{name:$name, read_only:true, azure_managed_identity:{access_connector_id:$id}}')"
  code="$(curl -sS -o "$tmp" -w '%{http_code}' \
    -H "Authorization: Bearer ${token}" \
    -H "X-Databricks-Azure-Workspace-Resource-Id: ${WS_ID}" \
    -H 'Content-Type: application/json' \
    "https://${HOST}/api/2.1/unity-catalog/storage-credentials/${CREDENTIAL}")"
  if [[ "$code" == "404" ]]; then
    code="$(curl -sS -o "$tmp" -w '%{http_code}' \
      -H "Authorization: Bearer ${token}" \
      -H "X-Databricks-Azure-Workspace-Resource-Id: ${WS_ID}" \
      -H 'Content-Type: application/json' \
      -X POST "https://${HOST}/api/2.1/unity-catalog/storage-credentials" \
      -d "$body")"
  fi
  if [[ "$code" != "200" && "$code" != "201" ]]; then
    echo "No se pudo crear la credencial $CREDENTIAL (HTTP $code)." >&2
    cat "$tmp" >&2
    rm -f "$tmp"
    return 0
  fi

  local url
  url="abfss://${CONTAINER}@${ACCOUNT}.dfs.core.windows.net/"
  body="$(jq -n --arg name "$EXTERNAL_LOCATION" --arg url "$url" --arg cred "$CREDENTIAL" \
    '{name:$name, url:$url, credential_name:$cred, read_only:true}')"
  code="$(curl -sS -o "$tmp" -w '%{http_code}' \
    -H "Authorization: Bearer ${token}" \
    -H "X-Databricks-Azure-Workspace-Resource-Id: ${WS_ID}" \
    -H 'Content-Type: application/json' \
    "https://${HOST}/api/2.1/unity-catalog/external-locations/${EXTERNAL_LOCATION}")"
  if [[ "$code" == "404" ]]; then
    code="$(curl -sS -o "$tmp" -w '%{http_code}' \
      -H "Authorization: Bearer ${token}" \
      -H "X-Databricks-Azure-Workspace-Resource-Id: ${WS_ID}" \
      -H 'Content-Type: application/json' \
      -X POST "https://${HOST}/api/2.1/unity-catalog/external-locations" \
      -d "$body")"
  fi
  rm -f "$tmp"
  if [[ "$code" != "200" && "$code" != "201" ]]; then
    echo "No se pudo crear el external location $EXTERNAL_LOCATION (HTTP $code)." >&2
    return 0
  fi
  poner DATABRICKS_CREDENTIAL "$CREDENTIAL"
  poner DATABRICKS_EXTERNAL_LOCATION "$EXTERNAL_LOCATION"
  echo "Credencial $CREDENTIAL y external location $EXTERNAL_LOCATION, solo lectura, sobre ${url}"
}

preparar_catalogo() {
  local token tmp code
  token="$(az account get-access-token --resource 2ff814a6-3304-4ab8-85cb-cd0e6f879c1d --query accessToken -o tsv)"
  tmp="$(mktemp)"

  pedir() {
    local method="$1" path="$2" body="${3-}"
    if [[ -n "$body" ]]; then
      code="$(curl -sS -o "$tmp" -w '%{http_code}' -X "$method" \
        -H "Authorization: Bearer ${token}" \
        -H "X-Databricks-Azure-Workspace-Resource-Id: ${WS_ID}" \
        -H 'Content-Type: application/json' \
        "https://${HOST}${path}" -d "$body")"
    else
      code="$(curl -sS -o "$tmp" -w '%{http_code}' -X "$method" \
        -H "Authorization: Bearer ${token}" \
        -H "X-Databricks-Azure-Workspace-Resource-Id: ${WS_ID}" \
        "https://${HOST}${path}")"
    fi
  }

  pedir GET "/api/2.1/unity-catalog/external-locations/${EXTERNAL_LOCATION}"
  if [[ "$code" != "200" ]]; then
    rm -f "$tmp"
    return 0
  fi

  pedir GET "/api/2.1/unity-catalog/current-metastore-assignment"
  local metastore catalog sp_name sp_id app_id
  metastore="$(jq -r '.metastore_id // empty' "$tmp")"
  catalog="$(jq -r '.default_catalog_name // empty' "$tmp")"
  [[ -n "$catalog" ]] || catalog="${WORKSPACE//-/_}"
  sp_name="tableflow-rdv-sp"

  if [[ -n "$metastore" ]]; then
    echo "Activando External data access..."
    pedir PATCH "/api/2.1/unity-catalog/metastores/${metastore}" '{"external_access_enabled":true}'
    if [[ "$code" != "200" ]]; then
      echo "No se pudo activar External data access (HTTP $code)." >&2
      cat "$tmp" >&2
      rm -f "$tmp"
      return 1
    fi
  fi

  pedir GET "/api/2.0/preview/scim/v2/ServicePrincipals"
  sp_id="$(jq -r --arg n "$sp_name" 'first(.Resources[]? | select(.displayName==$n) | .id) // empty' "$tmp")"
  app_id="$(jq -r --arg n "$sp_name" 'first(.Resources[]? | select(.displayName==$n) | .applicationId) // empty' "$tmp")"
  if [[ -z "$sp_id" ]]; then
    echo "Creando el service principal $sp_name..."
    pedir POST "/api/2.0/preview/scim/v2/ServicePrincipals" \
      "$(jq -n --arg n "$sp_name" '{schemas:["urn:ietf:params:scim:schemas:core:2.0:ServicePrincipal"], displayName:$n, active:true}')"
    if [[ "$code" != "200" && "$code" != "201" ]]; then
      echo "No se pudo crear el service principal (HTTP $code)." >&2
      cat "$tmp" >&2
      rm -f "$tmp"
      return 1
    fi
    sp_id="$(jq -r '.id // empty' "$tmp")"
    app_id="$(jq -r '.applicationId // empty' "$tmp")"
  else
    echo "El service principal $sp_name ya existe."
  fi

  if [[ -z "$sp_id" || -z "$app_id" ]]; then
    echo "El service principal no trajo id." >&2
    rm -f "$tmp"
    return 1
  fi

  if [[ -z "${DATABRICKS_SP_SECRET:-}" || "${DATABRICKS_SP_CLIENT_ID:-}" != "$app_id" ]]; then
    pedir POST "/api/2.0/accounts/servicePrincipals/${sp_id}/credentials/secrets" '{}'
    if [[ "$code" != "200" && "$code" != "201" ]]; then
      echo "No se pudo crear el secret del service principal (HTTP $code)." >&2
      cat "$tmp" >&2
      rm -f "$tmp"
      return 1
    fi
    DATABRICKS_SP_SECRET="$(jq -r '.secret // empty' "$tmp")"
    if [[ -z "$DATABRICKS_SP_SECRET" || "$DATABRICKS_SP_SECRET" == *[[:space:]]* || "$DATABRICKS_SP_SECRET" == *"'"* ]]; then
      echo "Databricks no devolvió un secret utilizable." >&2
      rm -f "$tmp"
      return 1
    fi
  fi

  poner DATABRICKS_SP_ID "$sp_id"
  poner DATABRICKS_SP_CLIENT_ID "$app_id"
  poner DATABRICKS_SP_SECRET "$DATABRICKS_SP_SECRET"
  poner DATABRICKS_CATALOG "$catalog"

  conceder() {
    local tipo="$1" nombre="$2" privs="$3"
    pedir PATCH "/api/2.1/unity-catalog/permissions/${tipo}/${nombre}" \
      "$(jq -n --arg p "$app_id" --argjson add "$privs" '{changes:[{principal:$p, add:$add}]}')"
    if [[ "$code" != "200" && "$code" != "201" ]]; then
      echo "No se pudieron conceder permisos sobre ${nombre} (HTTP $code)." >&2
      cat "$tmp" >&2
      return 1
    fi
  }

  conceder catalog "$catalog" \
    '["USE_CATALOG","USE_SCHEMA","CREATE_SCHEMA","CREATE_TABLE","CREATE_FUNCTION","CREATE_VOLUME","SELECT","MODIFY","EXECUTE","READ_VOLUME","WRITE_VOLUME","EXTERNAL_USE_SCHEMA"]'
  conceder external_location "$EXTERNAL_LOCATION" \
    '["CREATE_EXTERNAL_TABLE","READ_FILES","WRITE_FILES","EXTERNAL_USE_LOCATION"]'
  rm -f "$tmp"
  echo "Principal $sp_name listo en el catálogo $catalog. El secret quedó en $SALIDAS."
}

echo "Registrando la credencial y el external location en Unity Catalog..."
registrar_uc
preparar_catalogo

echo
echo "Workspace: https://${HOST}"
echo "El SELECT manual sigue esperando el table location de ./confluent/desplegar.sh --cerrar."
echo "La integración de catálogo se publica con ./confluent/desplegar.sh --catalogo."
echo "Copia local: $SALIDAS"
