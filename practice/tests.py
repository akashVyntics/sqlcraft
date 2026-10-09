import json
import os
import re
import subprocess
from urllib.parse import urlsplit
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core import mail
from django.test import Client, TestCase, SimpleTestCase, override_settings
from allauth.account.models import EmailAddress
from .fixtures import dataset
from .judge import execute_sql, validate_sql, same_result
from .models import Attempt, Draft
from .questions import QUESTIONS, BY_ID

class CurriculumTests(SimpleTestCase):
    def test_all_reference_queries_run_across_datasets(self):
        for q in QUESTIONS:
            with self.subTest(problem=q['id']):
                results = execute_sql(q['solution'], (0, 7, 22))
                self.assertEqual(len(results), 3)
                self.assertTrue(all(r['columns'] for r in results))

    def test_all_questions_have_both_languages_and_unique_ids(self):
        self.assertEqual(len(QUESTIONS), len(BY_ID))
        for q in QUESTIONS:
            for field in ('title', 'prompt', 'hint', 'explanation'):
                self.assertTrue(q[field]['en'])
                self.assertTrue(q[field]['hi'])

    def test_readonly_and_external_access_rules(self):
        for sql in ["DROP TABLE orders", "SELECT 1; DELETE FROM orders", "COPY orders TO '/tmp/leak.csv'", "SELECT * FROM read_csv('/etc/passwd')", "SELECT * FROM sqlite_scan('/tmp/db.sqlite3', 'users')", "SELECT * FROM information_schema.tables", "SELECT * FROM query('SELECT 1')", "SELECT * INTO new_table FROM orders", "SELECT getenv('SECRET')"]:
            with self.subTest(sql=sql), self.assertRaises(ValueError):
                validate_sql(sql)
        validate_sql("WITH totals AS (SELECT SUM(amount) AS amount FROM orders) SELECT amount FROM totals")

    def test_row_limit_and_invalid_query(self):
        with self.assertRaises(ValueError):
            execute_sql('SELECT a.order_id FROM orders a CROSS JOIN orders b')
        with self.assertRaises(ValueError):
            execute_sql('SELECT missing_column FROM orders')

    def test_judge_requires_order_and_preserves_duplicates(self):
        expected = {'columns': ['x'], 'rows': [[1], [1], [2]]}
        self.assertTrue(same_result(expected, expected))
        self.assertFalse(same_result({'columns': ['x'], 'rows': [[1], [2]]}, expected))
        self.assertFalse(same_result({'columns': ['x'], 'rows': [[2], [1], [1]]}, expected))
        self.assertFalse(same_result({'columns': ['wrong'], 'rows': expected['rows']}, expected))
        self.assertTrue(same_result({'columns': ['x'], 'rows': [[0.3]]}, {'columns': ['x'], 'rows': [[0.1 + 0.2]]}))

    def test_production_requires_an_isolated_runner(self):
        with patch.dict(os.environ, {'DJANGO_DEBUG': 'false', 'SQL_RUNNER_URL': '', 'SQL_RUNNER_TOKEN': ''}):
            with self.assertRaisesMessage(ValueError, 'isolated query runner'):
                execute_sql('SELECT 1')

    def test_timeout_releases_execution_capacity(self):
        with patch('practice.judge.subprocess.run', side_effect=subprocess.TimeoutExpired('worker', 8)):
            for _ in range(3):
                with self.assertRaisesMessage(ValueError, 'Query timed out'):
                    execute_sql('SELECT 1')
        self.assertEqual(execute_sql('SELECT 1 AS value')[0]['rows'], [[1]])

    def test_unbounded_recursive_query_is_terminated(self):
        sql = 'WITH RECURSIVE numbers AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM numbers) SELECT SUM(n) FROM numbers'
        validate_sql(sql)
        with self.assertRaises(ValueError):
            execute_sql(sql)

