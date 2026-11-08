# Pako — módulos y datos de trabajo

Definición basada en las capturas del sistema de referencia y en el archivo `2026_2030_FINAL2.xlsx` de Pako. Se conserva la identidad visual actual: blanco, tinta y verde. Los modales organizan la información; los campos opcionales no impiden guardar un registro básico.

## Organización

| Pantalla | Uso | Detalle y acciones |
|---|---|---|
| Propiedades | Cartera de inmuebles | Ficha en modal, propietarios, porcentajes, servicios y edición |
| Propietarios | Personas titulares y datos para transferir | Contacto, banco, participaciones y contratos relacionados |
| Inquilinos y garantes | Una ficha por persona | Contactos, datos laborales, contratos como inquilino y garantías |
| Contratos | Condiciones de cada alquiler | Modal con ficha, mensualidades, movimientos, documentos, aumentos y mensajes |
| Alquileres y cobros | Planilla operativa mensual | Generar mensualidades, registrar cobros parciales o completos, recibos, mensajes y filtros |
| Liquidaciones | Dinero a rendir al propietario | Honorarios, deducciones, neto, liquidación individual o masiva, transferencias y confirmación de recepción |
| Gastos | Gastos del negocio y de inmuebles | Concepto, fecha, responsable, importe y observaciones |
| Alertas y pendientes | Deudas y tareas del Excel | Fecha, monto conocido o a confirmar, responsable, prioridad, seguimiento y próxima acción |
| Resultados | Resumen anual | Honorarios de terceros, ingresos propios, gastos, resultado y margen mensual |
| Compraventas | Operaciones y comisiones | Precio, vendedor/agente, comisiones distribuidas, fuente del cliente y operación compartida |
| Planillas originales | Consulta del histórico real | Hojas del Excel, búsqueda, paginado, ficha por fila y enlaces externos presentes en el archivo |

El histórico de Excel y los movimientos nuevos están separados. Consultar una fila original no crea ni modifica un cobro. Los valores originales son los resultados guardados en el XLSX; no se ejecutan ni recalculan fórmulas. Los resultados nuevos se calculan únicamente con los registros operativos de la base.

## Propiedades

**Obligatorio:** dirección. Si no se completa un nombre, se genera a partir de dirección y unidad. El precio de referencia puede quedar sin definir; el alquiler del contrato se registra aparte.

**Opcionales:** tipo, piso, unidad/departamento, localidad, provincia, barrio, código postal, carpeta/código interno, matrícula, ambientes, dormitorios, baños, superficies, estado general, precio de referencia, participación propia de la inmobiliaria y observaciones.

**Propietarios:** una o varias personas y su participación. No puede superar 100% entre todos. Se pueden crear contactos desde el mismo modal. Una propiedad sin titulares vinculados puede guardarse, pero no liquidarse a un propietario todavía.

**Servicios e impuestos:** identificadores o referencias de luz/EPEC, agua, gas, municipal y Rentas/DGR, dentro de una sección desplegable opcional. Cargar una cuenta no afirma que un servicio esté pagado.

## Personas, inquilinos y garantes

**Obligatorio:** nombre y apellido. **Opcionales:** DNI, CUIT/CUIL, teléfono con código internacional, email, domicilio, ocupación, empleador, teléfono laboral, banco, titular, alias, CBU y observaciones.

Una persona se carga una vez y puede participar en distintos contratos. El garante se vincula al contrato; no es simplemente una nota perdida. Un inquilino no puede ser garante de ese mismo contrato. Los datos de contacto y bancarios se consultan desde su ficha.

## Contratos

**Obligatorios:** propiedad, al menos un inquilino, inquilino principal, fechas de inicio y fin, alquiler inicial y vigente, moneda y día de pago. El día de pago se propone como 10 y se puede cambiar.

**Opcionales:** garantes, medio de pago, honorarios de administración, índice de ajuste, frecuencia en meses, próximo aumento, porcentaje pactado, depósito, fecha de firma, cuenta de cobro y notas. Se pueden crear inquilinos y garantes desde el formulario sin perder lo completado.

