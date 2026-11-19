-- =============================================================================
-- PoC RDV: validación en Databricks después de flink/02-dml-eventos-prueba.sql.
-- Tableflow confirma commits cada pocos minutos: si los conteos dan menos,
-- esperar y volver a correr.
-- =============================================================================

-- 1. Columnas: las del esquema Avro, la clave del mensaje y la metadata de Kafka
--    (cflt_metadata_topic, cflt_metadata_partition, cflt_metadata_offset, ...).
DESCRIBE TABLE poc_datos.rdv.cliente_actualizado;

-- 2. Conteos contra lo que insertó el DML de Flink.
SELECT 'cuenta_abierta' AS tabla, COUNT(*) AS filas, 3 AS esperadas FROM poc_datos.rdv.cuenta_abierta
UNION ALL
SELECT 'movimiento_registrado', COUNT(*), 5 FROM poc_datos.rdv.movimiento_registrado
UNION ALL
SELECT 'cliente_actualizado', COUNT(*), 3 FROM poc_datos.rdv.cliente_actualizado
UNION ALL
SELECT 'pago_servicio_realizado', COUNT(*), 2 FROM poc_datos.rdv.pago_servicio_realizado;

-- 3. Tableflow no duplica: cada (partición, offset) aparece una sola vez. Esperado: 0 filas.
SELECT cflt_metadata_partition, cflt_metadata_offset, COUNT(*) AS veces
FROM poc_datos.rdv.movimiento_registrado
GROUP BY cflt_metadata_partition, cflt_metadata_offset
HAVING COUNT(*) > 1;

-- 4. RDV guarda tal cual llega: el reenvío del productor sí está, con otro offset.
--    Esperado: evt-mv-0002 con 2 filas.
SELECT evento_id, COUNT(*) AS filas, COLLECT_LIST(cflt_metadata_offset) AS offsets
FROM poc_datos.rdv.movimiento_registrado
GROUP BY evento_id
HAVING COUNT(*) > 1;

-- 5. Historia completa por entidad: las dos versiones de CLI-0001.
SELECT cliente_id, evento_id, email, direccion.distrito, direccion.ciudad, ocurrido_en
FROM poc_datos.rdv.cliente_actualizado
WHERE cliente_id = 'CLI-0001'
ORDER BY ocurrido_en;

-- 6. Tipos complejos: array, map y decimal llegan tipados, no como texto.
SELECT cliente_id, telefono
FROM poc_datos.rdv.cliente_actualizado
LATERAL VIEW EXPLODE(telefonos) t AS telefono;

SELECT pago_id, monto, atributos['canal'] AS canal, atributos['periodo'] AS periodo
FROM poc_datos.rdv.pago_servicio_realizado;

SELECT tipo, moneda, SUM(monto) AS total, TYPEOF(SUM(monto)) AS tipo_total
FROM poc_datos.rdv.movimiento_registrado
GROUP BY tipo, moneda;

-- 7. Trazabilidad al origen: tópico, partición y offset de cada fila.
SELECT cflt_metadata_topic, cflt_metadata_partition, cflt_metadata_offset, cflt_metadata_timestamp, cuenta_id
FROM poc_datos.rdv.cuenta_abierta
ORDER BY cflt_metadata_timestamp;

-- 8. Latencia de materialización: del timestamp de Kafka a ahora.
SELECT
  MAX(cflt_metadata_timestamp)                                             AS ultimo_evento,
  TIMESTAMPDIFF(SECOND, MAX(cflt_metadata_timestamp), CURRENT_TIMESTAMP()) AS segundos_desde_ultimo
FROM poc_datos.rdv.movimiento_registrado;

-- 9. Versiones Delta que escribió Tableflow y time travel sobre la primera.
DESCRIBE HISTORY poc_datos.rdv.movimiento_registrado;

SELECT COUNT(*) AS filas_en_version_inicial
FROM poc_datos.rdv.movimiento_registrado VERSION AS OF 0;

-- 10. RDV es de solo lectura para Databricks. Esta sentencia debe fallar con
--     un error de permisos sobre el storage; si funciona, el Access Connector
--     tiene más permisos de los que debe.
-- INSERT INTO poc_datos.rdv.cuenta_abierta (cuenta_id) VALUES ('NO-DEBE-ENTRAR');
