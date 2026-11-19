-- =============================================================================
-- PoC RDV: eventos de prueba. Cada INSERT ... VALUES es un statement acotado:
-- escribe sus filas en el tópico y termina.
--
-- Totales esperados en RDV después de este archivo:
--   rdv-poc-cuenta-abierta            3
--   rdv-poc-movimiento-registrado     5  (incluye un reenvío del mismo evento)
--   rdv-poc-cliente-actualizado       3  (dos versiones del mismo cliente)
--   rdv-poc-pago-servicio-realizado   2
-- RDV guarda todo tal cual llega: el reenvío y las dos versiones aparecen como
-- filas distintas, con offsets distintos. Deduplicar es trabajo de la capa siguiente.
-- =============================================================================

INSERT INTO `rdv-poc-cuenta-abierta`
  (`cuenta_id`, `evento_id`, `cliente_id`, `tipo_cuenta`, `moneda`, `ocurrido_en`)
VALUES
  ('CTA-0001', 'evt-ca-0001', 'CLI-0001', 'AHORROS',    'PEN', CAST('2026-11-13 09:00:00.000' AS TIMESTAMP_LTZ(3))),
  ('CTA-0002', 'evt-ca-0002', 'CLI-0002', 'CORRIENTE',  'USD', CAST('2026-11-13 09:05:00.000' AS TIMESTAMP_LTZ(3))),
  ('CTA-0003', 'evt-ca-0003', 'CLI-0001', 'PLAZO_FIJO', 'PEN', CAST('2026-11-13 09:10:00.000' AS TIMESTAMP_LTZ(3)));

INSERT INTO `rdv-poc-movimiento-registrado`
  (`movimiento_id`, `evento_id`, `cuenta_id`, `tipo`, `monto`, `moneda`, `descripcion`, `ocurrido_en`)
VALUES
  ('MOV-0001', 'evt-mv-0001', 'CTA-0001', 'CREDITO', CAST(1500.00 AS DECIMAL(18, 2)), 'PEN', 'Depósito inicial',    CAST('2026-11-13 09:15:00.000' AS TIMESTAMP_LTZ(3))),
  ('MOV-0002', 'evt-mv-0002', 'CTA-0001', 'DEBITO',  CAST(  89.90 AS DECIMAL(18, 2)), 'PEN', CAST(NULL AS STRING), CAST('2026-11-13 09:20:00.000' AS TIMESTAMP_LTZ(3))),
  ('MOV-0003', 'evt-mv-0003', 'CTA-0002', 'CREDITO', CAST( 250.00 AS DECIMAL(18, 2)), 'USD', 'Transferencia',       CAST('2026-11-13 09:25:00.000' AS TIMESTAMP_LTZ(3))),
  ('MOV-0004', 'evt-mv-0004', 'CTA-0003', 'CREDITO', CAST(5000.00 AS DECIMAL(18, 2)), 'PEN', 'Apertura plazo fijo', CAST('2026-11-13 09:30:00.000' AS TIMESTAMP_LTZ(3))),
  -- Reenvío del productor: mismo evento_id que MOV-0002.
  ('MOV-0002', 'evt-mv-0002', 'CTA-0001', 'DEBITO',  CAST(  89.90 AS DECIMAL(18, 2)), 'PEN', CAST(NULL AS STRING), CAST('2026-11-13 09:20:00.000' AS TIMESTAMP_LTZ(3)));

INSERT INTO `rdv-poc-cliente-actualizado`
  (`cliente_id`, `evento_id`, `email`, `telefonos`, `direccion`, `ocurrido_en`)
VALUES
  ('CLI-0001', 'evt-cl-0001', 'ana@correo.pe', ARRAY['999111222'],
     ROW('Av. Larco 123', 'Miraflores', 'Lima'), CAST('2026-11-13 09:35:00.000' AS TIMESTAMP_LTZ(3))),
  ('CLI-0002', 'evt-cl-0002', CAST(NULL AS STRING), ARRAY['988777666', '014445555'],
     ROW('Jr. Cusco 456', 'Cercado', 'Arequipa'), CAST('2026-11-13 09:40:00.000' AS TIMESTAMP_LTZ(3))),
  -- Segunda versión del mismo cliente: cambia el correo y la dirección.
  ('CLI-0001', 'evt-cl-0003', 'ana.p@correo.pe', ARRAY['999111222'],
     ROW('Calle Las Begonias 789', 'San Isidro', 'Lima'), CAST('2026-11-13 09:45:00.000' AS TIMESTAMP_LTZ(3)));

INSERT INTO `rdv-poc-pago-servicio-realizado`
  (`pago_id`, `evento_id`, `cuenta_id`, `empresa`, `numero_suministro`, `monto`, `atributos`, `ocurrido_en`)
VALUES
  ('PAG-0001', 'evt-pg-0001', 'CTA-0001', 'Luz del Sur', 'SUM-778899', CAST(120.50 AS DECIMAL(18, 2)),
     MAP['canal', 'app', 'periodo', '2026-10'], CAST('2026-11-13 09:50:00.000' AS TIMESTAMP_LTZ(3))),
  ('PAG-0002', 'evt-pg-0002', 'CTA-0002', 'Sedapal', 'SUM-112233', CAST(45.00 AS DECIMAL(18, 2)),
     MAP['canal', 'web'], CAST('2026-11-13 09:55:00.000' AS TIMESTAMP_LTZ(3)));

-- Verificación del lado de Kafka, antes de mirar el lago.
SELECT `movimiento_id`, `evento_id`, `monto`, `$rowtime` FROM `rdv-poc-movimiento-registrado`;
