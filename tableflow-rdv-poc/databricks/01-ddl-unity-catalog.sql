-- =============================================================================
-- PoC RDV: lado Databricks. Unity Catalog solo registra las tablas que
-- Tableflow escribe; Databricks nunca escribe en ellas.
--
-- Prerrequisito, fuera de SQL (Catalog Explorer, CLI o Terraform):
--   Storage credential `cred_rdv_poc` sobre un Access Connector de Databricks
--   cuya managed identity tenga SOLO `Storage Blob Data Reader` en la cuenta.
--   Así Azure bloquea cualquier escritura desde Databricks sobre RDV.
--
-- Después de crearla, marcar la external location como "Limit to read-only use"
-- en Catalog Explorer.
--
-- Reemplazar <storage_account> por el nombre de la cuenta del paso 2.
-- =============================================================================

CREATE EXTERNAL LOCATION IF NOT EXISTS rdv_poc_tableflow
  URL 'abfss://rdv@<storage_account>.dfs.core.windows.net/'
  WITH (STORAGE CREDENTIAL cred_rdv_poc);

CREATE CATALOG IF NOT EXISTS poc_datos;

CREATE SCHEMA IF NOT EXISTS poc_datos.rdv;

-- Lectura para la capa siguiente; nadie recibe MODIFY.
GRANT USE CATALOG ON CATALOG poc_datos TO `datos-ingenieria`;
GRANT USE SCHEMA, SELECT ON SCHEMA poc_datos.rdv TO `datos-ingenieria`;
