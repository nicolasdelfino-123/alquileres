"""Run against an isolated PostgreSQL DB with RENTAL_TEST_DATABASE_URL set."""
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.engine import make_url

from app import create_app
from app.extensions import db
from app.models import User
from app.models.auth_token_model import AuthToken
from app.models.mail_outbox_model import MailOutbox
from app.services.mail_service import cipher, process_one
from app.services.email_auth_service import EmailAuthService
from app.services.rate_limit_service import consume
from app.services.management_service import APIError

URL = os.environ.get('RENTAL_TEST_DATABASE_URL', '')


@unittest.skipUnless(URL.startswith('postgresql'), 'Requires isolated PostgreSQL')
class MailConcurrencyTest(unittest.TestCase):
    def setUp(self):
        if not (make_url(URL).database or '').startswith('codex_rental_test'):
            raise RuntimeError('Only disposable codex_rental_test* databases are permitted')
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': URL,
            'JWT_SECRET_KEY': 'test-only-secret-with-at-least-32-characters', 'AUTH_RATE_LIMIT_ENABLED': False,
            'MAIL_ENCRYPTION_KEY': Fernet.generate_key().decode(), 'REGISTRATION_CODE': 'team-code',
            'SMTP_HOST': 'smtp.example.invalid', 'SMTP_USERNAME': 'app@example.com', 'SMTP_PASSWORD': 'fake', 'SMTP_FROM': 'app@example.com'})
        with self.app.app_context():
            db.create_all()
            EmailAuthService.handle('register', {'username': 'owner', 'email': 'owner@example.com', 'password': 'original-password-123', 'registration_code': 'team-code'})
            item = db.session.scalar(select(MailOutbox))
            self.token = json.loads(cipher().decrypt(item.payload.encode()))['token']

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_two_workers_deliver_job_once(self):
        barrier = Barrier(2)
        def worker():
            with self.app.app_context():
                barrier.wait(timeout=5)
                return process_one()
        with patch('app.services.mail_service.deliver') as deliver:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: worker(), range(2)))
        self.assertEqual(deliver.call_count, 1)
        self.assertEqual(sorted(results), [False, True])

    def test_two_requests_cannot_consume_link_twice(self):
        barrier = Barrier(2)
        def verify():
            with self.app.app_context():
                barrier.wait(timeout=5)
                try:
                    EmailAuthService.handle('verify-email', {'token': self.token})
                    return 200
                except APIError as error:
                    return error.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: verify(), range(2)))
        self.assertEqual(sorted(results), [200, 400])

    def test_atomic_rate_limit_across_sessions(self):
        barrier = Barrier(5)
        def hit():
            with self.app.app_context():
                barrier.wait(timeout=5)
                try:
                    consume('concurrency-test', 'same-user', 2, 60)
                    return True
                except APIError as error:
                    self.assertEqual(error.status, 429)
                    return False
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(lambda _: hit(), range(5)))
        self.assertEqual(results.count(True), 2)
