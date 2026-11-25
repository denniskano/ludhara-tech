#!/usr/bin/env bash
# Configura la demo Tableflow en Confluent Cloud (cluster Basic lkc-2ryr1m, eastus2).
# Usa el CLI con la sesión de "confluent login": provider-integration v2 y tableflow.
#
# Antes, corre ../azure/desplegar.sh. Ese script deja el tenant, la cuenta y el container.
#
#   ./desplegar.sh
#       Crea la provider integration Azure, le pone el tenant y imprime el
#       Application ID para cerrar el acceso en Azure:
#         ../azure/desplegar.sh --app-id <application-id>
#
#   ./desplegar.sh --cerrar
#       Cuando los roles de Azure ya están asignados (espera unos 3 minutos):
#       tópico, Datagen quickstart TRANSACTIONS y Tableflow en Delta.
#       Imprime el table location para Databricks.
#
#   ./desplegar.sh --pausar
#       Pausa Datagen cuando el tópico ya tiene unas decenas de mensajes.
#
#   ./desplegar.sh --catalogo
#       Publica los tópicos Delta en Unity Catalog. Antes tiene que haber
#       corrido ../azure/databricks.sh, que deja el service principal.
set -euo pipefail

ENV="${CONFLUENT_ENV_ID:-env-3r253o}"
CLUSTER="${KAFKA_CLUSTER_ID:-lkc-2ryr1m}"
TOPIC="${KAFKA_TOPIC:-rdv-demo-transactions}"
DLQ="${TABLEFLOW_DLQ:-rdv-demo-tableflow-dlq}"
INTEGRATION_NAME="${PROVIDER_INTEGRATION_NAME:-tableflow-rdv-demo}"
CONNECTOR_NAME="${CONNECTOR_NAME:-datagen-rdv-demo}"
CATALOG_INTEGRATION_NAME="${CATALOG_INTEGRATION_NAME:-tableflow-rdv-uc}"

ROOT="$(cd "$(dirname "$0")" && pwd)"
SALIDAS="$ROOT/salidas.env"
AZURE_SALIDAS="$ROOT/../azure/salidas.env"
DATAGEN_JSON="$ROOT/datagen.json"

MODO="abrir"
INTEGRATION_ID_ARG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cerrar) MODO="cerrar"; shift ;;
    --pausar) MODO="pausar"; shift ;;
    --catalogo) MODO="catalogo"; shift ;;
    --integration-id)
      INTEGRATION_ID_ARG="${2:-}"
      shift 2
      ;;
    *)
      echo "Uso: $0 [--cerrar | --pausar | --catalogo] [--integration-id <cspi-...>]" >&2
      exit 1
      ;;
  esac
done

for cmd in confluent jq; do
  command -v "$cmd" >/dev/null || { echo "Falta $cmd." >&2; exit 1; }
done

sesion_vigente() {
  confluent kafka cluster describe "$CLUSTER" --environment "$ENV" -o json >/dev/null 2>&1
}

if ! sesion_vigente; then
  echo
  echo "La sesión de Confluent caducó. Abre tú el enlace que imprime el CLI; el navegador no se abre solo."
  echo "Cuando la página termine, pega aquí el código que te pida."
  echo
  confluent login --no-browser
  if ! sesion_vigente; then
    echo "Sigo sin poder leer el cluster $CLUSTER en el environment $ENV." >&2
    exit 1
  fi
fi

PROVIDER_INTEGRATION_ID=""
CONFLUENT_APP_ID=""
KAFKA_API_KEY=""
KAFKA_API_SECRET=""
CONNECTOR_ID=""
# Una corrida anterior, con el CLI viejo, pudo haber creado esta key. Se conserva para poder borrarla.
CLOUD_API_KEY=""
CLOUD_API_SECRET=""
CLOUD_API_KEY_PROPIA=0
CATALOG_INTEGRATION_ID=""

