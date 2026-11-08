import re
from pathlib import Path
from uuid import uuid4
from flask import Blueprint, current_app, request, send_file, jsonify
from app.extensions import db
from app.models import Document, RentCharge, RentPayment, OwnerSettlement, OwnerTransfer, Person
from app.services.management_service import APIError, get_record, serialize, ManagementService, validate

file_bp = Blueprint('files', __name__)
MAX_FILE = 10 * 1024 * 1024


def init_document_limits(app):
    @app.before_request
    def limits():
        if request.path in {'/api/files','/api/archive'} and request.method == 'POST':
            request.max_content_length = MAX_FILE + 65536


@file_bp.post('/files')
def upload():
    file = request.files.get('file')
    if not file or not file.filename:
        raise APIError('Seleccioná un PDF, JPG o PNG')
    head = file.stream.read(16)
    file.stream.seek(0)
    suffix = '.pdf' if head.startswith(b'%PDF-') else '.png' if head.startswith(b'\x89PNG\r\n\x1a\n') else '.jpg' if head.startswith(b'\xff\xd8\xff') else None
    if not suffix:
        raise APIError('El contenido debe ser un PDF, JPG o PNG válido')
    data = dict(request.form)
    allowed = {'property_id','contract_id','person_id','charge_id','payment_id','settlement_id','transfer_id','document_type','notes','period_year','period_month'}
    if set(data) - allowed:
        raise APIError('Metadatos de documento no admitidos')
    data = {key:value for key,value in data.items() if value.strip()}
    data.setdefault('document_type', 'Comprobante')
    directory = Path(current_app.instance_path) / 'documents'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    stored = uuid4().hex + suffix
    target = directory / stored
    try:
        with target.open('xb') as output:
            target.chmod(0o600)
            size = 0
            while chunk := file.stream.read(65536):
                size += len(chunk)
                if size > MAX_FILE:
                    raise APIError('El archivo supera 10 MB', 413)
                output.write(chunk)
        data.update(file_path=stored, original_filename=Path(file.filename.replace('\\','/')).name[:255])
        # Metadata and money operations remain separate: uploading never changes a payment.
        record = ManagementService.create('documents', data)
        return jsonify(serialize(record)), 201
    except Exception:
        target.unlink(missing_ok=True)
        raise


@file_bp.get('/files/<int:identifier>')
def download(identifier):
    record = get_record(Document, identifier)
    if not re.fullmatch(r'[a-f0-9]{32}\.(pdf|png|jpg)', record.file_path):
        raise APIError('Este documento tiene un enlace externo, no un archivo local', 404)
    path = Path(current_app.instance_path) / 'documents' / record.file_path
    if not path.is_file():
        raise APIError('Archivo no encontrado', 404)
    return send_file(path, as_attachment=True, download_name=record.original_filename)
