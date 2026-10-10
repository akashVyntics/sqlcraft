import json
import os
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase, override_settings
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress
from .judge import execute_sql, checked_results, same_result, RunnerUnavailable
from .models import Attempt


class RunnerProtocolTests(SimpleTestCase):
    def test_incomplete_or_malformed_results_cannot_be_accepted(self):
        payloads = [{'results': []}, {'results': [{}]}, {'results': [{'columns': ['x'], 'rows': [[1, 2]]}]}, {'results': [{'columns': ['x'], 'rows': [[float('nan')]]}]}]
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(RunnerUnavailable):
                checked_results(payload, (0,))
        self.assertFalse(same_result({'columns': ['x'], 'rows': [[True]]}, {'columns': ['x'], 'rows': [[1]]}))

    def test_production_http_response_is_validated(self):
        with patch.dict(os.environ, {'SQL_RUNNER_URL': 'http://runner:9000', 'SQL_RUNNER_TOKEN': 'test-only-token'}):
            with patch('practice.judge.urlopen') as open_request:
                open_request.return_value.__enter__.return_value.read.return_value = b'{"results": []}'
                with self.assertRaises(RunnerUnavailable):
                    execute_sql('SELECT 1', (0, 7, 22))


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class SubmissionHistoryTests(TestCase):
    def setUp(self):
        self.alice = get_user_model().objects.create_user(username='workspace', email='workspace@example.com', password='a-long-example-password')
        EmailAddress.objects.create(user=self.alice, email=self.alice.email, verified=True, primary=True)
        self.client.force_login(self.alice)

    def post(self, path, payload):
        return self.client.post(path, json.dumps(payload), content_type='application/json')

    def test_bad_sql_submission_is_saved_as_a_failed_attempt(self):
        response = self.post('/api/questions/completed-orders/run/', {'sql': 'SELECT nonexistent FROM orders', 'mode': 'submit'})
        self.assertEqual(response.status_code, 400)
        attempt = Attempt.objects.get(user=self.alice)
        self.assertFalse(attempt.accepted)
        self.assertTrue(attempt.error)
        self.assertEqual(attempt.tests_total, 0)

    def test_unclosed_sql_string_is_a_client_error(self):
        response = self.post('/api/questions/completed-orders/run/', {'sql': "SELECT 'unclosed", 'mode': 'run'})
        self.assertEqual(response.status_code, 400)

    def test_runner_outage_does_not_count_as_a_submission(self):
        with patch('practice.views.execute_sql', side_effect=RunnerUnavailable('Runner unavailable')):
            response = self.post('/api/questions/completed-orders/run/', {'sql': 'SELECT 1', 'mode': 'submit'})
        self.assertEqual(response.status_code, 503)
        self.assertFalse(Attempt.objects.exists())
