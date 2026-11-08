import json
import smtplib
import ssl
import unittest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from cryptography.fernet import Fernet
from sqlalchemy import select

from app import create_app
from app.extensions import db
from app.models import User
from app.models.auth_token_model import AuthToken
from app.models.mail_outbox_model import MailOutbox, AuthRateBucket
from app.models.common import utcnow
from app.services.mail_service import process_one, cipher, deliver, build_message


class MailProductionTest(unittest.TestCase):
    def setUp(self):
        self.config = {'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'JWT_SECRET_KEY': 'test-only-jwt-secret-at-least-32-characters', 'REGISTRATION_CODE': 'test-registration-code-at-least-32-characters',
            'MAIL_ENCRYPTION_KEY': Fernet.generate_key().decode(), 'SMTP_HOST': 'smtp.gmail.com', 'SMTP_PORT': 587,
            'SMTP_USERNAME': 'app@gmail.com', 'SMTP_PASSWORD': 'fake-app-password', 'SMTP_FROM': 'app@gmail.com',
            'AUTH_RATE_LIMIT_ENABLED': True}
        self.app = create_app(self.config)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def register(self):
        return self.client.post('/api/auth/register', json={'username': 'nico', 'email': 'nico@example.com',
            'password': 'original-password-123', 'registration_code': self.config['REGISTRATION_CODE']})

    def test_registration_commits_encrypted_job_without_smtp(self):
        with patch('app.services.mail_service.deliver') as smtp:
            self.assertEqual(self.register().status_code, 200)
            smtp.assert_not_called()
        item = db.session.scalar(select(MailOutbox))
        self.assertNotIn('nico@example.com', item.payload)
        payload = json.loads(cipher().decrypt(item.payload.encode()))
        self.assertEqual(payload['email'], 'nico@example.com')
        self.assertNotEqual(db.session.scalar(select(AuthToken)).digest, payload['token'])
        with patch('app.services.mail_service.deliver') as smtp:
            self.assertTrue(process_one())
            self.assertEqual(smtp.call_count, 1)
            message = smtp.call_args.args[0]
            self.assertIn('#token=', message.get_content())
            self.assertNotIn('&token=', message.get_content())
        self.assertEqual(item.status, 'sent')
        self.assertIsNone(item.payload)
        self.assertFalse(process_one())

    def test_transient_failure_retries_then_clears_payload(self):
        self.register()
        item = db.session.scalar(select(MailOutbox))
        with patch('app.services.mail_service.deliver', side_effect=smtplib.SMTPServerDisconnected('sensitive reply')):
            self.assertTrue(process_one())
        self.assertEqual(item.status, 'pending')
        self.assertEqual(item.attempts, 1)
        self.assertEqual(item.last_error, 'SMTPServerDisconnected')
        self.assertGreater(item.available_at, utcnow())
        self.assertFalse(process_one())
        item.available_at = utcnow() - timedelta(seconds=1)
        item.attempts = 5
        db.session.commit()
        with patch('app.services.mail_service.deliver', side_effect=OSError()):
            process_one()
        self.assertEqual(item.status, 'failed')
        self.assertIsNone(item.payload)

    def test_permanent_failure_and_expired_token(self):
        self.register()
        item = db.session.scalar(select(MailOutbox))
        with patch('app.services.mail_service.deliver', side_effect=smtplib.SMTPRecipientsRefused({'email': (550, b'bad address')})):
            process_one()
        self.assertEqual(item.status, 'failed')
        item.status, item.available_at = 'pending', utcnow()
        token = db.session.get(AuthToken, item.token_id)
        token.expires_at = utcnow() - timedelta(seconds=1)
        db.session.commit()
        with patch('app.services.mail_service.deliver') as smtp:
            process_one()
            smtp.assert_not_called()
        self.assertEqual(item.status, 'cancelled')
        self.assertIsNone(item.payload)

    def test_tls_requires_validating_context_before_login(self):
        with patch('app.services.mail_service.smtplib.SMTP') as transport:
            smtp = transport.return_value.__enter__.return_value
            smtp.send_message.return_value = {}
            deliver(build_message('nico@example.com', 'reset', 'secret'))
            context = smtp.starttls.call_args.kwargs['context']
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)
            names = [call[0] for call in smtp.method_calls]
            self.assertLess(names.index('starttls'), names.index('login'))
        self.app.config['SMTP_TLS'], self.app.config['SMTP_SSL'] = False, True
        with patch('app.services.mail_service.smtplib.SMTP_SSL') as transport:
            transport.return_value.__enter__.return_value.send_message.return_value = {}
            deliver(build_message('nico@example.com', 'verify', 'secret'))
            self.assertTrue(transport.call_args.kwargs['context'].check_hostname)
        self.app.config['SMTP_SSL'] = False
        from app.services.management_service import APIError
        with self.assertRaises(APIError):
            deliver(build_message('nico@example.com', 'verify', 'secret'))

    def test_limits_are_shared_and_failure_still_counts(self):
        payload = {'username': 'someone', 'password': 'wrong-password'}
        for _ in range(20):
            self.assertEqual(self.client.post('/api/auth/login', json=payload).status_code, 401)
        # A separate client shares the persistent counter rather than resetting it.
        other_client = self.app.test_client()
        response = other_client.post('/api/auth/login', json=payload)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '300')
        self.assertGreater(db.session.scalar(select(AuthRateBucket.count).order_by(AuthRateBucket.count.desc()).limit(1)), 20)
        for key in db.session.scalars(select(AuthRateBucket.key)):
            self.assertNotIn('someone', key)

    def test_cors_headers_and_request_size(self):
        allowed = self.client.get('/health/live', headers={'Origin': 'http://localhost:5173'})
        self.assertEqual(allowed.headers['Cache-Control'], 'no-store')
        self.assertEqual(allowed.headers['Referrer-Policy'], 'no-referrer')
        evil = self.client.options('/api/auth/login', headers={'Origin': 'https://evil.invalid', 'Access-Control-Request-Method': 'POST'})
        self.assertNotIn('Access-Control-Allow-Origin', evil.headers)
        self.assertEqual(self.client.post('/api/auth/login', json={'username': 'u', 'password': 'x' * 70000}).status_code, 413)

    def test_production_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, 'Configuración de producción inválida'):
            create_app({**self.config, 'PRODUCTION': True})
        valid = {**self.config, 'TESTING': False, 'PRODUCTION': True, 'FRONTEND_URL': 'https://app.example.com',
                 'TRUSTED_HOSTS': ['app.example.com'], 'MAIL_WORKER_AUTOSTART': False, 'SQLALCHEMY_DATABASE_URI': 'postgresql://test:test@localhost/test'}
        app = create_app(valid)
        self.assertFalse(app.debug)
        bad = app.test_client().get('/health/live', headers={'Host': 'evil.invalid'})
        self.assertEqual(bad.status_code, 400)
        for override in [{'SMTP_TLS': False}, {'DEBUG': True}, {'AUTH_RATE_LIMIT_ENABLED': False},
                         {'MAIL_ENCRYPTION_KEY': 'broken'}, {'FRONTEND_URL': 'http://app.example.com'}]:
            with self.assertRaises(RuntimeError):
                create_app({**valid, **override})

    def test_invalidated_jobs_never_send(self):
        self.register()
        item = db.session.scalar(select(MailOutbox))
        token = db.session.get(AuthToken, item.token_id)
        token.used_at = utcnow()
        db.session.commit()
        with patch('app.services.mail_service.deliver') as smtp:
            process_one()
            smtp.assert_not_called()
        self.assertEqual(item.status, 'cancelled')
        self.assertIsNone(item.payload)
