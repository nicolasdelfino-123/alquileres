# Despliegue futuro en DonWeb Cloud Server / VPS

Este archivo documenta la configuración que falta definir cuando se conozcan el dominio y el servidor. El código no equivale a un despliegue validado: hay que probar el envío real y la operación en el VPS antes de entregar al cliente.

## Funcionamiento para el cliente

El usuario recupera su contraseña desde el login indicando únicamente su correo. El sistema envía un enlace para crear una nueva contraseña. La contraseña de aplicación de Gmail pertenece al remitente del sistema y se configura una sola vez por el administrador; no se solicita a los usuarios que recuperan acceso.

## Variables del servidor

- `APP_ENV=production` y `FLASK_DEBUG=0`.
- `DATABASE_URL`: PostgreSQL con usuario de privilegios mínimos y acceso restringido. No exponer el puerto de la base a Internet.
- `JWT_SECRET_KEY`: secreto aleatorio de al menos 32 bytes, diferente de la clave de correo.
- `MAIL_ENCRYPTION_KEY`: clave Fernet persistente, privada y respaldada. En local se genera automáticamente en `backend/instance/mail.key`; si se trasladan las credenciales de la base local, conservar esa misma clave. Perderla impide descifrar las credenciales y correos pendientes. En producción no se genera automáticamente.
- `FRONTEND_URL=https://DOMINIO_REAL`: origen público del frontend, sin rutas, parámetros ni credenciales.
- `TRUSTED_HOSTS=DOMINIO_REAL`: hosts aceptados por Flask, sin esquema ni puerto.
- `PROXY_HOPS=1` únicamente con un proxy confiable delante de Gunicorn y sin acceso público directo al backend. Si hay más proxies, revisar la topología antes de cambiar el valor.
- `WEB_CONCURRENCY=2` como punto inicial; ajustar con mediciones y el presupuesto de conexiones PostgreSQL. La cola automática usa una conexión adicional por proceso cuando está activa.

La aplicación rechaza al arrancar en producción el uso de SQLite, HTTP público, secretos faltantes, debug/testing activos y límites de autenticación desactivados.

## Configurar Gmail desde la aplicación

Un administrador ingresa a **Configurar correo** y guarda el Gmail del sistema y su contraseña de aplicación. La conexión usa `smtp.gmail.com:587`, STARTTLS y certificados verificados. La credencial se cifra en la base con `MAIL_ENCRYPTION_KEY` y nunca se devuelve al navegador. Guardar los secretos de despliegue fuera del repositorio.

Google exige verificación en dos pasos para emitir contraseñas de aplicación y puede restringirlas según la cuenta. Ver [ayuda de Google](https://support.google.com/accounts/answer/185833). Si la cuenta no permite esa modalidad, hay que integrar OAuth o usar otro servicio SMTP; no desactivar TLS ni usar la contraseña habitual de Google.

Gmail aplica cuotas de envío y puede suspender temporalmente el envío al alcanzarlas. Para una cuenta personal, consultar los [límites oficiales](https://support.google.com/mail/answer/22839). El código desacopla el proveedor y permite pasar a un SMTP transaccional configurando `SMTP_*` en el entorno y retirando la configuración Gmail guardada, mediante una migración controlada. Este cambio de proveedor aún no tiene interfaz.

## Servir la aplicación

Usar Gunicorn con `backend/gunicorn.conf.py` y el entrypoint `run:app`. No usar el servidor de desarrollo de Flask en producción. El backend escucha solo en `127.0.0.1:8000`.

Servir el build de React con Nginx y certificado HTTPS válido. Proxy de `/api/` y `/health/` hacia Gunicorn, preservando `Host` y sobrescribiendo los encabezados forwarded en el proxy confiable. El frontend debe compilarse con `VITE_API_URL=/api` para usar el mismo origen. Configurar fallback a `index.html` para las rutas React, especialmente `/cuenta`.

Configurar en Nginx `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, HSTS cuando HTTPS esté confirmado, y una CSP adaptada al build (`default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`). Desactivar cache de `index.html` y de respuestas API; los assets con hash pueden cachearse. No registrar query strings ni cuerpos de peticiones.

Configurar inicio/reinicio automático del servicio con systemd o el gestor del VPS. No iniciar hilos antes del fork de Gunicorn; `preload_app` está desactivado. El envío se inicia automáticamente por proceso al recibir solicitudes y PostgreSQL coordina el trabajo. Un crash puede provocar la repetición del mismo correo; el enlace sigue siendo de un solo uso. No se promete entrega exactamente una vez.

Antes de servir la versión nueva, crear un backup y ejecutar las migraciones como paso de despliegue. No ejecutar migraciones concurrentes desde los workers de producción.

## Validaciones previas a la entrega

1. Backup cifrado de PostgreSQL y de la clave de cifrado; restauración comprobada en otro entorno.
2. Crear o trasladar una cuenta administradora de forma controlada; en producción no existe bootstrap público. La cuenta inicial puede crearse desde la pantalla de configuración local antes de trasladar la base.
3. Probar un correo real desde la pantalla de configuración y el flujo completo de recuperación, incluso enlaces vencidos y ya utilizados.
4. Comprobar TLS, acceso HTTPS y que `/cuenta` abre desde el enlace de un correo en otro dispositivo.
5. Monitorizar `/health/live`, `/health/ready`, errores de entrega, cuotas de Gmail y crecimiento de la cola. El comando de operación `flask --app run.py mail-status` muestra contadores sin destinatarios ni tokens; conectarlo al monitoreo del servidor. Alertar si hay fallos definitivos o correos pendientes durante más de unos minutos. Los fallos no generan alertas externas por sí solos.
6. Ejecutar pruebas PostgreSQL y revisar dependencias Python/Node antes del despliegue. Hacer una prueba de carga con el volumen esperado; no se ha certificado capacidad ni SLA.
7. Acordar el alcance: actualmente todos los usuarios habilitados pertenecen a una misma inmobiliaria y comparten sus datos. No habilitar varias empresas independientes sin implementar y probar aislamiento por empresa.

## Controles implementados

Cola de correo persistente cifrada con reintentos exponenciales y límite de intentos; credenciales cifradas; verificación de certificados TLS; límites de intentos compartidos en PostgreSQL; enlaces aleatorios de un solo uso y vencimiento; tokens de recuperación hasheados; revocación de sesiones al cambiar la contraseña; CORS por origen; límite de tamaño de petición; cabeceras de seguridad y validación de hosts en producción. Los tokens de los nuevos enlaces viajan en el fragmento de la URL y el frontend los quita de la barra de direcciones al leerlos.

La limpieza automática elimina contadores vencidos y registros de correo/tokens expirados hace más de siete días. Los payloads cifrados se borran al entregar, cancelar o agotar los intentos. Estos controles no sustituyen una revisión integral de permisos, backups, infraestructura y seguridad del sistema antes de manejar datos reales.
