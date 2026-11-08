import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet
from sqlalchemy import select
from app import create_app
from app.extensions import db
from app.models import User
from app.models.mail_settings_model import MailSettings
from app.services.mail_service import smtp_config


class MailSettingsTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'JWT_SECRET_KEY': 'test-only-secret-with-at-least-32-characters', 'MAIL_ENCRYPTION_KEY': Fernet.generate_key().decode(),
            'AUTH_RATE_LIMIT_ENABLED': False, 'REGISTRATION_CODE': None})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.origin = {'Origin': 'http://localhost:5173'}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def save(self, **overrides):
        data = {'email': 'app@gmail.com', 'password': 'abcd efgh ijkl mnop',
                'registration_code': 'a-private-team-code', 'username': 'owner', 'admin_password': 'system-password-123'}
        data.update(overrides)
        return self.client.post('/api/settings/mail', json=data, headers=self.origin)

    def test_local_setup_creates_admin_and_stores_only_encrypted_password(self):
        self.assertTrue(self.client.get('/api/settings/mail').json['can_create_admin'])
        self.assertEqual(self.save().status_code, 200)
        user = db.session.scalar(select(User))
        self.assertEqual(user.role, 'admin')
        self.assertTrue(user.check_password('system-password-123'))
        stored = db.session.get(MailSettings, 1)
        self.assertNotIn('abcdefghijklmnop', stored.credentials)
        config = smtp_config()
        self.assertEqual(config['SMTP_PASSWORD'], 'abcdefghijklmnop')
        self.assertEqual(config['SMTP_HOST'], 'smtp.gmail.com')
        response = self.client.get('/api/settings/mail')
        self.assertNotIn('password', response.json)
        self.assertEqual(response.json['registration_code'], 'a-private-team-code')
        self.assertFalse(response.json['can_create_admin'])
        with patch('app.routes.mail_settings_routes.deliver') as sender:
            test = self.client.post('/api/settings/mail/test', json={}, headers=self.origin)
        self.assertEqual(test.status_code, 200)
        self.assertEqual(sender.call_args.args[0]['To'], 'app@gmail.com')
        registration = self.client.post('/api/auth/register', json={'username': 'newuser', 'email': 'someone@example.com', 'password': 'new-user-password-123', 'registration_code': 'a-private-team-code'})
        self.assertEqual(registration.status_code, 200)

    def test_remote_and_cross_origin_bootstrap_are_rejected(self):
        response = self.client.get('/api/settings/mail', environ_overrides={'REMOTE_ADDR': '198.51.100.1'})
        self.assertEqual(response.status_code, 401)
        # A hostile page on a different host cannot bootstrap even when it resolves to loopback.
        response = self.client.get('/api/settings/mail', base_url='http://evil.invalid')
        self.assertEqual(response.status_code, 401)
        response = self.client.post('/api/settings/mail', json={}, headers={'Origin': 'https://evil.invalid'})
        self.assertEqual(response.status_code, 403)

    def test_production_requires_admin_even_on_loopback(self):
        self.save()
        token = self.client.post('/api/auth/login', json={'username': 'owner', 'password': 'system-password-123'}).json['access_token']
        self.app.config['PRODUCTION'] = True
        self.assertEqual(self.client.get('/api/settings/mail').status_code, 401)
        response = self.client.get('/api/settings/mail', headers={'Authorization': 'Bearer ' + token})
        self.assertEqual(response.status_code, 200)
        user = db.session.scalar(select(User))
        user.role = 'operator'
        db.session.commit()
        response = self.client.get('/api/settings/mail', headers={'Authorization': 'Bearer ' + token})
        self.assertEqual(response.status_code, 403)

    def test_empty_password_keeps_existing_and_bad_password_does_not_replace_it(self):
        self.save()
        self.assertEqual(self.save(password='', username=None, admin_password=None).status_code, 200)
        self.assertEqual(smtp_config()['SMTP_PASSWORD'], 'abcdefghijklmnop')
        self.assertEqual(self.save(password='short', username=None, admin_password=None).status_code, 400)
        self.assertEqual(smtp_config()['SMTP_PASSWORD'], 'abcdefghijklmnop')

    def test_new_admin_cannot_be_created_when_one_exists(self):
        self.assertEqual(self.save().status_code, 200)
        self.assertEqual(self.save(username='another').status_code, 409)
        self.assertEqual(db.session.query(User).count(), 1)
