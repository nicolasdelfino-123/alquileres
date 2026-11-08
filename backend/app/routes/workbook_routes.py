from pathlib import Path
from uuid import uuid4
from flask import Blueprint, current_app, request, jsonify
from app.services.management_service import APIError
from app.services.workbook_service import Workbook

workbook_bp=Blueprint('workbook',__name__)


def source_path():
    return Path(current_app.instance_path)/'planillas'/'pako.xlsx'


@workbook_bp.get('/archive')
def metadata():
    path=source_path()
    if not path.is_file():return {'available':False,'sheets':[]}
    book=Workbook(path)
    try:return {'available':True,'sheets':[s['name'] for s in book.sheets], 'filename':'Planilla original de Bricks Bienes Raíces'}
    finally:book.close()


@workbook_bp.get('/archive/sheet')
def sheet():
    path=source_path()
    if not path.is_file():raise APIError('Todavía no se cargó una planilla',404)
    book=Workbook(path)
    try:return jsonify(book.read(request.args.get('name','JUNIO')))
    finally:book.close()


@workbook_bp.post('/archive')
def upload():
    file=request.files.get('file')
    if not file or not (file.filename or '').lower().endswith('.xlsx'):
        raise APIError('Seleccioná un archivo XLSX')
    path=source_path();path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=path.parent/(uuid4().hex+'.xlsx')
    try:
        with temporary.open('xb') as output:
            temporary.chmod(0o600)
            size=0
            while chunk:=file.stream.read(65536):
                size+=len(chunk)
                if size>10*1024*1024:raise APIError('La planilla supera 10 MB',413)
                output.write(chunk)
        book=Workbook(temporary)
        try:count=len(book.sheets)
        finally:book.close()
        temporary.replace(path)
        return {'message':f'Planilla cargada para consulta: {count} hojas. No se crearon cobros ni contratos.'}
    finally:
        temporary.unlink(missing_ok=True)
