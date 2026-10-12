# Libreto: Temporal Cloud on Azure — Private Link por namespace

Diagrama: [temporal-cloud-azure-private-link.drawio](temporal-cloud-azure-private-link.drawio)
Duración estimada: 8 a 10 minutos, más preguntas.
Fuente: Temporal Cloud on Azure Pre-Release Guide (actualizada el 6 de octubre de 2026).

Cada bloque indica **dónde señalar** en el diagrama y **qué decir**. Las frases entre comillas son sugeridas; se pueden decir con palabras propias.

---

## 1. Apertura (30 s)

**Señalar:** título y la línea naranja debajo.

"Este diagrama muestra cómo los workers del Banco se conectan a Temporal Cloud en Azure sin pasar por internet, usando Azure Private Link, y cómo se controla qué red puede llegar a cada namespace.

Un aviso antes de empezar: Temporal Cloud en Azure está en pre-release, solo por invitación. Sirve para desarrollo y evaluación, no tiene SLA y no se debe usar en producción. Temporal apunta a Public Preview en noviembre de 2026 y a GA en el primer trimestre de 2027. Hoy hay dos regiones: centralus y australiaeast."

---

## 2. La idea en una frase (30 s)

**Señalar:** recorrer con el dedo de izquierda a derecha: Workers → Private Endpoint → Private Link Service → Namespaces.

"La idea es simple: creamos un Private Endpoint en nuestra VNet, Temporal lo aprueba cuando registramos una Connectivity Rule, y luego adjuntamos esa regla a cada namespace que queremos proteger. A partir de ese momento, el namespace solo acepta tráfico que llegue por ese Private Endpoint."

---

## 3. Lado Azure: dónde viven los workers (1 min 30 s)

**Señalar:** recuadro azul "Azure — suscripción BCP", luego la VNet de aplicaciones (spoke).

"A la izquierda está nuestra suscripción de Azure. En la VNet de aplicaciones corren los workers de APOQ y NREM en AKS, con el SDK de Temporal en Java, autenticados con mTLS o API key. También están los clients que inician workflows y una VM o pod de prueba para validar la conexión."

**Señalar:** VNet del Private Endpoint (hub), caja del Private Endpoint.

"En la VNet hub, dentro de una subnet dedicada, está el Private Endpoint. Tiene una IP privada, en el ejemplo 10.1.2.3, y apunta por alias al Private Link Service de Temporal. Nace en estado Pending y pasa a Approved cuando Temporal lo aprueba.

El NSG debe permitir el puerto 7233 desde las VNets de los workers."

**Señalar:** caja Peering · VPN · ExpressRoute.

"Los workers no tienen que estar en la misma VNet del Private Endpoint. Pueden estar en otra VNet conectada por peering, VPN o ExpressRoute. Lo único obligatorio es que puedan enrutar hasta esa IP privada."

---

## 4. DNS privado: la pieza que más se olvida (1 min 30 s)

**Señalar:** recuadro "Private DNS zone" y la flecha punteada que baja desde la VNet de aplicaciones.

"Este es el punto que más falla en la práctica. Los workers se conectan a un hostname como `apoq.<account-id>.tmprl.cloud`. Si nadie lo cambia, ese nombre se resuelve con DNS público y el tráfico sale por internet, aunque el Private Endpoint exista.

Por eso creamos una Private DNS zone para `<account-id>.tmprl.cloud`, con un registro A por namespace que apunta a la IP del Private Endpoint. Y vinculamos esa zona a todas las VNets que tienen workers o clients, con registration desactivado."

**Señalar:** texto "Alternativa sin DNS privado".

"Existe una alternativa: apuntar el worker directo a la IP y configurar `tls_server_name` con el hostname del namespace. Funciona, pero no la recomendamos: obliga a cambiar la configuración de cada aplicación, y si recreamos el Private Endpoint hay que tocar todas. Con DNS privado basta cambiar un registro."

---

## 5. Lado Temporal Cloud: aprobación y reglas (1 min 30 s)

**Señalar:** recuadro "Temporal Cloud — región azure-centralus", caja Private Link Service y la flecha gruesa "Azure Private Link".

"A la derecha está Temporal Cloud. El tráfico viaja por el backbone de Azure, del Private Endpoint al Private Link Service de Temporal. Nunca toca internet."

**Señalar:** recuadro Connectivity Rules, caja CR-AZ, flecha "aprueba".

"¿Cómo se aprueba el Private Endpoint? Creando una Connectivity Rule privada en nuestra cuenta de Temporal, con el resource ID del Private Endpoint y la región. Al crearla, Temporal aprueba la conexión.

Hay un plazo duro: la regla debe crearse dentro de las 24 horas siguientes a la creación del Private Endpoint. Si no, el endpoint se rechaza y hay que crearlo de nuevo."

**Señalar:** caja CR-PUB.

"También existe una regla pública. Solo la usamos durante la transición, mientras haya workers que todavía salen por internet."

---

