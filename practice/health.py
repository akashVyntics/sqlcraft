import json
import os
from urllib.request import Request, urlopen
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def live(request):
    return JsonResponse({'status': 'ok'})


@require_GET
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        runner_url = os.getenv('SQL_RUNNER_URL', '')
        if runner_url:
            check = Request(runner_url.rstrip('/') + '/health', headers={'Authorization': 'Bearer ' + os.getenv('SQL_RUNNER_TOKEN', '')})
            with urlopen(check, timeout=3) as response:
                if json.loads(response.read(4096)) != {'status': 'ok'}:
                    raise ValueError('Invalid health response')
        elif not settings.DEBUG:
            raise ValueError('Runner not configured')
    except Exception:
        # A public probe must not disclose connection strings, tokens or stack traces.
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ready'})
