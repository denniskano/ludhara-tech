package tech.ludhara.cuenta360.consumer;

import jakarta.enterprise.context.ApplicationScoped;

import org.eclipse.microprofile.reactive.messaging.Incoming;

import io.smallrye.reactive.messaging.annotations.Blocking;
import tech.ludhara.cuenta360.eventos.CuentaCerrada;
import tech.ludhara.cuenta360.proyeccion.ProyeccionCuenta360;

@ApplicationScoped
public class CuentaCerradaConsumer {

    private final ProyeccionCuenta360 proyeccion;

    CuentaCerradaConsumer(ProyeccionCuenta360 proyeccion) {
        this.proyeccion = proyeccion;
    }

    @Incoming("cuenta-cerrada")
    @Blocking(value = "cuenta-cerrada-pool", ordered = false)
    public void consumir(CuentaCerrada evento) {
        proyeccion.aplicar("cuenta-cerrada", evento.getCuentaId(), evento.getOcurridoEn(), evento);
    }
}
