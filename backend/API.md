# API de gestión de alquileres

Base: `/api`. Fechas `YYYY-MM-DD`, fechas de auditoría UTC, dinero y porcentajes
como cadenas decimales en las respuestas (incluido `price` de propiedades).
Los números JSON se leen directamente como Decimal. Se rechazan negativos,
valores no finitos, importes con más de dos decimales y campos desconocidos.
JWT obligatorio mediante Authorization: Bearer; Los endpoints de login, registro y recuperación son públicos; el registro exige el código del equipo.

## Recursos y rutas

| Recurso | Rutas |
|---|---|
| Personas | `/persons`, `/persons/{id}` |
| Propiedades | `/properties`, `/properties/{id}` (URLs existentes conservadas) |
| Copropietarios | `/property-owners`, `/property-owners/{id}` |
| Contratos | `/contracts`, `/contracts/{id}` |
| Ajustes | `/adjustments`, `/adjustments/{id}` |
| Gastos | `/expenses`, `/expenses/{id}` |
| Documentos | `/documents`, `/documents/{id}` |
| Recordatorios | `/reminders`, `/reminders/{id}` |

Colecciones: GET/POST. Elementos: GET/PUT/PATCH/DELETE, excepto propiedades que
mantienen GET/PUT/DELETE. PUT y PATCH aceptan modificaciones parciales.
No se puede eliminar un registro con referencias dependientes.
Filtros GET: los campos de referencia que existan en el recurso (`property_id`,
`contract_id`, `person_id`, `tenant_id`, `owner_id`, `charge_id`, `settlement_id`),
`period_year`, `period_month`, `currency`, `status`, según corresponda.

Estados de contrato: `active`, `expired`, `terminated`, `cancelled`.
Recordatorios: `pending`, `completed`, `cancelled`; `completed_at` es automático.
Gastos: `responsible_party` = `owner`, `tenant`, `agency`.
Documentos: CRUD de metadatos y ruta del archivo; no carga, descarga ni eliminación
física de archivos. Usuarios creados por CLI o desde la web con código de registro y verificación por correo.

## Operaciones financieras

`/charges`, `/payments`, `/settlements`, `/transfers`: GET/POST de colección y
GET de elemento. Importes confirmados inmutables, sin PUT ni DELETE.
Anulación: POST `/{recurso}/{id}/cancel` con `{"reason":"motivo"}`.
Se preservan registro, fecha de creación, fecha y motivo de anulación.

Mensualidad: `contract_id`, `period_year`, `period_month`, `due_date`, y opcionalmente
`rent_amount`, `other_charges`, `discounts`, `notes`.
La combinación contrato/período es única, incluso tras anularla.
`total_amount` lo calcula el servidor. Si se omite `rent_amount`, se toma el último
ajuste vigente al primer día del período o el `current_rent` del contrato.
Se guardan moneda y porcentaje de administración como fotografía histórica.
Editar un contrato o ajuste no modifica mensualidades existentes.
Los ajustes no cambian automáticamente `current_rent` ni crean mensualidades.

Pago: `contract_id`, `charge_id`, `payment_date`, `amount`, `payment_method`,
`reference`, `idempotency_key`, `notes` opcional.
Transferencia: `settlement_id`, `transfer_date`, `amount`, `payment_method`,
`reference`, `idempotency_key`, `notes` opcional.
Referencias únicas en cada tipo de operación; para efectivo se usa un número de
recibo único. Clave de idempotencia obligatoria: repetir la misma operación devuelve
el registro existente, cambiar sus datos con la misma clave responde 409.
No se reutilizan referencias ni claves de registros anulados.
No se permiten sobrepagos ni transferencias superiores al saldo. No hay anticipos
sin mensualidad ni compensación automática entre mensualidades.

Liquidación: `property_id`, `owner_id`, `period_year`, `period_month`,
`settlement_date`, `idempotency_key`, y opcionalmente `gross_amount`,
`administration_fee`, `deductions`, `currency` (ARS por defecto), `notes`.
Solo se puede liquidar lo efectivamente cobrado, hasta la fecha de liquidación,
por las mensualidades de esa propiedad/período/moneda y según el porcentaje del
propietario. La suma de porcentajes de propietarios nunca puede superar 100.
El bruto consume disponibilidad, incluidos honorarios y deducciones.
Sin bruto explícito se usa toda la disponibilidad de ese propietario.
Sin honorario explícito se aplica proporcionalmente el honorario histórico de
las mensualidades cobradas. `net_amount = gross_amount - administration_fee - deductions`.
Los gastos no se deducen automáticamente: una deducción se indica explícitamente
al liquidar, evitando descontar un mismo gasto sin instrucción.
Liquidaciones adicionales solo pueden utilizar cobros todavía no liquidados.
No se mezclan monedas. Las transferencias parciales mantienen `partial` hasta
completar el neto; solo entonces se informa `transferred`.

Cada escritura se confirma en una transacción. Las operaciones financieras y
cambios de copropiedad bloquean la fila de la propiedad; además se bloquean
contratos, mensualidades o liquidaciones afectadas. PostgreSQL serializa así las
solicitudes concurrentes sobre los mismos fondos. La API valida claves foráneas;
la base también valida restricciones y la correspondencia pago/contrato/mensualidad.
Para corregir un pago liquidado: anular primero transferencias, luego liquidaciones
del período y finalmente el pago. Una mensualidad con pagos activos no se anula.