## 6. El control es por namespace (2 min)

**Señalar:** recuadro "Namespaces", de arriba hacia abajo.

"Este es el mensaje central: crear la regla no protege nada por sí solo. La protección se activa cuando la adjuntamos a un namespace, y se decide namespace por namespace. Los tres ejemplos muestran los tres comportamientos posibles."

**Señalar:** apoq (verde) y la flecha roja desde Internet.

"APOQ tiene solo la regla privada. Acepta tráfico únicamente desde ese Private Link. Si alguien intenta conectarse desde internet, aun con credenciales válidas, recibe 'Request unauthorized'. Es el estado objetivo."

**Señalar:** nrem (ámbar) y la flecha ámbar desde Internet.

"NREM tiene la regla privada y la pública. Acepta ambos caminos. Es el estado de migración: lo usamos mientras movemos los workers a Private Link, y al terminar quitamos la regla pública."

**Señalar:** dev (gris).

"Dev no tiene reglas. Es el comportamiento por defecto: no bloquea nada y atiende cualquier solicitud autenticada. Un namespace nuevo queda así hasta que le adjuntemos reglas."

**Señalar:** nota inferior del recuadro.

"Un detalle de diseño: la relación es de muchos a muchos. Un Private Endpoint sirve para todos los namespaces de la región, y un namespace puede aceptar varios Private Endpoints. No necesitamos un endpoint por aplicación."

---

## 7. Cómo se configura (1 min)

**Señalar:** franja "Administración" y luego el panel "Pasos de configuración".

"Abajo están las herramientas y los siete pasos. En resumen:

1. Crear el Private Endpoint con el alias de la región del namespace.
2. Verificar que quede en Pending y copiar su resource ID.
3. Crear la Connectivity Rule dentro de las 24 horas.
4. Obtener la IP privada del endpoint.
5. Crear la Private DNS zone, los registros A y los VNet links.
6. Adjuntar la regla a cada namespace.
7. Probar: desde la VNet responde; desde fuera falla con 'Request unauthorized'.

Los pasos de Azure se hacen con el portal o Azure CLI. Los de Temporal, con el CLI `temporal cloud`, la Cloud Ops API o Terraform."

---

## 8. Riesgos y advertencias (1 min)

**Señalar:** panel "Comportamiento de las reglas y advertencias".

"Tres advertencias para cerrar:

- **Corte de tráfico.** Si adjuntamos solo la regla privada a un namespace que tiene workers saliendo por internet, los cortamos en el acto. Por eso primero adjuntamos privada y pública, migramos y recién después quitamos la pública.
- **La API es declarativa.** `UpdateNamespace` reemplaza el spec completo. Si se omite un campo, se borra. Siempre hay que partir de la respuesta de `GetNamespace`.
- **Herramientas.** `tcld` no está soportado en Azure; usamos `temporal cloud` CLI, la Cloud Ops API o Terraform.

Y algo para confirmar con Temporal: la guía muestra dos alias distintos para centralus. Antes de crear el Private Endpoint hay que validar cuál es el vigente."

---

## 9. Cierre (30 s)

"En resumen: Private Endpoint en nuestra VNet, Connectivity Rule para que Temporal lo apruebe, DNS privado para que los workers lo usen sin cambiar código, y la regla adjunta a cada namespace para cerrar el acceso público. Y todo esto hoy es pre-release: lo podemos evaluar en desarrollo, pero no es una opción para APOQ y NREM en producción hasta que haya GA y SLA."

---

## Preguntas frecuentes

**¿Necesitamos un Private Endpoint por namespace?**
No. Un Private Endpoint da acceso a todos los namespaces de la región. Lo que es por namespace es el registro A en el DNS y la regla adjunta.

**¿El Private Endpoint puede estar en otra región?**
Sí, pero el alias debe ser de la región del namespace. Se recomienda que endpoint, namespace y workers estén en la misma región.

**¿Qué pasa si se borra la API key con la que se creó la regla?**
Nada. La key solo se usa al crear la regla; no queda asociada a ella.

**¿Cómo sé si un worker está usando Private Link o internet?**
Con `nslookup` desde el pod: si el hostname resuelve a la IP privada del endpoint, usa Private Link. La prueba definitiva es adjuntar solo la regla privada en un namespace de prueba y ver que el worker siga funcionando.

**¿El Private Endpoint se quedó en Pending, qué reviso?**
Que exista una regla con ese resource ID exacto, que el alias sea de la región correcta y que no hayan pasado más de 24 horas desde que se creó el endpoint.

**¿Hay alta disponibilidad multi-región?**
Todavía no en Azure. Cuando exista, se recomendará un Private Endpoint en cada región y una configuración de DNS distinta (sobre `azure-<region>.region.tmprl.cloud`).

**¿Esto cambia el plan de retiro ante insolvencia?**
No. Private Link resuelve la conectividad privada con Temporal Cloud; no reduce la dependencia del proveedor. El plan de retiro sigue aplicando igual.
