import os
import subprocess
import sys
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase, Client, override_settings


@override_settings(DEBUG=True)
class ProbeTests(TestCase):
    def test_liveness_and_database_readiness(self):
        self.assertEqual(self.client.get('/health/live/').json(), {'status': 'ok'})
        with patch.dict(os.environ, {'SQL_RUNNER_URL': ''}):
            self.assertEqual(self.client.get('/health/ready/').status_code, 200)

    @override_settings(DEBUG=False)
    def test_production_readiness_requires_runner(self):
        with patch.dict(os.environ, {'SQL_RUNNER_URL': ''}):
            self.assertEqual(self.client.get('/health/ready/').status_code, 503)

    def test_runner_readiness_failure_discloses_no_secrets(self):
        with patch.dict(os.environ, {'SQL_RUNNER_URL': 'http://runner:9000', 'SQL_RUNNER_TOKEN': 'private-secret'}):
            with patch('practice.health.urlopen', side_effect=RuntimeError('private-secret connection failed')):
                response = self.client.get('/health/ready/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'unavailable'})
        self.assertNotContains(response, 'private-secret', status_code=503)

    @override_settings(DEBUG=False)
    def test_unknown_api_and_page_have_safe_errors(self):
        self.assertEqual(self.client.get('/api/missing/').json(), {'error': 'Resource not found.'})
        self.assertContains(self.client.get('/missing/'), 'Page not found', status_code=404)

    def test_api_csrf_failure_is_json(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post('/api/progress/delete/', '{}', content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertIn('security token', response.json()['error'])


class StartupConfigurationTests(SimpleTestCase):
    def test_blank_database_url_uses_sqlite_only_in_development(self):
        result = subprocess.run([sys.executable, 'manage.py', 'check'], env=dict(os.environ, DATABASE_URL='', DJANGO_DEBUG='true'), capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_production_refuses_missing_database(self):
        result = subprocess.run([sys.executable, 'manage.py', 'check'], env=dict(os.environ, DATABASE_URL='', DJANGO_DEBUG='false', DJANGO_SECRET_KEY='ci-only-startup-fixture-key-not-for-production-91882'), capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Production requires DATABASE_URL for durable PostgreSQL', result.stderr)
