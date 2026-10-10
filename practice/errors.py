from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import render
from django.views.csrf import csrf_failure as default_csrf_failure


def csrf_failure(request, reason=''):
    if request.path.startswith('/api/'):
        return JsonResponse({'error': 'Your session security token has expired. Refresh the page and try again.'}, status=403)
    return default_csrf_failure(request, reason=reason)


def not_found(request, exception):
    if request.path.startswith('/api/'):
        return JsonResponse({'error': 'Resource not found.'}, status=404)
    return render(request, '404.html', status=404)


def server_error(request):
    if request.path.startswith('/api/'):
        return JsonResponse({'error': 'The server could not complete this request. Please try again.'}, status=500)
    return HttpResponse(render_to_string('500.html'), status=500)
