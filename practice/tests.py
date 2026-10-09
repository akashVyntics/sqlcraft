import json
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
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
