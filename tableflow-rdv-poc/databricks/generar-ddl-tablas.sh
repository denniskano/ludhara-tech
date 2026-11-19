#!/usr/bin/env bash
# Genera 02-ddl-tablas-rdv.sql con la ruta que Tableflow asignó a cada tabla
# (tableflow/table-paths.json, que escribe ajustar-config.sh). Tableflow decide la ruta; no se elige.
set -euo pipefail

aqui="$(cd "$(dirname "$0")" && pwd)"
entrada="${aqui}/../tableflow/table-paths.json"
salida="${aqui}/02-ddl-tablas-rdv.sql"
esquema="${RDV_SCHEMA:-poc_datos.rdv}"
prefijo="${RDV_TOPIC_PREFIX:-rdv-poc-}"

if [[ ! -s "$entrada" ]]; then
  echo "No existe $entrada: correr antes tableflow/ajustar-config.sh." >&2
  exit 1
fi
rutas="$(cat "$entrada")"

a_abfss() {
  local ruta="$1"
  if [[ "$ruta" =~ ^abfss:// ]]; then
    printf '%s' "$ruta"
  elif [[ "$ruta" =~ ^[a-z]+://([^./]+)\.(blob|dfs)\.core\.windows\.net/([^/]+)/(.+)$ ]]; then
    printf 'abfss://%s@%s.dfs.core.windows.net/%s' "${BASH_REMATCH[3]}" "${BASH_REMATCH[1]}" "${BASH_REMATCH[4]}"
  else
    echo "Formato de table_path no reconocido: $ruta" >&2
    exit 1
  fi
}

{
  echo "-- Generado por generar-ddl-tablas.sh a partir de tableflow/table-paths.json."
  echo "-- Sin COMMENT ni TBLPROPERTIES: cualquiera de los dos intenta escribir en el log Delta,"
  echo "-- que es de Tableflow y está en solo lectura para Databricks."
  echo
  for topico in $(jq -r 'keys[]' <<<"$rutas"); do
    ruta="$(jq -r --arg t "$topico" '.[$t]' <<<"$rutas")"
    if [[ -z "$ruta" || "$ruta" == "null" ]]; then
      echo "Tableflow todavía no publicó la ruta de $topico; volver a correr tableflow/ajustar-config.sh." >&2
      exit 1
    fi
    tabla="${topico#"$prefijo"}"
    tabla="${tabla//-/_}"
    echo "-- ${topico}"
    echo "CREATE TABLE IF NOT EXISTS ${esquema}.${tabla}"
    echo "USING DELTA"
    echo "LOCATION '$(a_abfss "$ruta")';"
    echo
  done
} >"$salida"

echo "Escrito $salida"