## Consultas

- GET `/charges/{id}/balance`: mensualidad, `paid_amount`, `outstanding_balance`, estado.
- GET `/persons/{id}/debts`: saldos totales y vencidos por moneda, mensualidades pendientes.
- GET `/settlements/{id}/balance`: liquidación, `transferred_amount`, saldo, estado.
- GET `/persons/{id}/settlements`: liquidaciones y saldos de transferencia por moneda.
- GET `/dashboard?year=2026&month=10&currency=ARS`: cobros por fecha de pago,
  pendientes por período de mensualidad, honorarios por período de liquidación,
  gastos por fecha y saldo de transferencias por período. Excluye anulaciones.
- GET `/contracts/upcoming-expirations?days=30`: contratos activos que vencen en el horizonte.
- GET `/contracts/upcoming-adjustments?days=30`: próximos ajustes programados o
  calculados por frecuencia desde el inicio/último ajuste. No aplica índices externos.

Mensualidades con cobros incompletos: `partial`; sin cobros y vencidas: `overdue`;
saldadas: `paid`. El saldo y estado se calculan desde pagos activos, por lo que el
vencimiento se refleja en consultas sin un proceso programado.
Errores: 400 validación, 404 referencia inexistente, 409 conflicto financiero o duplicado.

## Verificación y despliegue posterior

Desde `backend`: `venv/bin/python -m unittest discover -s tests -v`.
Las pruebas usan exclusivamente datos sintéticos y SQLite en memoria por defecto.
No se ejecutan migraciones ni se toca la base configurada por `DATABASE_URL`.
Para PostgreSQL se admite `RENTAL_TEST_DATABASE_URL` apuntando exclusivamente a
una base descartable cuyo nombre comience con `codex_rental_test`; las pruebas
crean y eliminan las tablas de esa base. Incluyen prueba concurrente en PostgreSQL.

Antes de utilizar los nuevos endpoints con la base real, generar, revisar y aplicar
migraciones, configurar `JWT_SECRET_KEY` (al menos 32 bytes) y crear usuarios internos.

JWT: POST `/auth/login` con `username`/`password`; GET `/auth/me` consulta el usuario.
Roles `admin`/`operator`; DELETE y anulaciones financieras requieren `admin`.
Crear usuarios con `flask --app run.py create-user --username USUARIO --email EMAIL --role admin`
(contraseña solicitada por consola). Tokens válidos durante 30 minutos.
Contratos aceptan `tenant_ids`, conservando `tenant_id` como principal; GET/POST
`/contracts/{id}/tenants` y `/contract-tenants` administran asociaciones antes de generar mensualidades.
Las deudas del contrato son compartidas por todos sus inquilinos, sin duplicarlas en el dashboard.
`/sales`: CRUD con `property_id`, `buyer_id`, `seller_id`, `price`, `currency`, `sale_date`,
`commission` (importe monetario) y `status` (`pending`, `completed`, `cancelled`).

## Gestión operativa ampliada

- `GET /workspace?year=2026&month=11&currency=ARS`: ficha de trabajo mensual con contratos, personas, propietarios, cobros, liquidaciones, transferencias, documentos y totales. Requiere administrador en el esquema actual.
- `POST /charges/generate`: `year`, `month`, `currency`, `contract_ids` opcional. Genera mensualidades faltantes sin duplicar períodos.
- `POST /charges/{id}/correct`: importes, vencimiento, notas y `reason`. Solo antes de movimientos, con revisión auditada.
- `POST /contracts/{id}/apply-adjustment`: `effective_date`, `mode` (`IPC`, `ICL`, `percentage`, `amount`) y valores correspondientes. Conserva el cálculo y no reescribe mensualidades existentes.
- `GET /contracts/{id}/adjustments`: historial.
- `POST /settlements/generate-owner`: `owner_id`, período, moneda e `idempotency_key` de hasta 50 caracteres. Liquida cobros disponibles sin deducciones adicionales.
- `POST /transfers/{id}/confirm`: registra la confirmación administrativa de recepción.
- `POST /files`: multipart con archivo y metadatos de vínculo; PDF/JPG/PNG hasta 10 MB. `GET /files/{id}` descarga autenticada.
- `GET /reports/business?year=2026&currency=ARS`: resumen anual por fecha de cobro y gastos del negocio.
- `GET|POST /contracts/{id}/messages`: consultar o programar un aviso por correo. POST: `person_id`, `message`, `scheduled_at` ISO con zona horaria. Solo personas del contrato o propietarios del inmueble. `POST /messages/{id}/cancel` cancela un pendiente.
- `GET /archive`: hojas del Excel privado. `GET /archive/sheet?name=JUNIO`: consulta. `POST /archive`: reemplazar copia de consulta mediante XLSX multipart, sin importar operaciones contables.

Propiedades aceptan `ownerships` (`person_id`, `ownership_percentage`) y datos opcionales de ubicación, características y servicios. Contratos aceptan `guarantor_ids`, día de pago, depósito, firma, próximo aumento y cuenta de cobro. Los campos bancarios de cobro del contrato son independientes de los del propietario.