if [[ -f "$SALIDAS" ]]; then
  # shellcheck disable=SC1090
  source "$SALIDAS"
fi
[[ -n "$INTEGRATION_ID_ARG" ]] && PROVIDER_INTEGRATION_ID="$INTEGRATION_ID_ARG"

guardar() {
  umask 077
  {
    printf 'CONFLUENT_ENV_ID=%s\n' "$ENV"
    printf 'KAFKA_CLUSTER_ID=%s\n' "$CLUSTER"
    printf 'KAFKA_TOPIC=%s\n' "$TOPIC"
    printf 'PROVIDER_INTEGRATION_ID=%s\n' "$PROVIDER_INTEGRATION_ID"
    printf 'CONFLUENT_APP_ID=%s\n' "$CONFLUENT_APP_ID"
    printf 'KAFKA_API_KEY=%s\n' "$KAFKA_API_KEY"
    printf 'KAFKA_API_SECRET=%s\n' "$KAFKA_API_SECRET"
    printf 'CONNECTOR_ID=%s\n' "$CONNECTOR_ID"
    printf 'CLOUD_API_KEY=%s\n' "$CLOUD_API_KEY"
    printf 'CLOUD_API_SECRET=%s\n' "$CLOUD_API_SECRET"
    printf 'CLOUD_API_KEY_PROPIA=%s\n' "$CLOUD_API_KEY_PROPIA"
    printf 'CATALOG_INTEGRATION_ID=%s\n' "$CATALOG_INTEGRATION_ID"
  } >"$SALIDAS"
  chmod 600 "$SALIDAS"
}

solo_json() {
  printf '%s\n' "$1" | sed -n '/^[\[{]/,$p'
}

leer_azure() {
  if [[ ! -f "$AZURE_SALIDAS" ]]; then
    echo "No está $AZURE_SALIDAS. Primero corre $ROOT/../azure/desplegar.sh." >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  source "$AZURE_SALIDAS"
  : "${AZURE_TENANT_ID:?}"
  : "${AZURE_STORAGE_ACCOUNT:?}"
  : "${AZURE_CONTAINER:?}"
}

campo() {
  local json="$1" filtro="$2"
  printf '%s' "$json" | jq -r "$filtro"
}

app_id_de() {
  campo "$1" '.config.confluent_multi_tenant_app_id // .confluent_multi_tenant_app_id // empty'
}

estado_de() {
  campo "$1" 'if (.status | type) == "string" then .status elif (.status | type) == "object" then (.status.phase // .status.status // empty) else empty end'
}

