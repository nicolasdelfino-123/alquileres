"""Automatic background sender; database locks coordinate PostgreSQL processes."""
import threading
import time
from flask import request


def init_mail_runtime(app):
    started = False
    lock = threading.Lock()

    def cleanup():
        from datetime import timedelta
        from sqlalchemy import delete, select
        from app.extensions import db
        from app.models.common import utcnow
        from app.models.mail_outbox_model import AuthRateBucket, MailOutbox
        from app.models.auth_token_model import AuthToken
        from app.models.communication_model import Communication
        cutoff = utcnow() - timedelta(days=7)
        db.session.execute(delete(AuthRateBucket).where(AuthRateBucket.expires_at < utcnow()))
        expired = select(AuthToken.id).where(AuthToken.expires_at < cutoff)
        db.session.execute(delete(MailOutbox).where(MailOutbox.token_id.in_(expired)))
        db.session.execute(delete(AuthToken).where(AuthToken.expires_at < cutoff))
        db.session.execute(delete(Communication).where(Communication.status != "pending", Communication.created_at < utcnow() - timedelta(days=400)))
        db.session.commit()

    def run():
        from app.extensions import db
        from app.services.mail_service import process_one
        from app.services.communication_service import process_one as process_notice
        last_cleanup = 0
        while True:
            try:
                with app.app_context():
                    if time.monotonic() - last_cleanup > 300:
                        cleanup()
                        last_cleanup = time.monotonic()
                    for _ in range(20):
                        auth_work = process_one()
                        notice_work = process_notice()
                        if not auth_work and not notice_work:
                            break
            except Exception as error:
                app.logger.warning("mail_background_error type=%s", type(error).__name__)
            time.sleep(2)

    @app.before_request
    def ensure_started():
        nonlocal started
        if app.testing or not request.endpoint or not app.config["MAIL_WORKER_AUTOSTART"] or started:
            return
        with lock:
            if not started:
                threading.Thread(target=run, daemon=True, name="pako-mail").start()
                started = True
