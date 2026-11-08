import unittest
from cryptography.fernet import Fernet
from datetime import timedelta
from app.models.common import utcnow
from unittest.mock import patch
from app import create_app
from app.extensions import db
from app.models import User
from app.models.auth_token_model import AuthToken
from app.services.management_service import APIError


class EmailAuthTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:', 'JWT_SECRET_KEY': 'test-secret-with-at-least-32-characters', 'REGISTRATION_CODE': 'team-code', 'AUTH_RATE_LIMIT_ENABLED': False, 'MAIL_ENCRYPTION_KEY': Fernet.generate_key().decode(), 'SMTP_HOST': 'smtp.example.invalid', 'SMTP_FROM': 'app@example.com', 'SMTP_USERNAME': 'test', 'SMTP_PASSWORD': 'test'})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.patcher = patch('app.services.email_auth_service.enqueue', wraps=__import__('app.services.mail_service', fromlist=['enqueue']).enqueue)
        self.mail = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def post(self, action, **body):
        return self.client.post('/api/auth/' + action, json=body)

    def register(self, **overrides):
        data = dict(username='nico', email='NICO@example.com', password='original-password-123', registration_code='team-code')
        data.update(overrides)
        return self.post('register', **data)

    def age_tokens(self):
        db.session.query(AuthToken).update({'created_at': utcnow() - timedelta(days=2)})
        db.session.commit()

    def test_full_flow_and_session_revocation(self):
        self.assertEqual(self.register(role='admin').status_code, 200)
        user = db.session.query(User).one()
        self.assertEqual(user.role, 'operator')
        self.assertFalse(user.is_active)
        self.assertEqual(user.email, 'nico@example.com')
        credentials = dict(username='nico', password='original-password-123')
        self.assertEqual(self.post('login', **credentials).status_code, 401)
        token = self.mail.call_args.args[2]
        self.assertNotEqual(db.session.query(AuthToken).one().digest, token)
        self.assertEqual(self.post('reset-password', token=token, password='new-password-123').status_code, 400)
        self.assertEqual(self.post('verify-email', token=token).status_code, 200)
        self.assertEqual(self.post('verify-email', token=token).status_code, 400)
        access = self.post('login', **credentials).json['access_token']
        self.age_tokens()
        self.assertEqual(self.post('forgot-password', email=user.email).status_code, 200)
        reset = self.mail.call_args.args[2]
        self.assertEqual(self.post('reset-password', token=reset, password='short').status_code, 400)
        self.assertEqual(self.post('reset-password', token=reset, password='new-password-123').status_code, 200)
        self.assertEqual(self.post('reset-password', token=reset, password='another-password-123').status_code, 400)
        self.assertEqual(self.client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + access}).status_code, 401)
        self.assertEqual(self.post('login', **credentials).status_code, 401)
        self.assertEqual(self.post('login', username='nico', password='new-password-123').status_code, 200)

    def test_expiry_resend_throttle(self):
        self.register()
        token = self.mail.call_args.args[2]
        self.post('resend-verification', email='nico@example.com')
        self.assertEqual(self.mail.call_count, 1)
        self.age_tokens()
        db.session.query(AuthToken).update({'expires_at': utcnow() - timedelta(days=1)})
        db.session.commit()
        self.assertEqual(self.post('verify-email', token=token).status_code, 400)
        self.post('resend-verification', email='nico@example.com')
        self.assertEqual(self.mail.call_count, 2)
        self.assertEqual(self.post('verify-email', token=self.mail.call_args.args[2]).status_code, 200)

    def test_code_duplicate_and_failed_delivery(self):
        self.assertEqual(self.register(registration_code='wrong').status_code, 403)
        self.mail.side_effect = APIError('Correo no disponible', 503)
        self.assertEqual(self.register().status_code, 503)
        self.assertEqual(db.session.query(User).count(), 0)
        self.mail.side_effect = None
        self.register()
        self.register(password='attacker-password-123')
        self.assertTrue(db.session.query(User).one().check_password('original-password-123'))

    def test_unknown_and_disabled_accounts(self):
        unknown = self.post('forgot-password', email='unknown@example.com')
        self.register()
        self.post('verify-email', token=self.mail.call_args.args[2])
        user = db.session.query(User).one()
        user.is_active = False
        db.session.commit()
        self.mail.reset_mock()
        self.assertEqual(self.post('forgot-password', email=user.email).json, unknown.json)
        self.post('resend-verification', email=user.email)
        self.mail.assert_not_called()


if __name__ == '__main__':
    unittest.main()