buscar_integracion() {
  local json
  json="$(confluent provider-integration v2 list --cloud azure --environment "$ENV" -o json 2>/dev/null || true)"
  json="$(solo_json "$json")"
  [[ -n "$json" ]] || return 0
  printf '%s' "$json" | jq -r --arg n "$INTEGRATION_NAME" '
    (if type == "array" then . elif .data then .data else [] end)
    | map(select((.display_name // .name // "") == $n)) | .[0].id // empty'
}

describe_integracion() {
  local raw
  raw="$(confluent provider-integration v2 describe "$PROVIDER_INTEGRATION_ID" --environment "$ENV" -o json)"
  solo_json "$raw"
}

abrir() {
  leer_azure

  if [[ -z "$PROVIDER_INTEGRATION_ID" ]]; then
    PROVIDER_INTEGRATION_ID="$(buscar_integracion || true)"
  fi

  local json
  if [[ -z "$PROVIDER_INTEGRATION_ID" ]]; then
    echo "Creando la provider integration $INTEGRATION_NAME..."
    json="$(solo_json "$(confluent provider-integration v2 create "$INTEGRATION_NAME" --cloud azure --environment "$ENV" -o json)")"
    PROVIDER_INTEGRATION_ID="$(campo "$json" '.id // empty')"
  else
    echo "La provider integration ya existe: $PROVIDER_INTEGRATION_ID"
  fi

  if [[ -z "$PROVIDER_INTEGRATION_ID" ]]; then
    echo "El CLI no devolvió el id de la integración." >&2
    exit 1
  fi

  json="$(describe_integracion)"
  local estado
  estado="$(estado_de "$json")"
  if [[ "$estado" == "DRAFT" || -z "$estado" ]]; then
    echo "Asignando el tenant $AZURE_TENANT_ID..."
    if ! confluent provider-integration v2 update "$PROVIDER_INTEGRATION_ID" \
      --azure-tenant-id "$AZURE_TENANT_ID" --environment "$ENV" -o json >/dev/null; then
      echo "No se pudo guardar el tenant. Sigo si la integración ya lo tiene." >&2
    fi
    json="$(describe_integracion)"
    estado="$(estado_de "$json")"
  fi

  CONFLUENT_APP_ID="$(app_id_de "$json")"
  guardar
  if [[ -z "$CONFLUENT_APP_ID" ]]; then
    echo "La integración $PROVIDER_INTEGRATION_ID no trajo el Application ID." >&2
    echo "$json" >&2
    exit 1
  fi

  echo
  echo "Pega este Application ID en Azure. Crea el service principal y los dos roles:"
  echo "  $ROOT/../azure/desplegar.sh --app-id $CONFLUENT_APP_ID"
  echo
  echo "Estado de la integración: ${estado:-desconocido}."
  echo "Espera unos 3 minutos a que los roles propaguen y cierra la demo con:"
  echo "  $ROOT/desplegar.sh --cerrar"
  echo
  echo "Copia local: $SALIDAS"
}

asegurar_kafka_key() {
  if [[ -n "$KAFKA_API_KEY" && -n "$KAFKA_API_SECRET" ]]; then
    return
  fi
  echo "Creando una API key de Kafka para Datagen..."
  local json
  json="$(solo_json "$(confluent api-key create --resource "$CLUSTER" --description "$CONNECTOR_NAME" --environment "$ENV" -o json)")"
  KAFKA_API_KEY="$(campo "$json" '.api_key // .key // empty')"
  KAFKA_API_SECRET="$(campo "$json" '.api_secret // .secret // empty')"
  if [[ -z "$KAFKA_API_KEY" || -z "$KAFKA_API_SECRET" ]]; then
    echo "La API key de Kafka no salió en JSON." >&2
    exit 1
  fi
  guardar
}

buscar_conector() {
  local json
  json="$(confluent connect cluster list --cluster "$CLUSTER" --environment "$ENV" -o json 2>/dev/null || true)"
  json="$(solo_json "$json")"
  [[ -n "$json" ]] || return 0
  printf '%s' "$json" | jq -r --arg n "$CONNECTOR_NAME" '
    (if type == "array" then . elif .data then .data else [] end)
    | map(select(.name == $n or (.info.name // "") == $n)) | .[0].id // empty'
}

esperar_esquema() {
  local i
  for i in $(seq 1 24); do
    if confluent schema-registry schema describe \
      --subject "${TOPIC}-value" --version latest --environment "$ENV" >/dev/null 2>&1; then
      echo "El subject ${TOPIC}-value ya está en Schema Registry."
      return 0
    fi
    sleep 10
  done
  return 1
}

tableflow_json() {
  local raw
  raw="$(confluent tableflow topic describe "$TOPIC" --cluster "$CLUSTER" --environment "$ENV" -o json 2>/dev/null || true)"
  solo_json "$raw"
}

cerrar() {
  leer_azure
  if [[ -z "$PROVIDER_INTEGRATION_ID" ]]; then
    echo "No hay provider integration. Corre primero $ROOT/desplegar.sh." >&2
    exit 1
  fi

  local json estado
  json="$(describe_integracion)"
  estado="$(estado_de "$json")"
  if [[ "$estado" == "DRAFT" ]]; then
    echo "La integración sigue en DRAFT. Termina el acceso en Azure y espera unos 3 minutos:" >&2
    echo "  $ROOT/../azure/desplegar.sh --app-id $(app_id_de "$json")" >&2
    exit 1
  fi

  echo "Creando el tópico $TOPIC..."
  confluent kafka topic create "$TOPIC" \
    --if-not-exists --partitions 1 --config cleanup.policy=delete \
    --cluster "$CLUSTER" --environment "$ENV"

  asegurar_kafka_key
  CONNECTOR_ID="$(buscar_conector || true)"
  if [[ -z "$CONNECTOR_ID" ]]; then
    echo "Creando el conector $CONNECTOR_NAME (quickstart TRANSACTIONS, AVRO)..."
    jq -n \
      --arg name "$CONNECTOR_NAME" \
      --arg topic "$TOPIC" \
      --arg key "$KAFKA_API_KEY" \
      --arg secret "$KAFKA_API_SECRET" \
      '{name: $name, config: {
          "connector.class": "DatagenSource",
          name: $name,
          "kafka.auth.mode": "KAFKA_API_KEY",
          "kafka.api.key": $key,
          "kafka.api.secret": $secret,
          "kafka.topic": $topic,
          "output.data.format": "AVRO",
          quickstart: "TRANSACTIONS",
          "schema.keyfield": "transaction_id",
          "tasks.max": "1",
          "max.interval": "5000"
        }}' >"$DATAGEN_JSON"
    chmod 600 "$DATAGEN_JSON"
    local creado
    creado="$(solo_json "$(confluent connect cluster create --config-file "$DATAGEN_JSON" \
      --cluster "$CLUSTER" --environment "$ENV" -o json)")"
    CONNECTOR_ID="$(campo "$creado" '.id // empty')"
    guardar
  else
    echo "El conector ya existe: $CONNECTOR_ID"
  fi

  echo "Esperando el esquema del value..."
  if ! esperar_esquema; then
    echo "El subject ${TOPIC}-value no apareció. Revisa el conector y vuelve a correr --cerrar." >&2
    exit 1
  fi

  json="$(tableflow_json)"
  if [[ -z "$json" ]]; then
    echo "Habilitando Tableflow en Delta..."
    confluent tableflow topic enable "$TOPIC" \
      --cluster "$CLUSTER" --environment "$ENV" \
      --storage-type AzureDataLakeStorageGen2 \
      --provider-integration "$PROVIDER_INTEGRATION_ID" \
      --storage-account-name "$AZURE_STORAGE_ACCOUNT" \
      --container-name "$AZURE_CONTAINER" \
      --table-formats DELTA \
      --metadata-column-naming-scheme PORTABLE \
      --error-handling LOG \
      --log-target "$DLQ" \
      --retention-ms 604800000
  else
    echo "Tableflow ya está habilitado en $TOPIC."
    confluent tableflow topic update "$TOPIC" \
      --cluster "$CLUSTER" --environment "$ENV" \
      --metadata-column-naming-scheme PORTABLE \
      --error-handling LOG \
      --log-target "$DLQ" \
      --retention-ms 604800000
  fi

  local path="" i
  for i in $(seq 1 6); do
    json="$(tableflow_json)"
    if [[ -n "$json" ]]; then
      path="$(campo "$json" '.spec.storage.table_path // .storage.table_path // .table_path // empty')"
      [[ -n "$path" ]] && break
    fi
    sleep 20
  done

  echo
  if [[ -n "$path" ]]; then
    echo "Table location para Databricks (CREATE EXTERNAL TABLE ... LOCATION):"
    echo "  $path"
  else
    echo "Tableflow quedó habilitado en $TOPIC. El table location aparece cuando termina el sync."
    echo "Vuelve a consultarlo con:"
    echo "  confluent tableflow topic describe $TOPIC --cluster $CLUSTER --environment $ENV"
  fi
  echo
  echo "Cuando haya unas decenas de mensajes, pausa Datagen:"
  echo "  $ROOT/desplegar.sh --pausar"
  echo
  if ! publicar_catalogo 0; then
    echo "Tableflow ya quedó habilitado. La integración de catálogo no se publicó."
    echo "Cuando el principal exista: $ROOT/desplegar.sh --catalogo"
  fi
  echo
  echo "Copia local: $SALIDAS"
}

publicar_catalogo() {
  local exigido="${1:-0}" json id catalog endpoint
  if [[ ! -f "$AZURE_SALIDAS" ]]; then
    echo "No está $AZURE_SALIDAS. Primero corre ../azure/databricks.sh." >&2
    [[ "$exigido" == 1 ]] && return 1
    return 0
  fi
  # shellcheck disable=SC1090
  source "$AZURE_SALIDAS"
  catalog="${DATABRICKS_CATALOG:-dbw_tableflow_rdv_demo}"
  endpoint="${DATABRICKS_WORKSPACE_URL:-}"
  if [[ -z "${DATABRICKS_SP_CLIENT_ID:-}" || -z "${DATABRICKS_SP_SECRET:-}" || -z "$endpoint" ]]; then
    echo "Falta el service principal de Databricks. Corre ../azure/databricks.sh." >&2
    [[ "$exigido" == 1 ]] && return 1
    return 0
  fi

  json="$(confluent tableflow catalog-integration list --cluster "$CLUSTER" --environment "$ENV" -o json 2>/dev/null || true)"
  json="$(solo_json "$json")"
  if [[ -n "$json" ]]; then
    id="$(printf '%s' "$json" | jq -r --arg n "$CATALOG_INTEGRATION_NAME" '
      (if type == "array" then . elif .data then .data else [] end)
      | map(select((.name // .display_name // .spec.name // .spec.display_name // "") == $n))
      | .[0].id // .[0].spec.id // empty')"
  fi
  if [[ -n "${id:-}" ]]; then
    CATALOG_INTEGRATION_ID="$id"
    guardar
    echo "La catalog integration ya existe: $CATALOG_INTEGRATION_ID"
    return 0
  fi

  echo "Publicando $catalog en Unity Catalog como $CATALOG_INTEGRATION_NAME..."
  json="$(solo_json "$(confluent tableflow catalog-integration create "$CATALOG_INTEGRATION_NAME" \
    --type unity \
    --workspace-endpoint "$endpoint" \
    --catalog-name "$catalog" \
    --unity-client-id "$DATABRICKS_SP_CLIENT_ID" \
    --unity-client-secret "$DATABRICKS_SP_SECRET" \
    --cluster "$CLUSTER" --environment "$ENV" -o json)")"
  CATALOG_INTEGRATION_ID="$(campo "$json" '.id // .spec.id // empty')"
  guardar
  if [[ -z "$CATALOG_INTEGRATION_ID" ]]; then
    echo "El CLI no devolvió el id de la catalog integration." >&2
    printf '%s\n' "$json" | jq 'del(.client_secret, .unity_client_secret, .spec.client_secret, .spec.unity_client_secret)' >&2 || true
    return 1
  fi
  echo "Catalog integration $CATALOG_INTEGRATION_ID."
  echo "En unos minutos aparece el schema ${CLUSTER} dentro de $catalog."
}

pausar() {
  if [[ -z "$CONNECTOR_ID" ]]; then
    CONNECTOR_ID="$(buscar_conector || true)"
  fi
  if [[ -z "$CONNECTOR_ID" ]]; then
    echo "No encontré el conector $CONNECTOR_NAME." >&2
    exit 1
  fi
  confluent connect cluster pause "$CONNECTOR_ID" --cluster "$CLUSTER" --environment "$ENV"
  echo "Conector $CONNECTOR_ID en pausa."
}

case "$MODO" in
  abrir) abrir ;;
  cerrar) cerrar ;;
  pausar) pausar ;;
  catalogo) publicar_catalogo 1 ;;
esac
