package tech.ludhara.cuenta360.proyeccion;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

import jakarta.enterprise.context.ApplicationScoped;

import org.apache.avro.specific.SpecificRecord;

import io.quarkus.arc.DefaultBean;

/**
 * Reemplazar por el adaptador de la base de datos real. Acotada en tamaño para que no agote el heap a 5 000 TPS, por
 * lo que la idempotencia solo vale para las entidades que siguen en memoria.
 */
@DefaultBean
@ApplicationScoped
public class ProyeccionEnMemoria implements ProyeccionCuenta360 {

    private static final int MAX_ENTIDADES = 100_000;

    private final Map<Clave, Instant> ultimoAplicado = new LinkedHashMap<>(16, 0.75f, true) {
        @Override
        protected boolean removeEldestEntry(Map.Entry<Clave, Instant> eldest) {
            return size() > MAX_ENTIDADES;
        }
    };

    @Override
    public synchronized boolean aplicar(String tipoEvento, String entidadId, Instant ocurridoEn,
            SpecificRecord evento) {
        Clave clave = new Clave(tipoEvento, entidadId);
        Instant vigente = ultimoAplicado.get(clave);
        if (vigente != null && !ocurridoEn.isAfter(vigente)) {
            return false;
        }
        ultimoAplicado.put(clave, ocurridoEn);
        return true;
    }

    private record Clave(String tipoEvento, String entidadId) {
    }
}
