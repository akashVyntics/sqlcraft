from django.conf import settings
from .models import LearnerPreference

def site_settings(request):
    language = None
    if request.user.is_authenticated:
        language = LearnerPreference.objects.filter(user=request.user).values_list('language', flat=True).first() or 'en'
    return {'google_enabled': settings.GOOGLE_ENABLED, 'local_development': settings.DEBUG, 'account_language': language}
