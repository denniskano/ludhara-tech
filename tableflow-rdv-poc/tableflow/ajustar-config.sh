#!/usr/bin/env bash
# Se corre después de habilitar Tableflow en el Console. Fija en cada tópico lo que
# el diálogo de habilitación no pide (DLQ, nombres de metadata, retención de
# snapshots) y guarda la ruta que Tableflow asignó a cada tabla.
set -euo pipefail

: "${CONFLUENT_ENV_ID:?Falta CONFLUENT_ENV_ID (env-...)}"
: "${KAFKA_CLUSTER_ID:?Falta KAFKA_CLUSTER_ID (lkc-...)}"
: "${TABLEFLOW_API_KEY:?Falta TABLEFLOW_API_KEY}"
: "${TABLEFLOW_API_SECRET:?Falta TABLEFLOW_API_SECRET}"

dlq="${TABLEFLOW_DLQ_TOPIC:-rdv-poc-tableflow-dlq}"
retencion_ms="${TABLEFLOW_RETENTION_MS:-604800000}"
topicos=(
  rdv-poc-cuenta-abierta
  rdv-poc-movimiento-registrado
  rdv-poc-cliente-actualizado
  rdv-poc-pago-servicio-realizado
)

api="https://api.confluent.cloud/tableflow/v1/tableflow-topics"
alcance="environment=${CONFLUENT_ENV_ID}&spec.kafka_cluster=${KAFKA_CLUSTER_ID}"
salida="$(cd "$(dirname "$0")" && pwd)/table-paths.json"

cuerpo="$(jq -n \
  --arg env "$CONFLUENT_ENV_ID" \
  --arg lkc "$KAFKA_CLUSTER_ID" \
  --arg ret "$retencion_ms" \
  --arg dlq "$dlq" \
  '{spec: {
      environment: {id: $env},
      kafka_cluster: {id: $lkc},
      config: {
        retention_ms: $ret,
        metadata_column_naming_scheme: "PORTABLE",
        error_handling: {mode: "LOG", target: $dlq}
      }
  }}')"

llamar() {
  curl -sS --fail-with-body -u "${TABLEFLOW_API_KEY}:${TABLEFLOW_API_SECRET}" \
    -H 'Content-Type: application/json' "$@"
}

rutas='{}'
faltan=0
for topico in "${topicos[@]}"; do
  llamar -X PATCH "${api}/${topico}" -d "$cuerpo" >/dev/null
  estado="$(llamar "${api}/${topico}?${alcance}")"

  jq -r --arg t "$topico" '
    "\($t): fase=\(.status.phase // "?")"
    + " naming=\(.spec.config.metadata_column_naming_scheme // "?")"
    + " errores=\(.spec.config.error_handling.mode // "?")"
    + (if .status.error_message then " error=\(.status.error_message)" else "" end)' <<<"$estado"

  ruta="$(jq -r '.spec.storage.table_path // empty' <<<"$estado")"
  if [[ -z "$ruta" ]]; then
    echo "  Sin table_path todavía: revisar que el storage sea ADLS propio y volver a correr." >&2
    faltan=$((faltan + 1))
    continue
  fi
  rutas="$(jq --arg t "$topico" --arg r "$ruta" '. + {($t): $r}' <<<"$rutas")"
done

if ((faltan > 0)); then
  rm -f "$salida"
  echo "Faltan $faltan rutas; no se escribe $salida." >&2
  exit 1
fi
echo "$rutas" >"$salida"
echo "Rutas guardadas en $salida"
