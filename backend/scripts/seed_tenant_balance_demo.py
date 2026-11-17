"""Ejemplo local explícito para supervisar la ficha de deuda; no corre al iniciar."""
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from app import create_app
from app.extensions import db
from app.models import Person
from app.models.common import business_today
from app.services.management_service import ManagementService

TAG = 'DEMO-SALDO-ARS-USD-V1'
NOTE = f'{TAG} · Datos ficticios para revisar la ficha del inquilino.'


def main():
    app = create_app({'MAIL_WORKER_AUTOSTART': False})
    parsed = make_url(app.config['SQLALCHEMY_DATABASE_URI'])
    if app.config['PRODUCTION'] or parsed.get_backend_name() != 'postgresql' or parsed.host not in {'localhost', '127.0.0.1'}:
        raise RuntimeError('Este ejemplo solo se permite en desarrollo con PostgreSQL local.')
    with app.app_context():
        db.session.execute(text('SELECT pg_advisory_xact_lock(871624105)'))
        existing = db.session.scalar(select(Person).where(Person.notes == NOTE))
        if existing:
            print(f'Ejemplo existente, sin duplicados: persona {existing.id}')
            return
        folder = ROOT / 'instance/backups'
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        backup = folder / f'before-balance-demo-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.dump'
        env = dict(os.environ, PGHOST=parsed.host, PGPORT=str(parsed.port or 5432), PGDATABASE=parsed.database)
        if parsed.username:
            env['PGUSER'] = parsed.username
        if parsed.password:
            env['PGPASSWORD'] = parsed.password
        result = subprocess.run(['/usr/lib/postgresql/18/bin/pg_dump', '-Fc', '-f', str(backup)], env=env, capture_output=True)
        if result.returncode:
            backup.unlink(missing_ok=True)
            raise RuntimeError('No se pudo respaldar; no se crearon registros.')
        create = ManagementService.create.__wrapped__
        person = create('persons', {'first_name': 'Demo Saldo', 'last_name': 'Pesos y Dólares', 'notes': NOTE})
        today = business_today()
        due = today - timedelta(days=7)
        for currency, rent, paid in [('ARS', '350000.00', '100000.00'), ('USD', '600.00', '150.00')]:
            prop = create('properties', {'address': f'Propiedad de prueba {currency}', 'title': f'DEMO saldo {currency}',
                'internal_code': f'{TAG}-{currency}', 'price': '0', 'operation_type': 'alquiler', 'status': 'rented', 'notes': NOTE})
            contract = create('contracts', {'property_id': prop.id, 'tenant_id': person.id,
                'start_date': date(due.year, 1, 1).isoformat(), 'end_date': date(today.year + 1, 12, 31).isoformat(),
                'currency': currency, 'initial_rent': rent, 'current_rent': rent, 'administration_percentage': '0', 'notes': NOTE})
            charge = create('charges', {'contract_id': contract.id, 'period_year': due.year, 'period_month': due.month,
                'due_date': due.isoformat(), 'rent_amount': rent, 'notes': NOTE})
            create('payments', {'contract_id': contract.id, 'charge_id': charge.id, 'payment_date': due.isoformat(),
                'amount': paid, 'payment_method': 'transfer', 'reference': f'{TAG}-{currency}',
                'idempotency_key': f'{TAG}-{currency}', 'notes': NOTE})
        db.session.commit()
        print(f'Creado: Demo Saldo Pesos y Dólares · persona {person.id}')
        print('Pendiente: ARS 250000.00 y USD 450.00. Dos cuotas vencidas con pagos parciales.')
        print('Respaldo previo guardado en instance/backups. Sin mensajes ni correos programados.')


if __name__ == '__main__':
    os.umask(0o077)
    main()
