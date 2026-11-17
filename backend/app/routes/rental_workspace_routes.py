from flask import Blueprint, jsonify, request
from app.services.rental_workspace_service import RentalWorkspaceService as Service
from app.services.management_service import serialize, get_record
from app.controllers.management_controller import json_body
from app.models import RentalContract

workspace_bp = Blueprint('rental_workspace', __name__)

@workspace_bp.get('/workspace')
def workspace():
    return jsonify(Service.workspace(request.args))

@workspace_bp.post('/charges/generate')
def generate():
    return jsonify(Service.generate(json_body()))

@workspace_bp.post('/contracts/<int:identifier>/apply-adjustment')
def adjust(identifier):
    return jsonify(Service.adjust(identifier, json_body()))

@workspace_bp.get('/contracts/<int:identifier>/adjustments')
def adjustments(identifier):
    contract = get_record(RentalContract, identifier)
    return jsonify([serialize(v) for v in sorted(contract.adjustments, key=lambda v:v.effective_date)])

@workspace_bp.post('/transfers/<int:identifier>/confirm')
def confirm(identifier):
    return jsonify(Service.confirm_transfer(identifier))

@workspace_bp.get('/reports/business')
def business():
    return jsonify(Service.business(request.args))

@workspace_bp.route('/contracts/<int:identifier>/messages', methods=['GET','POST'])
def messages(identifier):
    from flask import g
    from sqlalchemy import select
    from app.extensions import db
    from app.models.communication_model import Communication
    from app.services.communication_service import public, schedule
    get_record(RentalContract, identifier)
    if request.method == 'POST':
        return jsonify(schedule(identifier,json_body(),g.current_user)), 201
    rows = db.session.scalars(select(Communication).where(Communication.contract_id==identifier).order_by(Communication.id.desc()).limit(100))
    return jsonify([public(row) for row in rows])

@workspace_bp.post('/messages/<int:identifier>/cancel')
def cancel_message(identifier):
    from app.models.communication_model import Communication
    from app.services.management_service import APIError
    from app.extensions import db
    record=get_record(Communication,identifier,lock=True)
    if record.status!='pending':
        raise APIError('Solo se pueden cancelar mensajes pendientes',409)
    record.status,record.payload='cancelled',None
    db.session.commit()
    from app.services.communication_service import public
    return jsonify(public(record))

@workspace_bp.post('/settlements/generate-owner')
def settle_owner():
    return jsonify(Service.settle_owner(json_body()))

@workspace_bp.post('/charges/<int:identifier>/correct')
def correct_charge(identifier):
    from flask import g
    return jsonify(Service.correct_charge(identifier,json_body(),g.current_user.id))

@workspace_bp.post('/contracts/<int:identifier>/service-controls')
def service_controls(identifier):
    from app.services.utility_service import generate_controls
    return jsonify(generate_controls(identifier, json_body()))

@workspace_bp.post('/contracts/<int:identifier>/adjustment-preview')
def adjustment_preview(identifier):
    from app.services.official_index_service import preview
    return jsonify(preview(identifier, json_body()))

@workspace_bp.post('/contracts/<int:identifier>/manual-adjustment-preview')
def manual_adjustment_preview(identifier):
    from app.services.official_index_service import manual_preview
    return jsonify(manual_preview(identifier, json_body()))

@workspace_bp.get('/contracts/<int:identifier>/adjustment-settings')
def adjustment_settings(identifier):
    from datetime import date
    from app.services.management_service import APIError
    from app.services.report_service import add_months
    contract = get_record(RentalContract, identifier)
    try:
        effective = date.fromisoformat(request.args.get('effective_date', ''))
    except (TypeError, ValueError):
        raise APIError('Ingresá la fecha real de aplicación del aumento') from None
    previous = max((a.effective_date for a in contract.adjustments if a.effective_date < effective), default=contract.start_date)
    return jsonify({'initial_date': previous.isoformat(), 'ipc_from': previous.strftime('%Y-%m'),
                    'ipc_to': add_months(effective.replace(day=1), -1).strftime('%Y-%m')})

@workspace_bp.get('/contracts/<int:identifier>/rent-calculation')
def rent_calculation(identifier):
    from app.services.rental_schedule_service import calculate_rent
    from app.services.report_service import period_arguments
    year, month, _ = period_arguments(request.args)
    contract = get_record(RentalContract, identifier)
    return jsonify(calculate_rent(contract, year, month))

@workspace_bp.route('/contracts/<int:identifier>/fees', methods=['GET', 'POST'])
def contract_fees(identifier):
    from app.services import contract_fee_service as fees
    if request.method == 'GET':
        return jsonify(fees.listing(identifier))
    return jsonify(fees.create(identifier, json_body())), 201

@workspace_bp.post('/contract-fees/<int:identifier>/payments')
def fee_payment(identifier):
    from app.services.contract_fee_service import pay
    return jsonify(pay(identifier, json_body()))

@workspace_bp.post('/contract-fees/<int:identifier>/cancel')
def cancel_fee(identifier):
    from app.services.contract_fee_service import cancel
    return jsonify(cancel(identifier, json_body()))

@workspace_bp.post('/contract-fee-payments/<int:identifier>/cancel')
def cancel_fee_payment(identifier):
    from app.services.contract_fee_service import cancel
    return jsonify(cancel(identifier, json_body(), payment=True))
