# Alquileres

Gestión inmobiliaria con Flask/PostgreSQL y React/Vite.

## Acceso

Administrador inicial local: usuario `pako`, correo `nicolasdelfino585@gmail.com`. La contraseña inicial se entregó en el chat y se almacena como hash; no se restablece al reiniciar.

El registro web pide usuario, correo y contraseña, sin código ni verificación previa. Las cuentas registradas son empleados: por ahora pueden consultar propiedades, sin modificar datos ni acceder a finanzas, propietarios o configuración. El administrador accede al sistema completo. Los permisos de empleados se aplican también en el backend.

La recuperación sigue disponible desde **Olvidé mi contraseña**; el envío real requiere un remitente configurado.

## Correo del sistema (administrador, una sola vez)

Con la aplicación abierta localmente:

1. Abrí http://localhost:5173/configurar-correo.
2. Configurá el Gmail desde el que el sistema enviará sus mensajes. Google requiere una contraseña de aplicación del remitente; el enlace para generarla está en la pantalla.
3. Guardá la configuración del remitente.
4. Tocá **Guardar y enviar prueba** y comprobá que el mail llegó, también en spam.

Las credenciales quedan cifradas y no se muestran al volver a abrir la pantalla. Los correos se procesan automáticamente; no hay que abrir una terminal adicional ni ejecutar un worker. Si cambiás el remitente, guardá su nueva credencial desde esta misma pantalla.

Para crear cuentas adicionales, usar **Crear una cuenta** en el login y elegir usuario, correo y contraseña. No se pide código.

En producción, la configuración de correo es accesible solo a administradores desde el menú. La configuración sin iniciar sesión está habilitada únicamente en desarrollo y desde el propio equipo, con controles de origen y host.

## Desarrollo

El backend se inicia con `python run.py` desde `backend`, con su entorno Python activo y dependencias de `requirements.txt`. El inicio local aplica las migraciones pendientes. PostgreSQL debe estar iniciado y `backend/.env` debe contener `DATABASE_URL` y `JWT_SECRET_KEY`.

El frontend se inicia con `npm run dev` desde `frontend` después de instalar sus dependencias. Consulta http://localhost:5000/api por defecto.

El detalle del despliegue futuro está en [PRODUCTION.md](PRODUCTION.md).

## Validación

Backend: `venv/bin/python -m unittest discover -s tests` desde `backend`. Frontend: `npm run build` desde `frontend`.

Las pruebas automáticas simulan SMTP y no envían correos reales. Las pruebas de concurrencia requieren una base PostgreSQL descartable `codex_rental_test*` indicada en `RENTAL_TEST_DATABASE_URL`.

## Módulos operativos

La definición de pantallas, campos obligatorios/opcionales y reglas está en [MODULOS_PAKO.md](MODULOS_PAKO.md). La navegación incluye propiedades, personas y garantes, contratos, cobros, liquidaciones, gastos, pendientes, resultados, ventas y consulta del Excel original.

Las nuevas tablas se aplican al iniciar el backend local con `run.py`. En producción, ejecutar la migración como paso de despliegue con backup previo. Respaldar también `backend/instance/documents`, `backend/instance/planillas` y la clave de cifrado; estos archivos privados no se guardan en Git.
