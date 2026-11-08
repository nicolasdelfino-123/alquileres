"""Carga manual y única de demostración. Nunca se ejecuta al iniciar la app.

Uso desde backend: venv/bin/python scripts/seed_demo_once.py
Inmuebles/importes de JUNIO; personas vinculadas, fechas y movimientos de prueba.
"""
import os
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import dotenv_values
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from app import create_app
from app.extensions import db
from app.models import Property
from app.models.common import business_today
from app.services.management_service import ManagementService, FinanceService, money
from app.services.workbook_service import Workbook, NS

TAG = 'DEMO-PAKO-V1'
NOTE = 'DEMO: origen JUNIO del Excel; fechas, inquilinos, titularidad y movimientos ficticios para probar el sistema.'


def source_rows():
    book = Workbook(ROOT / 'instance/planillas/pako.xlsx')
    try:
        sheet = next(s for s in book.sheets if s['name'] == 'JUNIO')
        raw = ET.fromstring(book.zip.read(sheet['path']))
        groups = {}
        owner = ''
        for row in raw.findall('x:sheetData/x:row', NS):
            for cell in row.findall('x:c', NS):
                if cell.attrib['r'].startswith('A'):
                    value = book.value(cell)
                    if '▶' in value:
                        owner = value.split('▶', 1)[1].strip().title()
            groups[int(row.attrib['r'])] = owner
        result = []
        for row in book.read('JUNIO')['rows']:
            values = row['values']
            if not re.fullmatch(r'\d+', values.get('A', '').strip()):
                continue
            owner = values.get('B') or groups[row['row']]
            owner = owner.split(' / Bricks')[0]
            if 'Bricks' in owner:
                owner = 'Bricks Inmobiliaria'
            try:
                amount = money(Decimal(values.get('G') or '0'))
            except InvalidOperation:
                amount = Decimal('0')
            fee_text = values.get('I', '')
            # Participación en propiedades propias no es honorario de administración.
            fee = Decimal(fee_text.rstrip('%')) if '%' in fee_text and 'Bricks' not in values.get('B', '') else Decimal('0')
            result.append((values, owner, amount, fee))
        return result
    finally:
        book.close()


def backup(parsed):
    directory = ROOT / 'instance/backups'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = directory / ('before-demo-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.dump')
    env = dict(os.environ, PGDATABASE=parsed.database, PGHOST=parsed.host or 'localhost', PGPORT=str(parsed.port or 5432))
    if parsed.username:
        env['PGUSER'] = parsed.username
    if parsed.password:
        env['PGPASSWORD'] = parsed.password
    completed = subprocess.run(['/usr/lib/postgresql/18/bin/pg_dump', '--format=custom', '--file', str(target)], env=env, capture_output=True)
    if completed.returncode:
        raise RuntimeError('No se pudo respaldar la base; no se cargaron datos.')


