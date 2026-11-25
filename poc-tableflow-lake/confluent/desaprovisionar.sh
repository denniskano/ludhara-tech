#!/usr/bin/env bash
# Borra lo que creó desplegar.sh en Confluent Cloud: conector, Tableflow,
# la catalog integration, tópicos, los subjects de esta demo, la API key
# de Kafka y la provider integration. No toca el environment, el cluster
# ni el resto de subjects.
# No borra Azure. Para eso corre ../azure/desaprovisionar.sh después.
set -euo pipefail

ENV="${CONFLUENT_ENV_ID:-env-3r253o}"
CLUSTER="${KAFKA_CLUSTER_ID:-lkc-2ryr1m}"
TOPIC="${KAFKA_TOPIC:-rdv-demo-transactions}"
DLQ="${TABLEFLOW_DLQ:-rdv-demo-tableflow-dlq}"
CONNECTOR_NAME="${CONNECTOR_NAME:-datagen-rdv-demo}"

ROOT="$(cd "$(dirname "$0")" && pwd)"
SALIDAS="$ROOT/salidas.env"
DATAGEN_JSON="$ROOT/datagen.json"

for cmd in confluent jq; do
  command -v "$cmd" >/dev/null || { echo "Falta $cmd." >&2; exit 1; }
done

if [[ ! -f "$SALIDAS" ]]; then
  echo "No está $SALIDAS. No hay una demo registrada por desplegar.sh." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$SALIDAS"
TOPIC="${KAFKA_TOPIC:-$TOPIC}"
ENV="${CONFLUENT_ENV_ID:-$ENV}"
CLUSTER="${KAFKA_CLUSTER_ID:-$CLUSTER}"

if ! confluent kafka cluster describe "$CLUSTER" --environment "$ENV" -o json >/dev/null 2>&1; then
  echo
  echo "La sesión de Confluent caducó. Abre tú el enlace que imprime el CLI; el navegador no se abre solo."
  echo "Cuando la página termine, pega aquí el código que te pida."
  echo
  confluent login --no-browser
fi

solo_json() {
  printf '%s\n' "$1" | sed -n '/^[\[{]/,$p'
}

if [[ -z "${CONNECTOR_ID:-}" ]]; then
  json="$(confluent connect cluster list --cluster "$CLUSTER" --environment "$ENV" -o json 2>/dev/null || true)"
  json="$(solo_json "$json")"
  if [[ -n "$json" ]]; then
    CONNECTOR_ID="$(printf '%s' "$json" | jq -r --arg n "$CONNECTOR_NAME" '
      (if type == "array" then . elif .data then .data else [] end)
      | map(select(.name == $n or (.info.name // "") == $n)) | .[0].id // empty')"
  fi
fi

if [[ -n "${CONNECTOR_ID:-}" ]]; then
  echo "Borrando el conector $CONNECTOR_ID..."
  confluent connect cluster delete "$CONNECTOR_ID" --force --cluster "$CLUSTER" --environment "$ENV"
fi

if confluent tableflow topic describe "$TOPIC" --cluster "$CLUSTER" --environment "$ENV" -o json >/dev/null 2>&1; then
  echo "Deshabilitando Tableflow en $TOPIC..."
  confluent tableflow topic disable "$TOPIC" --force --cluster "$CLUSTER" --environment "$ENV"
fi

for t in "$TOPIC" "$DLQ"; do
  if confluent kafka topic describe "$t" --cluster "$CLUSTER" --environment "$ENV" -o json >/dev/null 2>&1; then
    echo "Borrando el tópico $t..."
    confluent kafka topic delete "$t" --force --cluster "$CLUSTER" --environment "$ENV"
  fi
done

borrar_subject() {
  local subject="$1"
  if confluent schema-registry schema describe \
    --subject "$subject" --version latest --environment "$ENV" >/dev/null 2>&1; then
    echo "Borrando el subject $subject..."
    confluent schema-registry schema delete \
      --subject "$subject" --version all --environment "$ENV" --force
  fi
  confluent schema-registry schema delete \
    --subject "$subject" --version all --environment "$ENV" --permanent --force >/dev/null 2>&1 || true
}

borrar_subject "${TOPIC}-value"
borrar_subject "${TOPIC}-key"

CATALOG_INTEGRATION_NAME="${CATALOG_INTEGRATION_NAME:-tableflow-rdv-uc}"
if [[ -z "${CATALOG_INTEGRATION_ID:-}" ]]; then
  json="$(confluent tableflow catalog-integration list --cluster "$CLUSTER" --environment "$ENV" -o json 2>/dev/null || true)"
  json="$(solo_json "$json")"
  if [[ -n "$json" ]]; then
    CATALOG_INTEGRATION_ID="$(printf '%s' "$json" | jq -r --arg n "$CATALOG_INTEGRATION_NAME" '
      (if type == "array" then . elif .data then .data else [] end)
      | map(select((.name // .display_name // .spec.name // .spec.display_name // "") == $n))
      | .[0].id // .[0].spec.id // empty')"
  fi
fi
if [[ -n "${CATALOG_INTEGRATION_ID:-}" ]]; then
  echo "Borrando la catalog integration $CATALOG_INTEGRATION_ID..."
  confluent tableflow catalog-integration delete "$CATALOG_INTEGRATION_ID" --force \
    --cluster "$CLUSTER" --environment "$ENV"
fi

if [[ -n "${PROVIDER_INTEGRATION_ID:-}" ]] \
  && confluent provider-integration v2 describe "$PROVIDER_INTEGRATION_ID" --environment "$ENV" -o json >/dev/null 2>&1; then
  echo "Borrando la provider integration $PROVIDER_INTEGRATION_ID..."
  confluent provider-integration v2 delete "$PROVIDER_INTEGRATION_ID" --force --environment "$ENV"
fi

if [[ -n "${KAFKA_API_KEY:-}" ]] && confluent api-key describe "$KAFKA_API_KEY" -o json >/dev/null 2>&1; then
  echo "Borrando la API key de Kafka..."
  confluent api-key delete "$KAFKA_API_KEY" --force
fi

if [[ -n "${CLOUD_API_KEY:-}" && "${CLOUD_API_KEY_PROPIA:-0}" != "1" ]] \
  && confluent api-key describe "$CLOUD_API_KEY" -o json >/dev/null 2>&1; then
  echo "Borrando la Cloud API key que dejó una versión anterior del script..."
  confluent api-key delete "$CLOUD_API_KEY" --force
fi

rm -f "$SALIDAS" "$DATAGEN_JSON"
echo "Listo en Confluent. Los archivos locales de secretos se borraron."
echo "Para borrar el storage: $ROOT/../azure/desaprovisionar.sh"
