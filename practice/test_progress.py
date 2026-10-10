import json
from datetime import timedelta
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from allauth.account.models import EmailAddress
from .models import Attempt, Draft


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class HistoryAndExportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='history', email='history@example.com', password='a-long-example-password')
        self.other = get_user_model().objects.create_user(username='other-history', email='other@example.com', password='a-long-example-password')
        EmailAddress.objects.create(user=self.user, email=self.user.email, verified=True, primary=True)
        self.client.force_login(self.user)
        self.private = Attempt.objects.create(user=self.other, problem_id='completed-orders', sql='PRIVATE OTHER SQL', accepted=True)

    def test_paginated_history_filters_and_ownership(self):
        Attempt.objects.bulk_create([Attempt(user=self.user, problem_id='completed-orders', sql='SELECT 1', accepted=i % 2 == 0) for i in range(31)])
        data = self.client.get('/api/attempts/?page=2').json()
        self.assertEqual(data['total'], 31)
        self.assertEqual(len(data['attempts']), 6)
        self.assertEqual(self.client.get('/api/attempts/?status=accepted').json()['total'], 16)
        self.assertEqual(self.client.get(f'/api/attempts/{self.private.pk}/').status_code, 404)
        for suffix in ['?page=0', '?page=abc', '?status=invalid', '?problem=missing']:
            self.assertEqual(self.client.get('/api/attempts/' + suffix).status_code, 400)
        self.assertEqual(self.client.get('/api/attempts/?page=999').status_code, 404)
        self.assertNotContains(self.client.get('/history/'), 'PRIVATE OTHER SQL')

    def test_export_contains_all_owned_records_and_no_other_user(self):
        Draft.objects.create(user=self.user, problem_id='completed-orders', sql='SELECT "escaped"')
        Attempt.objects.create(user=self.user, problem_id='completed-orders', sql='SELECT 1', error='Query error')
        response = self.client.get('/api/progress/export/')
        exported = json.loads(b''.join(response.streaming_content))
        self.assertEqual(exported['email'], self.user.email)
        self.assertEqual(exported['drafts'][0]['sql'], 'SELECT "escaped"')
        self.assertEqual(len(exported['attempts']), 1)
        self.assertNotIn('PRIVATE OTHER SQL', json.dumps(exported))
        self.assertIn('attachment', response['Content-Disposition'])
        self.client.logout()
        self.assertEqual(self.client.get('/api/progress/export/').status_code, 401)

    def test_streak_duplicates_and_resume_progress(self):
        now = timezone.now().replace(hour=12)
        for days in (0, 0, 1, 3):
            attempt = Attempt.objects.create(user=self.user, problem_id='completed-orders', sql='SELECT 1', accepted=days == 0)
            Attempt.objects.filter(pk=attempt.pk).update(created_at=now - timedelta(days=days))
        Draft.objects.create(user=self.user, problem_id='revenue-total', sql='SELECT SUM(amount)')
        data = self.client.get('/api/progress/').json()
        self.assertEqual(data['streak_days'], 2)
        self.assertEqual(data['accepted_attempts'], 2)
        self.assertEqual(data['acceptance_rate'], 50)
        self.assertEqual(data['attempted_count'], 1)
        self.assertEqual(data['solved'], ['completed-orders'])
        self.assertEqual(data['drafts'][0]['problem_id'], 'revenue-total')
        self.assertNotEqual(data['next_problem'], 'completed-orders')
