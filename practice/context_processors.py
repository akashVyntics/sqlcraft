from django.conf import settings
def site_settings(request):
    return {'google_enabled': settings.GOOGLE_ENABLED, 'local_development': settings.DEBUG}
