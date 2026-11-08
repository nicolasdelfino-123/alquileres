"""Read only explicitly selected private documents belonging to this contract."""
import hashlib
import re
from pathlib import Path
from flask import current_app
from app.models import Document
from app.services.management_service import APIError, get_record

MAX_TOTAL=20*1024*1024

def selected_files(contract,person_id,identifiers):
    if not isinstance(identifiers,list) or len(identifiers)>5 or any(type(value)is not int for value in identifiers) or len(set(identifiers))!=len(identifiers):
        raise APIError('Seleccioná hasta cinco comprobantes distintos')
    files=[];size=0
    for identifier in identifiers:
        document=get_record(Document,identifier)
        linked=document.contract_id==contract.id or document.contract_id is None and document.property_id==contract.property_id
        if not linked or document.person_id not in {None,person_id}:
            raise APIError('El comprobante no corresponde a este contrato y destinatario')
        if not re.fullmatch(r'[a-f0-9]{32}\.(pdf|png|jpg)',document.file_path):
            raise APIError('Para adjuntar, subí el archivo PDF o imagen; los enlaces externos no son adjuntos')
        path=Path(current_app.instance_path)/'documents'/document.file_path
        if not path.is_file():raise APIError('No se encontró uno de los comprobantes')
        size+=path.stat().st_size
        if size>MAX_TOTAL:raise APIError('Los comprobantes seleccionados superan 20 MB')
        content=path.read_bytes()
        files.append({'id':document.id,'sha256':hashlib.sha256(content).hexdigest(),'filename':Path(document.original_filename.replace('\\','/')).name.replace('\r','').replace('\n','') or 'comprobante.pdf','data':content,'subtype':{'pdf':'pdf','png':'png','jpg':'jpeg'}[path.suffix[1:]],'maintype':'application' if path.suffix=='.pdf' else 'image'})
    return files
