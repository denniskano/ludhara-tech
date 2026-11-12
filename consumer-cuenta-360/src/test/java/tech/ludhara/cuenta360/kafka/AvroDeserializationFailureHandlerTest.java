package tech.ludhara.cuenta360.kafka;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.net.SocketTimeoutException;
import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;

import org.apache.avro.AvroTypeException;
import org.apache.kafka.common.errors.SerializationException;
import org.apache.kafka.common.header.Headers;
import org.apache.kafka.common.header.internals.RecordHeaders;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import io.confluent.kafka.schemaregistry.client.rest.exceptions.RestClientException;
import io.smallrye.mutiny.Uni;
import io.smallrye.reactive.messaging.kafka.DeserializationFailureHandler;

class AvroDeserializationFailureHandlerTest {

    private static final byte[] BYTES = { 0, 0, 0, 0, 7, 1, 2 };

    private AvroDeserializationFailureHandler handler;

    @BeforeEach
    void setUp() {
        handler = new AvroDeserializationFailureHandler();
        handler.backoffInicial = Duration.ofMillis(10);
        handler.backoffMaximo = Duration.ofMillis(20);
        handler.duracionMaxima = Duration.ofMillis(300);
    }

    @Test
    void mensajeIlegibleVaALaDlqConSusBytes() {
        Headers headers = new RecordHeaders();

        Object resultado = deserializar(fallaCon(new AvroTypeException("Found string, expecting long")), headers);

        assertNull(resultado);
        assertNotNull(headers.lastHeader(DeserializationFailureHandler.DESERIALIZATION_FAILURE_DLQ));
        assertArrayEquals(BYTES,
                headers.lastHeader(DeserializationFailureHandler.DESERIALIZATION_FAILURE_VALUE_DATA).value());
    }

    @Test
    void idDeEsquemaInexistenteEsVeneno() {
        Headers headers = new RecordHeaders();

        Object resultado = deserializar(fallaCon(new RestClientException("Schema not found", 404, 40403)), headers);

        assertNull(resultado);
        assertNotNull(headers.lastHeader(DeserializationFailureHandler.DESERIALIZATION_FAILURE_DLQ));
    }

    @Test
    void caidaBreveDeSchemaRegistrySeReintentaYNoTocaLaDlq() {
        Headers headers = new RecordHeaders();
        AtomicInteger intentos = new AtomicInteger();
        Uni<Object> deserializacion = Uni.createFrom().item(() -> {
            if (intentos.incrementAndGet() < 3) {
                throw new SerializationException("Error retrieving Avro schema", new SocketTimeoutException());
            }
            return "evento";
        });

        Object resultado = handler.decorateDeserialization(deserializacion, "pagos", false,
                "KafkaAvroDeserializer", BYTES, headers);

        assertEquals("evento", resultado);
        assertEquals(3, intentos.get());
        assertNull(headers.lastHeader(DeserializationFailureHandler.DESERIALIZATION_FAILURE_DLQ));
    }

    @Test
    void caidaLargaDeSchemaRegistryFallaElChannelSinMandarALaDlq() {
        Headers headers = new RecordHeaders();
        Uni<Object> deserializacion = fallaCon(new RestClientException("Service unavailable", 503, 50301));

        assertThrows(RuntimeException.class, () -> handler.decorateDeserialization(deserializacion, "pagos", false,
                "KafkaAvroDeserializer", BYTES, headers));
        assertNull(headers.lastHeader(DeserializationFailureHandler.DESERIALIZATION_FAILURE_DLQ));
    }

    @Test
    void credencialInvalidaDeSchemaRegistryNoEsVeneno() {
        assertEquals(true, FallasDeserializacion.esDeInfraestructura(
                new SerializationException(new RestClientException("Unauthorized", 401, 401))));
    }

    private Object deserializar(Uni<Object> deserializacion, Headers headers) {
        return handler.decorateDeserialization(deserializacion, "pagos", false, "KafkaAvroDeserializer", BYTES,
                headers);
    }

    private static Uni<Object> fallaCon(Throwable causa) {
        return Uni.createFrom().item(() -> {
            throw new SerializationException("Error deserializing Avro message", causa);
        });
    }
}
