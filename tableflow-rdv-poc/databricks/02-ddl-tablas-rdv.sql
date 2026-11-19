-- Plantilla. ./generar-ddl-tablas.sh reescribe este archivo con la ruta real de
-- cada tabla (tableflow/table-paths.json).
-- Sin COMMENT ni TBLPROPERTIES: cualquiera de los dos intenta escribir en el log Delta,
-- que es de Tableflow y está en solo lectura para Databricks.

-- rdv-poc-cliente-actualizado
CREATE TABLE IF NOT EXISTS poc_datos.rdv.cliente_actualizado
USING DELTA
LOCATION 'abfss://rdv@<storage_account>.dfs.core.windows.net/<table_path>';

-- rdv-poc-cuenta-abierta
CREATE TABLE IF NOT EXISTS poc_datos.rdv.cuenta_abierta
USING DELTA
LOCATION 'abfss://rdv@<storage_account>.dfs.core.windows.net/<table_path>';

-- rdv-poc-movimiento-registrado
CREATE TABLE IF NOT EXISTS poc_datos.rdv.movimiento_registrado
USING DELTA
LOCATION 'abfss://rdv@<storage_account>.dfs.core.windows.net/<table_path>';

-- rdv-poc-pago-servicio-realizado
CREATE TABLE IF NOT EXISTS poc_datos.rdv.pago_servicio_realizado
USING DELTA
LOCATION 'abfss://rdv@<storage_account>.dfs.core.windows.net/<table_path>';
