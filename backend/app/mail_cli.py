import json
import time
import click
from datetime import timedelta
from sqlalchemy import select, func, delete
from app.extensions import db
from app.models.common import utcnow
from app.models.auth_token_model import AuthToken
from app.models.mail_outbox_model import MailOutbox, AuthRateBucket


def init_mail_cli(app):
    @app.cli.command("mail-worker")
    @click.option("--once", is_flag=True, help="Process up to --batch items and exit.")
    @click.option("--batch", default=20, type=click.IntRange(1, 1000))
    @click.option("--poll-seconds", default=2, type=click.IntRange(1, 60))
    def worker(once, batch, poll_seconds):
        """Deliver queued mail. Concurrent workers require PostgreSQL."""
        from app.services.mail_service import process_one, validate_smtp, cipher
        validate_smtp()
        cipher()
        while True:
            count = 0
            for _ in range(batch):
                try:
                    if not process_one():
                        break
                except Exception as error:
                    db.session.rollback()
                    app.logger.error("mail_worker_error type=%s", type(error).__name__)
                    if once:
                        raise click.ClickException("No se pudo procesar la cola") from None
                    break
                count += 1
            db.session.remove()
            if once:
                click.echo(f"Correos procesados: {count}")
                return
            if count < batch:
                time.sleep(poll_seconds)

    @app.cli.command("mail-status")
    def status():
        """Queue counters without email addresses or tokens."""
        counts = dict(db.session.execute(select(MailOutbox.status, func.count()).group_by(MailOutbox.status)).all())
        oldest = db.session.scalar(select(func.min(MailOutbox.created_at)).where(MailOutbox.status == "pending"))
        click.echo(json.dumps({"counts": counts, "oldest_pending": oldest.isoformat() if oldest else None}))

    @app.cli.command("auth-cleanup")
    def cleanup():
        """Purge expired rate buckets and auth mail/token records older than seven days."""
        now = utcnow()
        cutoff = now - timedelta(days=7)
        db.session.execute(delete(AuthRateBucket).where(AuthRateBucket.expires_at < now))
        expired = select(AuthToken.id).where(AuthToken.expires_at < cutoff)
        db.session.execute(delete(MailOutbox).where(MailOutbox.token_id.in_(expired)))
        db.session.execute(delete(AuthToken).where(AuthToken.expires_at < cutoff))
        db.session.commit()
        click.echo("Limpieza completada")
