package tech.ludhara.cuenta360.consumer;

import jakarta.enterprise.context.ApplicationScoped;

import org.eclipse.microprofile.reactive.messaging.Incoming;

import io.smallrye.reactive.messaging.annotations.Blocking;
import tech.ludhara.cuenta360.eventos.CuentaAbierta;
import tech.ludhara.cuenta360.proyeccion.ProyeccionCuenta360;

@ApplicationScoped
public class CuentaAbiertaConsumer {

    private final ProyeccionCuenta360 proyeccion;

    CuentaAbiertaConsumer(ProyeccionCuenta360 proyeccion) {
        this.proyeccion = proyeccion;
    }

    @Incoming("cuenta-abierta")
    @Blocking(value = "cuenta-abierta-pool", ordered = false)
    public void consumir(CuentaAbierta evento) {
        proyeccion.aplicar("cuenta-abierta", evento.getCuentaId(), evento.getOcurridoEn(), evento);
    }
}