No se permiten contratos activos con fechas superpuestas para una misma propiedad. Después de generar mensualidades se conservan la identidad del contrato, sus fechas, moneda, inquilinos y garantías; los cambios de contacto siguen disponibles en la ficha de la persona.

La **cuenta para cobrar al inquilino** y la **cuenta para transferir al propietario** son datos distintos. Los mensajes al inquilino usan únicamente el alias/CBU de cobro del contrato, nunca asumen que la cuenta bancaria del propietario sea la receptora del alquiler.

## Cobros y mensualidades

Filtros por período, moneda, estado, propietario y búsqueda por dirección o persona. Orden por dirección, importe o vencimiento; vista de lista o tarjetas. Exportación CSV del listado.

Generar una mensualidad registra su período, vencimiento, alquiler y porcentaje de honorarios. Generarla otra vez no crea un duplicado. Los meses sin generar se muestran como tales y no se suman a deuda.

La generación individual permite agregar cargos, descuentos y detalle. Si se deja vacío el alquiler, se calcula desde el historial del contrato. Antes de tener cobros o liquidaciones se puede corregir una mensualidad indicando el motivo; se conserva una revisión con el antes, después y usuario. Luego de movimientos se protege el historial.

**Cobro:** fecha, importe y medio de pago. Referencia y observaciones son opcionales; si falta referencia, se genera una única. Se aceptan pagos parciales y se impide cobrar más que el saldo. El estado se calcula con los movimientos, no con una marca manual de «pagado».

## Honorarios, liquidaciones y transferencias

Los honorarios se toman del porcentaje guardado en cada mensualidad. Se calculan proporcionalmente sobre el alquiler cobrado, excluyendo reintegros y cargos adicionales ajenos al alquiler. Si existe un descuento que reduce el total por debajo del alquiler, se respeta esa base reducida.

La liquidación considera lo realmente cobrado y aún disponible, la participación del propietario, honorarios y deducciones. La liquidación individual permite ingresar gastos a descontar. Los gastos registrados por separado no se deducen otra vez automáticamente. La liquidación masiva del propietario omite inmuebles sin cobros disponibles y no incorpora deducciones; para eso se usa la individual.

**Transferencia:** fecha, importe y medio, con referencia opcional. Se muestra su comprobante y se puede marcar la confirmación de recepción por el propietario. Registrar una transferencia en Pako no opera una cuenta bancaria.

Neto liquidado, transferido y pendiente son cantidades distintas. No se permite transferir más que el saldo ni liquidar más que los cobros disponibles. Las anulaciones requieren motivo y respetan dependencias; no borran movimientos ni revierten operaciones bancarias.

## Recibos, documentos y comprobantes

Los recibos de inquilino se generan a partir de un pago registrado: persona, inmueble, período, fecha, importe, medio y referencia. En pagos parciales, el recibo refleja ese pago, no el alquiler total.

Las liquidaciones individuales y consolidadas por propietario muestran importes brutos, honorarios, gastos, neto y estado de transferencia. Hay vista previa y opción **Imprimir / guardar PDF** mediante el navegador; no se agrega un archivo PDF automáticamente a la base al imprimir.

Se pueden adjuntar PDF, JPG o PNG de hasta 10 MB, o guardar enlaces HTTPS a Drive, Canva u otros comprobantes. Los archivos se guardan fuera de la carpeta pública, con nombre aleatorio y descarga autenticada. Un documento no modifica por sí mismo los importes del movimiento. La clasificación elegida permite distinguir contrato, recibo, liquidación, gasto o transferencia.

## Aumentos: IPC, ICL y pactados