@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AccountAndProgressTests(TestCase):
    def setUp(self):
        cache.clear()
        self.alice = get_user_model().objects.create_user(username='alice', email='alice@example.com', password='a-long-example-password')
        self.bob = get_user_model().objects.create_user(username='bob', email='bob@example.com', password='a-long-example-password')
        EmailAddress.objects.create(user=self.alice, email=self.alice.email, primary=True, verified=True)
        self.client.force_login(self.alice)

    def post(self, path, data):
        return self.client.post(path, json.dumps(data), content_type='application/json')

    def test_anonymous_user_cannot_read_or_write_private_records(self):
        self.client.logout()
        for path, method in [('/api/progress/', 'get'), ('/api/progress/delete/', 'post'), ('/api/questions/completed-orders/draft/', 'post'), ('/api/questions/completed-orders/run/', 'post'), ('/api/questions/completed-orders/solution/', 'post')]:
            response = getattr(self.client, method)(path)
            self.assertEqual(response.status_code, 401)

    def test_users_cannot_read_or_overwrite_each_others_progress(self):
        Draft.objects.create(user=self.bob, problem_id='completed-orders', sql='private bob draft')
        Attempt.objects.create(user=self.bob, problem_id='completed-orders', sql='private', accepted=True)
        self.assertEqual(self.client.get('/api/progress/').json()['solved'], [])
        self.assertIsNone(self.client.get('/api/questions/completed-orders/').json()['draft'])
        self.post('/api/questions/completed-orders/draft/', {'sql': 'SELECT 1', 'user_id': self.bob.pk})
        self.assertEqual(Draft.objects.get(user=self.bob).sql, 'private bob draft')
        self.assertEqual(Draft.objects.get(user=self.alice).sql, 'SELECT 1')
        self.post('/api/progress/delete/', {})
        self.assertTrue(Attempt.objects.filter(user=self.bob).exists())
        self.assertTrue(Draft.objects.filter(user=self.bob).exists())

    def test_run_does_not_mark_solved_but_submit_does(self):
        sql = BY_ID['completed-orders']['solution']
        result = self.post('/api/questions/completed-orders/run/', {'sql': sql, 'mode': 'run'})
        self.assertEqual(result.status_code, 200, result.content)
        self.assertTrue(result.json()['accepted'])
        self.assertEqual(Attempt.objects.count(), 0)
        result = self.post('/api/questions/completed-orders/run/', {'sql': sql, 'mode': 'submit'})
        self.assertEqual(result.status_code, 200, result.content)
        self.assertEqual(result.json()['tests_passed'], 3)
        self.assertEqual(self.client.get('/api/progress/').json()['solved'], ['completed-orders'])

    def test_submission_checks_additional_data(self):
        public_total = sum(row[4] for row in dataset(0)['orders'] if row[3] == 'completed')
        result = self.post('/api/questions/revenue-total/run/', {'sql': f'SELECT {public_total} AS revenue', 'mode': 'submit'})
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json()['accepted'])
        self.assertEqual(result.json()['tests_passed'], 1)

    def test_csrf_is_required_for_authenticated_writes(self):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.alice)
        self.assertEqual(browser.post('/api/questions/completed-orders/draft/', json.dumps({'sql': 'SELECT 1'}), content_type='application/json').status_code, 403)
        browser.get('/problems/completed-orders/')
        token = browser.cookies['csrftoken'].value
        result = browser.post('/api/questions/completed-orders/draft/', json.dumps({'sql': 'SELECT 1'}), content_type='application/json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(result.status_code, 200)

    def test_auth_configuration_and_unverified_login(self):
        self.assertEqual(settings.ACCOUNT_EMAIL_VERIFICATION, 'mandatory')
        self.assertFalse(settings.SOCIALACCOUNT_EMAIL_AUTHENTICATION)
        self.client.logout()
        response = self.client.post('/accounts/login/', {'login': 'bob@example.com', 'password': 'a-long-example-password'})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_does_not_accept_external_redirect(self):
        self.client.logout()
        response = self.client.post('/accounts/login/?next=https://evil.example', {'login': 'alice@example.com', 'password': 'a-long-example-password', 'next': 'https://evil.example'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response['Location'].startswith('https://evil.example'))

    def test_api_validation_and_limits(self):
        self.assertEqual(self.post('/api/questions/completed-orders/draft/', {'sql': 'x' * 12001}).status_code, 400)
        self.assertEqual(self.post('/api/questions/no-such-question/draft/', {'sql': 'SELECT 1'}).status_code, 404)
        self.assertEqual(self.post('/api/questions/completed-orders/run/', {'sql': 'DROP TABLE orders'}).status_code, 400)
        cache.set(f'limit:query:{self.alice.pk}', 15, 60)
        self.assertEqual(self.post('/api/questions/completed-orders/run/', {'sql': 'SELECT 1'}).status_code, 429)

    def test_public_problem_does_not_leak_solution(self):
        self.client.logout()
        data = self.client.get('/api/questions/scd-history/').json()
        self.assertNotIn('solution', data)
        self.assertNotIn('explanation', data)

    def test_google_button_is_not_faked_without_configuration(self):
        self.client.logout()
        with override_settings(GOOGLE_ENABLED=False):
            self.assertNotContains(self.client.get('/accounts/login/'), 'Continue with Google')

    def test_security_headers_and_rendered_pages(self):
        self.client.logout()
        for path in ['/', '/problems/completed-orders/', '/accounts/login/', '/accounts/signup/', '/accounts/password/reset/']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn("default-src 'self'", response['Content-Security-Policy'])
            self.assertEqual(response['X-Frame-Options'], 'DENY')

    def test_account_sessions_are_separate(self):
        self.post('/api/questions/completed-orders/draft/', {'sql': 'SELECT 1'})
        self.client.logout()
        self.client.force_login(self.bob)
        self.assertIsNone(self.client.get('/api/questions/completed-orders/').json()['draft'])

    def test_signup_verification_and_first_login(self):
        self.client.logout()
        password = 'a-unique-new-user-passphrase-927'
        response = self.client.post('/accounts/signup/', {'email': 'newlearner@example.com', 'password1': password, 'password2': password})
        self.assertEqual(response.status_code, 302)
        learner = get_user_model().objects.get(email='newlearner@example.com')
        email = EmailAddress.objects.get(user=learner)
        self.assertFalse(email.verified)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertTrue(mail.outbox)
        link = re.search(r'https?://[^\s<>\"]+/accounts/confirm-email/[^\s/<>\"]+/', mail.outbox[-1].body)
        self.assertIsNotNone(link, mail.outbox[-1].body)
        confirmation_path = urlsplit(link.group()).path
        self.assertEqual(self.client.get(confirmation_path).status_code, 200)
        response = self.client.post(confirmation_path)
        self.assertEqual(response.status_code, 302)
        email.refresh_from_db()
        self.assertTrue(email.verified)
        self.client.post('/accounts/login/', {'login': learner.email, 'password': password})
        self.assertEqual(int(self.client.session['_auth_user_id']), learner.pk)

    def test_password_reset_link_changes_password(self):
        self.client.logout()
        response = self.client.post('/accounts/password/reset/', {'email': self.alice.email})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(mail.outbox)
        link = re.search(r'https?://[^\s<>\"]+/accounts/password/reset/key/[^\s<>\"]+', mail.outbox[-1].body)
        self.assertIsNotNone(link, mail.outbox[-1].body)
        response = self.client.get(urlsplit(link.group()).path, follow=True)
        self.assertEqual(response.status_code, 200)
        reset_path = response.request['PATH_INFO']
        password = 'a-brand-new-reset-passphrase-813'
        response = self.client.post(reset_path, {'password1': password, 'password2': password})
        self.assertEqual(response.status_code, 302)
        self.alice.refresh_from_db()
        self.assertTrue(self.alice.check_password(password))
        self.assertFalse(self.alice.check_password('a-long-example-password'))

    def test_draft_survives_a_new_browser_session(self):
        sql = BY_ID['completed-orders']['solution']
        self.assertEqual(self.post('/api/questions/completed-orders/draft/', {'sql': sql}).status_code, 200)
        other_browser = Client()
        other_browser.force_login(self.alice)
        data = other_browser.get('/api/questions/completed-orders/').json()
        self.assertEqual(data['draft'], sql)
