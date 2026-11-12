package tech.ludhara.cuenta360;

import static org.awaitility.Awaitility.await;
import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.function.IntFunction;
import java.util.stream.Collectors;

import jakarta.inject.Inject;

import org.apache.avro.specific.SpecificRecord;
import org.apache.kafka.clients.admin.Admin;
import org.apache.kafka.clients.admin.ConsumerGroupListing;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.ByteArrayDeserializer;
import org.apache.kafka.common.serialization.ByteArraySerializer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;
import org.eclipse.microprofile.config.ConfigProvider;
import org.jboss.logging.Logger;
import org.junit.jupiter.api.Test;

import io.confluent.kafka.serializers.KafkaAvroSerializer;
import io.quarkus.test.junit.QuarkusTest;
import tech.ludhara.cuenta360.eventos.ClienteActualizado;
import tech.ludhara.cuenta360.eventos.CuentaAbierta;
import tech.ludhara.cuenta360.eventos.CuentaCerrada;
import tech.ludhara.cuenta360.eventos.LimiteActualizado;
import tech.ludhara.cuenta360.eventos.MarcaTarjeta;
import tech.ludhara.cuenta360.eventos.MotivoBloqueo;
import tech.ludhara.cuenta360.eventos.MovimientoRegistrado;
import tech.ludhara.cuenta360.eventos.PagoServicioRealizado;
import tech.ludhara.cuenta360.eventos.TarjetaBloqueada;
import tech.ludhara.cuenta360.eventos.TarjetaEmitida;
import tech.ludhara.cuenta360.eventos.TipoCuenta;
import tech.ludhara.cuenta360.eventos.TipoMovimiento;
import tech.ludhara.cuenta360.eventos.TransferenciaEnviada;
import tech.ludhara.cuenta360.eventos.TransferenciaRecibida;

@QuarkusTest
class Cuenta360IT {

    private static final Logger LOG = Logger.getLogger(Cuenta360IT.class);

    private static final int EVENTOS_POR_TOPICO = 5_000;

    private static final Map<String, IntFunction<SpecificRecord>> EVENTOS = Map.of(
            "cuenta-abierta", i -> CuentaAbierta.newBuilder().setEventoId(id()).setCuentaId("c-" + i)
                    .setClienteId("cl-" + i).setTipoCuenta(TipoCuenta.AHORROS).setMoneda("PEN")
                    .setOcurridoEn(ahora()).build(),
            "cuenta-cerrada", i -> CuentaCerrada.newBuilder().setEventoId(id()).setCuentaId("c-" + i)
                    .setMotivo("cliente").setSaldoFinalCentavos(0).setOcurridoEn(ahora()).build(),
            "movimiento-registrado", i -> MovimientoRegistrado.newBuilder().setEventoId(id())
                    .setMovimientoId("m-" + i).setCuentaId("c-" + i).setTipo(TipoMovimiento.DEBITO)
                    .setMontoCentavos(1_500).setMoneda("PEN").setOcurridoEn(ahora()).build(),
            "transferencia-enviada", i -> TransferenciaEnviada.newBuilder().setEventoId(id())
                    .setTransferenciaId("t-" + i).setCuentaOrigenId("c-" + i).setCuentaDestino("x-" + i)
                    .setBancoDestino("BCP").setMontoCentavos(10_000).setMoneda("PEN").setOcurridoEn(ahora())
                    .build(),
            "transferencia-recibida", i -> TransferenciaRecibida.newBuilder().setEventoId(id())
                    .setTransferenciaId("t-" + i).setCuentaDestinoId("c-" + i).setCuentaOrigen("x-" + i)
                    .setBancoOrigen("BBVA").setMontoCentavos(10_000).setMoneda("PEN").setOcurridoEn(ahora())
                    .build(),
            "pago-servicio-realizado", i -> PagoServicioRealizado.newBuilder().setEventoId(id())
                    .setPagoId("p-" + i).setCuentaId("c-" + i).setEmpresa("Luz del Sur")
                    .setNumeroSuministro("s-" + i).setMontoCentavos(8_900).setOcurridoEn(ahora()).build(),
            "tarjeta-emitida", i -> TarjetaEmitida.newBuilder().setEventoId(id()).setTarjetaId("tj-" + i)
                    .setCuentaId("c-" + i).setMarca(MarcaTarjeta.VISA).setUltimosDigitos("4242")
                    .setOcurridoEn(ahora()).build(),
            "tarjeta-bloqueada", i -> TarjetaBloqueada.newBuilder().setEventoId(id()).setTarjetaId("tj-" + i)
                    .setMotivo(MotivoBloqueo.PERDIDA).setOcurridoEn(ahora()).build(),
            "cliente-actualizado", i -> ClienteActualizado.newBuilder().setEventoId(id()).setClienteId("cl-" + i)
                    .setEmail("cliente" + i + "@ludhara.tech").setOcurridoEn(ahora()).build(),
            "limite-actualizado", i -> LimiteActualizado.newBuilder().setEventoId(id()).setCuentaId("c-" + i)
                    .setLimiteDiarioCentavos(500_000).setLimiteAnteriorCentavos(300_000).setOcurridoEn(ahora())
                    .build());