def main():
    refreshed = ROOT / 'instance/seeds/portfolio-scenario-v2.json'
    if refreshed.exists() and json.loads(refreshed.read_text()).get('complete'):
        print('Seed ya cargado y actualizado. No se duplicó ningún registro.')
        return
    parsed = make_url(dotenv_values(ROOT / '.env')['DATABASE_URL'])
    if parsed.get_backend_name() != 'postgresql' or parsed.host not in {'localhost', '127.0.0.1', None}:
        raise RuntimeError('Este seed solo admite PostgreSQL local.')
    rows = source_rows()
    if len(rows) != 26 or any(not owner for _, owner, _, _ in rows):
        raise RuntimeError('La planilla cambió; revisar antes de cargar.')
    app = create_app({'MAIL_WORKER_AUTOSTART': False})
    with app.app_context():
        # Lock de sesión: evita dos ejecuciones simultáneas incluso durante backup.
        connection = db.engine.connect()
        try:
            connection.execute(text('SELECT pg_advisory_lock(871624103)'))
            if db.session.scalar(select(Property.id).where(Property.internal_code.like(TAG + '%')).limit(1)):
                print('Seed ya cargado. No se duplicó ni modificó ningún registro.')
                return
            backup(parsed)
            today = business_today()
            start = date(today.year, 1, 1)
            end = date(today.year + 2, 1, 1)
            create = ManagementService.create.__wrapped__
            counts = Counter()
            owners = {}
            states = Counter()
            for index, (values, owner_name, amount, fee) in enumerate(rows, 1):
                if owner_name not in owners:
                    parts = owner_name.split(' ', 1)
                    owners[owner_name] = create('persons', {'first_name': parts[0], 'last_name': parts[1] if len(parts) > 1 else 'Demo', 'notes': NOTE + ' Nombre de propietario tomado del Excel; contacto de demostración.'})
                    counts['propietarios'] += 1
                owner = owners[owner_name]
                prop = create('properties', {'address': values['C'], 'title': (values['C'] + ' ' + values.get('D', '') + ' · DEMO')[:120], 'unit': values.get('D') or None, 'internal_code': f'{TAG}-{index:03}', 'price': str(amount), 'status': 'rented' if amount else 'available', 'notes': NOTE, 'ownerships': [{'person_id': owner.id, 'ownership_percentage': '100'}]})
                counts['propiedades'] += 1
                if not amount:
                    continue
                tenant = create('persons', {'first_name': ['Ana', 'Martín', 'Lucía', 'Diego', 'Sofía', 'Pablo'][index % 6], 'last_name': f'Demo {index:02}', 'email': f'inquilino.demo{index:02}@example.invalid', 'notes': NOTE + ' Inquilino completamente ficticio.'})
                counts['inquilinos'] += 1
                contract = create('contracts', {'property_id': prop.id, 'tenant_id': tenant.id, 'start_date': start.isoformat(), 'end_date': end.isoformat(), 'initial_rent': str(amount), 'current_rent': str(amount), 'administration_percentage': str(fee), 'payment_day': 5 if index % 2 else 15, 'payment_method': 'transferencia', 'adjustment_frequency_months': 3, 'adjustment_index': 'Pactado (DEMO)', 'next_adjustment_date': date(today.year, 12, 1).isoformat(), 'notes': NOTE})
                counts['contratos'] += 1
                charge = create('charges', {'contract_id': contract.id, 'period_year': today.year, 'period_month': today.month, 'due_date': date(today.year, today.month, contract.payment_day).isoformat(), 'rent_amount': str(amount), 'notes': NOTE})
                counts['mensualidades'] += 1
                if index % 4 in (0, 1, 2):
                    paid = money(amount / 2) if index % 4 == 2 else amount
                    create('payments', {'contract_id': contract.id, 'charge_id': charge.id, 'payment_date': today.isoformat(), 'amount': str(paid), 'payment_method': 'transferencia', 'reference': f'{TAG}-COBRO-{index}', 'idempotency_key': f'{TAG}-COBRO-{index}', 'notes': NOTE})
                    counts['cobros'] += 1
                    if index % 4 in (0, 1):
                        settlement = create('settlements', {'property_id': prop.id, 'owner_id': owner.id, 'period_year': today.year, 'period_month': today.month, 'settlement_date': today.isoformat(), 'idempotency_key': f'{TAG}-LIQ-{index}', 'notes': NOTE})
                        counts['liquidaciones'] += 1
                        if settlement.net_amount > 0 and index % 4 == 1:
                            create('transfers', {'settlement_id': settlement.id, 'transfer_date': today.isoformat(), 'amount': str(settlement.net_amount), 'payment_method': 'transferencia', 'reference': f'{TAG}-TRANSF-{index}', 'idempotency_key': f'{TAG}-TRANSF-{index}', 'notes': NOTE})
                            counts['transferencias'] += 1
                states[charge.calculated_status] += 1
                if index <= 4:
                    create('reminders', {'property_id': prop.id, 'contract_id': contract.id, 'title': f'DEMO · Seguimiento del alquiler {index}', 'description': NOTE, 'due_date': today.isoformat(), 'priority': 'urgent' if index == 1 else 'normal', 'category': 'seguimiento', 'next_action': 'Revisar el caso de prueba.'})
                    counts['alertas'] += 1
            create('expenses', {'expense_date': today.isoformat(), 'category': 'Oficina (DEMO)', 'description': 'Gasto ficticio de oficina para mostrar resultados', 'amount': '35000', 'responsible_party': 'agency', 'notes': NOTE})
            counts['gastos'] += 1
            db.session.commit()
            print('Seed de prueba cargado: ' + ', '.join(f'{value} {key}' for key, value in counts.items()))
            print(f'Período: {today.year}-{today.month:02}. Estados: {dict(states)}. Backup privado guardado.')
        except Exception:
            db.session.rollback()
            raise
        finally:
            connection.execute(text('SELECT pg_advisory_unlock(871624103)'))
            connection.close()


if __name__ == '__main__':
    previous_mask = os.umask(0o077)
    try:
        main()
    finally:
        os.umask(previous_mask)
