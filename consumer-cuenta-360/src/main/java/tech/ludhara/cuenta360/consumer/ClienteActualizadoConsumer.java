package tech.ludhara.cuenta360.consumer;

import jakarta.enterprise.context.ApplicationScoped;

import org.eclipse.microprofile.reactive.messaging.Incoming;

import io.smallrye.reactive.messaging.annotations.Blocking;
import tech.ludhara.cuenta360.eventos.ClienteActualizado;
import tech.ludhara.cuenta360.proyeccion.ProyeccionCuenta360;

@ApplicationScoped
public class ClienteActualizadoConsumer {

    private final ProyeccionCuenta360 proyeccion;

    ClienteActualizadoConsumer(ProyeccionCuenta360 proyeccion) {
        this.proyeccion = proyeccion;
    }

    @Incoming("cliente-actualizado")
    @Blocking(value = "cliente-actualizado-pool", ordered = false)
    public void consumir(ClienteActualizado evento) {
        proyeccion.aplicar("cliente-actualizado", evento.getClienteId(), evento.getOcurridoEn(), evento);
    }
}
