from django.conf import settings
from django.db import models

class Attempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    problem_id = models.CharField(max_length=80)
    sql = models.TextField()
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'problem_id'], name='practice_at_user_id_d4c82d_idx'), models.Index(fields=['user', 'created_at'], name='practice_at_user_id_9b4b17_idx')]

class Draft(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    problem_id = models.CharField(max_length=80)
    sql = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'problem_id'], name='unique_user_problem_draft')]


class LearnerPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    language = models.CharField(max_length=2, choices=[('en', 'English'), ('hi', 'Hinglish')], default='en')
