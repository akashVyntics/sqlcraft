from django.contrib import admin
from django.urls import include, path
from practice import health
handler404 = 'practice.errors.not_found'
handler500 = 'practice.errors.server_error'
urlpatterns = [path('health/live/', health.live), path('health/ready/', health.ready), path('admin/', admin.site.urls), path('accounts/', include('allauth.urls')), path('', include('practice.urls'))]
