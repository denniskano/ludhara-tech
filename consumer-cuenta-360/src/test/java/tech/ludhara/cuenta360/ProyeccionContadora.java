package tech.ludhara.cuenta360;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.LongAdder;

import jakarta.enterprise.context.ApplicationScoped;

import org.apache.avro.specific.SpecificRecord;

import tech.ludhara.cuenta360.proyeccion.ProyeccionCuenta360;

@ApplicationScoped
public class ProyeccionContadora implements ProyeccionCuenta360 {

    private final Map<String, LongAdder> aplicados = new ConcurrentHashMap<>();

    @Override
    public boolean aplicar(String tipoEvento, String entidadId, Instant ocurridoEn, SpecificRecord evento) {
        aplicados.computeIfAbsent(tipoEvento, k -> new LongAdder()).increment();
        return true;
    }

    public long aplicados(String tipoEvento) {
        LongAdder contador = aplicados.get(tipoEvento);
        return contador == null ? 0 : contador.sum();
    }

    public long total() {
        return aplicados.values().stream().mapToLong(LongAdder::sum).sum();
    }
}
