import os
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase, Client, override_settings


class ProbeTests(TestCase):
    def test_liveness_and_database_readiness(self):
        self.assertEqual(self.client.get('/health/live/').json(), {'status': 'ok'})
        with patch.dict(os.environ, {'SQL_RUNNER_URL': ''}):
            self.assertEqual(self.client.get('/health/ready/').status_code, 200)

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
