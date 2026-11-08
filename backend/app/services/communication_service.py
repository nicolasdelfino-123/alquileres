import json
import re
import smtplib
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from cryptography.fernet import InvalidToken
from flask import current_app
from sqlalchemy import select
from app.extensions import db
from app.models.communication_model import Communication
from app.models import RentalContract, Person
from app.models.common import utcnow
from app.services.management_service import APIError, get_record, transactional
from app.services.mail_service import cipher, deliver, validate_smtp


def public(record):
    return {'id':record.id,'contract_id':record.contract_id,'person_id':record.person_id,'purpose':record.purpose,
            'channel':record.channel,'status':record.status,'scheduled_at':record.scheduled_at.isoformat()+'Z',
            'sent_at':record.sent_at.isoformat()+'Z' if record.sent_at else None,'last_error':record.last_error}


@transactional
def schedule(identifier, data, creator):
    contract = get_record(RentalContract,identifier)
    allowed = set(contract.tenant_ids) | {link.person_id for link in contract.property.owners}
    person_id = data.get('person_id')
    if type(person_id) is not int or person_id not in allowed:
        raise APIError('El destinatario debe ser un inquilino o propietario de este contrato')
    person = get_record(Person,person_id)
    if not person.email or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',person.email):
        raise APIError('Cargá un correo válido en la ficha del destinatario')
    text = data.get('message')
    if not isinstance(text,str) or not text.strip() or len(text)>8000:
        raise APIError('El mensaje debe tener entre 1 y 8000 caracteres')
    try:
        scheduled=datetime.fromisoformat(data.get('scheduled_at','').replace('Z','+00:00'))
        if scheduled.tzinfo is None:
            raise ValueError()
        scheduled=scheduled.astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError,TypeError,AttributeError):
        raise APIError('Ingresá una fecha y hora de envío válidas') from None
    if scheduled<utcnow()-timedelta(minutes=1) or scheduled>utcnow()+timedelta(days=366):
        raise APIError('Programá el envío entre ahora y los próximos 366 días')
    from app.services.message_attachments import selected_files
    attachments=selected_files(contract,person_id,data.get('document_ids',[]))
    validate_smtp()
    payload=cipher().encrypt(json.dumps({'recipient':person.email,'message':text,'attachments':[{'id':item['id'],'sha256':item['sha256']} for item in attachments]}).encode()).decode()
    record=Communication(contract_id=contract.id,person_id=person.id,created_by_id=creator.id,
                         channel='email',purpose='notice',payload=payload,scheduled_at=scheduled,available_at=scheduled)
    db.session.add(record)
    db.session.flush()
    return public(record)


def process_one():
    now=utcnow()
    job=db.session.scalar(select(Communication).where(Communication.status=='pending',Communication.available_at<=now)
                          .order_by(Communication.available_at,Communication.id).with_for_update(skip_locked=True).limit(1))
    if not job:
        db.session.rollback()
        return False
    if now>job.scheduled_at+timedelta(days=1):
        job.status,job.payload,job.last_error='failed',None,'DeliveryExpired'
        db.session.commit()
        return True
    job.attempts+=1
    try:
        payload=json.loads(cipher().decrypt(job.payload.encode()))
        config=validate_smtp()
        message=EmailMessage()
        message['From']=config['SMTP_FROM']
        message['To']=payload['recipient']
        message['Subject']='Aviso de alquiler · Bricks Bienes Raíces'
        message['Message-ID']=f"<pako-notice-{job.id}@{config['SMTP_FROM'].split('@')[-1]}>"
        message.set_content(payload['message'])
        from app.services.message_attachments import selected_files
        attachments=payload.get('attachments',[])
        files=selected_files(job.contract,job.person_id,[item['id'] for item in attachments])
        for item,expected in zip(files,attachments):
            if item['sha256']!=expected['sha256']:
                raise APIError('El comprobante cambió después de programar el envío')
            message.add_attachment(item['data'],maintype=item['maintype'],subtype=item['subtype'],filename=item['filename'])
        deliver(message)
    except (OSError,smtplib.SMTPException,InvalidToken,APIError,ValueError,KeyError) as error:
        job.last_error=type(error).__name__
        current_app.logger.warning('communication_failed id=%s error=%s',job.id,job.last_error)
        if job.attempts>=6 or isinstance(error,(InvalidToken,smtplib.SMTPRecipientsRefused)):
            job.status,job.payload='failed',None
        else:
            job.available_at=now+timedelta(seconds=min(60*2**(job.attempts-1),900))
    else:
        job.status,job.payload,job.sent_at,job.last_error='sent',None,now,None
    db.session.commit()
    return True