    @Inject
    ProyeccionContadora proyeccion;

    @Test
    void consumeLosDiezTopicosYMandaElVenenoASuDlq() throws Exception {
        String bootstrap = config("kafka.bootstrap.servers");
        byte[] veneno = "no-es-avro".getBytes(StandardCharsets.UTF_8);

        long inicio = System.nanoTime();
        try (KafkaProducer<String, Object> productor = productorAvro(bootstrap)) {
            for (int i = 0; i < EVENTOS_POR_TOPICO; i++) {
                for (Map.Entry<String, IntFunction<SpecificRecord>> evento : EVENTOS.entrySet()) {
                    productor.send(new ProducerRecord<>(evento.getKey(), "k-" + i, evento.getValue().apply(i)));
                }
            }
        }
        try (KafkaProducer<String, byte[]> productor = productorBytes(bootstrap)) {
            productor.send(new ProducerRecord<>("movimiento-registrado", "veneno", veneno)).get();
        }

        long esperados = (long) EVENTOS_POR_TOPICO * EVENTOS.size();
        await().atMost(Duration.ofMinutes(2)).pollInterval(Duration.ofMillis(200))
                .until(() -> proyeccion.total() >= esperados);
        double segundos = (System.nanoTime() - inicio) / 1e9;
        LOG.infof("%d eventos de 10 tópicos consumidos en %.1f s: %.0f eventos/s", esperados, segundos,
                esperados / segundos);

        for (String topico : EVENTOS.keySet()) {
            assertEquals(EVENTOS_POR_TOPICO, proyeccion.aplicados(topico), topico);
        }

        try (Admin admin = Admin.create(Map.of("bootstrap.servers", bootstrap))) {
            Set<String> grupos = admin.listConsumerGroups().all().get().stream()
                    .map(ConsumerGroupListing::groupId)
                    .filter(g -> g.startsWith("cuenta-360."))
                    .collect(Collectors.toSet());
            assertEquals(EVENTOS.keySet().stream().map(t -> "cuenta-360." + t).collect(Collectors.toSet()), grupos);
        }

        ConsumerRecord<String, byte[]> enDlq = leerUno(bootstrap, "cuenta-360.movimiento-registrado.dlq");
        assertEquals("veneno", enDlq.key());
        assertArrayEquals(veneno, enDlq.value());
        assertNotNull(enDlq.headers().lastHeader("dead-letter-reason"));
        assertEquals("movimiento-registrado",
                new String(enDlq.headers().lastHeader("dead-letter-topic").value(), StandardCharsets.UTF_8));
    }

    private static KafkaProducer<String, Object> productorAvro(String bootstrap) {
        return new KafkaProducer<>(Map.of(
                ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap,
                ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName(),
                ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, KafkaAvroSerializer.class.getName(),
                ProducerConfig.LINGER_MS_CONFIG, 5,
                "schema.registry.url", config("mp.messaging.connector.smallrye-kafka.schema.registry.url")));
    }

    private static KafkaProducer<String, byte[]> productorBytes(String bootstrap) {
        return new KafkaProducer<>(Map.of(
                ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap,
                ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName(),
                ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, ByteArraySerializer.class.getName()));
    }

    private static ConsumerRecord<String, byte[]> leerUno(String bootstrap, String topico) {
        try (KafkaConsumer<String, byte[]> consumer = new KafkaConsumer<>(Map.of(
                ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap,
                ConsumerConfig.GROUP_ID_CONFIG, "verificador-dlq",
                ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest",
                ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName(),
                ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, ByteArrayDeserializer.class.getName()))) {
            consumer.subscribe(List.of(topico));
            long limite = System.currentTimeMillis() + 30_000;
            while (System.currentTimeMillis() < limite) {
                for (ConsumerRecord<String, byte[]> record : consumer.poll(Duration.ofMillis(500))) {
                    return record;
                }
            }
            throw new AssertionError("La DLQ " + topico + " está vacía");
        }
    }

    private static String config(String clave) {
        return ConfigProvider.getConfig().getValue(clave, String.class);
    }

    private static String id() {
        return UUID.randomUUID().toString();
    }

    private static Instant ahora() {
        return Instant.ofEpochMilli(System.currentTimeMillis());
    }
}
