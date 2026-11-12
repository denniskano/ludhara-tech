package tech.ludhara.cuenta360.consumer;

import jakarta.enterprise.context.ApplicationScoped;

import org.eclipse.microprofile.reactive.messaging.Incoming;

import io.smallrye.reactive.messaging.annotations.Blocking;
import tech.ludhara.cuenta360.eventos.LimiteActualizado;
import tech.ludhara.cuenta360.proyeccion.ProyeccionCuenta360;

@ApplicationScoped
public class LimiteActualizadoConsumer {

    private final ProyeccionCuenta360 proyeccion;

    LimiteActualizadoConsumer(ProyeccionCuenta360 proyeccion) {
        this.proyeccion = proyeccion;
    }

    @Incoming("limite-actualizado")
    @Blocking(value = "limite-actualizado-pool", ordered = false)
    public void consumir(LimiteActualizado evento) {
        proyeccion.aplicar("limite-actualizado", evento.getCuentaId(), evento.getOcurridoEn(), evento);
    }
}
