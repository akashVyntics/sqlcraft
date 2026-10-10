import json
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress
from .models import LearnerPreference, Draft, Attempt


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class AccountSettingsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='settings', email='settings@example.com', password='a-long-example-password')
        self.email = EmailAddress.objects.create(user=self.user, email=self.user.email, verified=True, primary=True)
        self.client.force_login(self.user)

    def test_preferences_survive_new_session_and_reject_invalid_values(self):
        response = self.client.post('/account/settings/', {'language': 'hi'})
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        self.client.force_login(self.user)
        self.assertContains(self.client.get('/'), 'data-language="hi"')
        response = self.client.post('/api/account/preferences/', json.dumps({'language': 'javascript'}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LearnerPreference.objects.get(user=self.user).language, 'hi')

    def test_unverified_session_cannot_access_private_apis(self):
        self.email.verified = False
        self.email.save()
        Draft.objects.create(user=self.user, problem_id='completed-orders', sql='PRIVATE DRAFT')
        Attempt.objects.create(user=self.user, problem_id='completed-orders', sql='SELECT 1', accepted=True)
        detail = self.client.get('/api/questions/completed-orders/').json()
        self.assertNotIn('draft', detail)
        self.assertFalse(self.client.get('/api/questions/').json()['questions'][0]['solved'])
        self.assertEqual(self.client.get('/api/progress/').status_code, 403)
        self.assertEqual(self.client.post('/api/account/preferences/', '{}', content_type='application/json').status_code, 403)

    def test_password_change_and_post_logout(self):
        password = 'new-strong-account-passphrase-8492'
        response = self.client.post('/accounts/password/change/', {'oldpassword': 'a-long-example-password', 'password1': password, 'password2': password})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(password))
        self.client.get('/accounts/logout/')
        self.assertIn('_auth_user_id', self.client.session)
        self.client.post('/accounts/logout/')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_account_pages_render(self):
        for path in ['/account/settings/', '/accounts/email/', '/accounts/password/change/']:
            self.assertEqual(self.client.get(path).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get('/account/settings/').status_code, 302)