- **IPC:** Índice de Precios al Consumidor, publicado por [INDEC](https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-31). Se cargan las variaciones de cada mes y se multiplican los factores: `alquiler × (1 + mes1/100) × (1 + mes2/100) …`.
- **ICL:** Índice para Contratos de Locación, publicado por [BCRA](https://www.bcra.gob.ar/tasas-de-interes/). Se cargan los valores correspondientes al inicio y fin del período: `alquiler × ICL final / ICL inicial`.
- **Porcentaje pactado:** aplica el porcentaje confirmado por las partes.
- **Importe acordado:** permite registrar directamente el nuevo alquiler.

La app guarda fecha de aplicación, base anterior, importe nuevo, porcentaje, método, cálculo, fuente y notas. Se aplica al primer día de un mes dentro del contrato y no reescribe mensualidades ya generadas. No se descargan índices oficiales automáticamente en esta versión. El administrador debe verificar fechas y valores; el sistema no elige una cláusula contractual por su cuenta.

## Alertas, deudas y seguimiento

Se muestran vencimientos y próximos aumentos de los contratos, además de tareas manuales. Cada tarea puede tener propiedad, contrato, persona responsable, categoría, prioridad, estado de gestión, monto si se conoce y próxima acción. Un importe «a confirmar» no se convierte en cero ni en deuda contable.

Las tareas recurrentes identifican un seguimiento repetitivo; no generan cobros o tareas nuevas automáticamente por el solo hecho de marcarse recurrentes.

## Mensajes

Cuatro plantillas: recordatorio de pago, próximo aumento, vencimiento del contrato y consulta al propietario. Se completan con datos del contrato y se pueden revisar antes de enviar.

- **WhatsApp:** abre la conversación con el mensaje preparado. El usuario confirma el envío en WhatsApp. No hay automatización de WhatsApp Cloud conectada ni envío de PDFs por WhatsApp desde esta versión.
- **Correo:** permite enviar ahora o programar fecha y hora. El remitente Gmail/SMTP debe estar configurado. Se usa una cola persistente y cifrada con reintentos y estado consultable en la ficha; los pendientes se pueden cancelar. La aceptación por SMTP no garantiza que el mensaje haya llegado a la bandeja principal.

Programar un aviso es una acción explícita del usuario. No se envían mensajes a todos los contactos solo por abrir una pantalla. Los recordatorios periódicos completamente desatendidos y la integración con WhatsApp Business requieren una siguiente configuración y desarrollo.

## Resultados y ventas

Los resultados usan la fecha real del cobro y la fecha del gasto. Separan honorarios sobre la porción administrada de terceros e ingresos por la participación propia registrada en cada inmueble. Solo restan los gastos a cargo de la inmobiliaria. No mezclan monedas ni consideran ingreso propio todo lo cobrado para propietarios.

En ventas se puede registrar una operación por su descripción aunque no se tenga cargado el inmueble, comprador o titular vendedor. Se distinguen agente/vendedor, precio de cierre, comisión total, comisión personal, comisión de la inmobiliaria, fuente del cliente, compartido con y observaciones. Las comisiones distribuidas no pueden superar el total. Son acuerdos de la operación, no ingresos cobrados automáticamente dentro del resultado de alquileres.

## Acceso y alcance actual

El administrador usa los módulos completos. Se conserva la restricción actual del empleado a consulta de propiedades; ampliar permisos por persona requiere definir expresamente qué acciones y datos se le habilitan. No hay un editor granular de permisos implementado en esta entrega.

El sistema actual corresponde a una sola inmobiliaria y una base compartida. No se afirma aislamiento entre empresas independientes ni sincronización con bancos, portales inmobiliarios o sistemas fiscales.

## Uso inicial

1. Consultar el histórico en **Planillas originales**. Se incluyó una copia privada del Excel encontrado; el original no se modificó.
2. Cargar o revisar propietarios y sus datos bancarios.
3. Cargar propiedades y confirmar sus participaciones.
4. Cargar inquilinos y garantes; crear los contratos con las fechas reales.
5. Generar las mensualidades del período, registrar cobros y adjuntar sus comprobantes.
6. Liquidar, registrar la transferencia y confirmar recepción.

No se transformaron automáticamente filas históricas en operaciones contables: las capturas y la planilla no contienen todos los inquilinos, fechas exactas y referencias necesarias para hacerlo sin supuestos.
