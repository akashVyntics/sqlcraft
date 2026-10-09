import json
import hashlib
from django.core.cache import cache
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from .fixtures import SCHEMA, dataset
from .judge import execute_sql, same_result
from .models import Attempt, Draft
from .questions import QUESTIONS, BY_ID

@ensure_csrf_cookie
def home(request):
    return render(request, 'practice/home.html', {'question_count': len(QUESTIONS)})

@ensure_csrf_cookie
def problem_page(request, slug):
    if slug not in BY_ID:
        raise Http404
    return render(request, 'practice/problem.html', {'problem_id': slug})

def auth_error(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Sign in to save your progress and run queries.'}, status=401)

def limited(request, category, count=30):
    key = f'limit:{category}:{request.user.pk}'
    if cache.add(key, 1, 60):
        return False
    try:
        current = cache.incr(key)
    except ValueError:
        cache.set(key, 1, 60)
        return False
    return current > count

def body(request):
    if request.content_type != 'application/json':
        raise ValueError('Send an application/json request.')
    try:
        value = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('Invalid JSON request.')
    if not isinstance(value, dict):
        raise ValueError('Send a JSON object.')
    return value

@require_GET
def question_list(request):
    solved = set()
    if request.user.is_authenticated:
        solved = set(Attempt.objects.filter(user=request.user, accepted=True).values_list('problem_id', flat=True))
    return JsonResponse({'questions': [{k: q[k] for k in ('id', 'title', 'level', 'topic')} | {'solved': q['id'] in solved} for q in QUESTIONS]})

@require_GET
def question_detail(request, slug):
    q = BY_ID.get(slug)
    if not q:
        return JsonResponse({'error': 'Problem not found.'}, status=404)
    public = {k: v for k, v in q.items() if k not in ('solution', 'explanation')}
    samples = dataset(0)
    public['schema'] = [{'name': t, 'columns': SCHEMA[t], 'rows': samples[t], 'row_count': len(samples[t])} for t in q['tables']]
    if request.user.is_authenticated:
        draft = Draft.objects.filter(user=request.user, problem_id=slug).first()
        public['draft'] = draft.sql if draft else None
        public['solved'] = Attempt.objects.filter(user=request.user, problem_id=slug, accepted=True).exists()
    return JsonResponse(public)

@require_GET
def progress(request):
    if error := auth_error(request):
        return error
    attempts = Attempt.objects.filter(user=request.user)
    solved = list(attempts.filter(accepted=True).values_list('problem_id', flat=True).distinct())
    activity = list(attempts.order_by('-created_at').values('problem_id', 'accepted', 'created_at')[:20])
    return JsonResponse({'solved': solved, 'total_attempts': attempts.count(), 'activity': activity,
        'email': request.user.email, 'by_level': {level: sum(q['id'] in solved for q in QUESTIONS if q['level'] == level) for level in ('Basic', 'Intermediate', 'Advanced', 'Engineering')}})

@require_POST
def save_draft(request, slug):
    if error := auth_error(request):
        return error
    if slug not in BY_ID:
        return JsonResponse({'error': 'Problem not found.'}, status=404)
    if limited(request, 'draft', 60):
        return JsonResponse({'error': 'Too many saves. Try again in a minute.'}, status=429)
    try:
        sql = body(request).get('sql')
        if not isinstance(sql, str) or len(sql) > 12000:
            raise ValueError('Draft must be at most 12,000 characters.')
        Draft.objects.update_or_create(user=request.user, problem_id=slug, defaults={'sql': sql})
        return JsonResponse({'saved': True})
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

@require_POST
def run_query(request, slug):
    if error := auth_error(request):
        return error
    q = BY_ID.get(slug)
    if not q:
        return JsonResponse({'error': 'Problem not found.'}, status=404)
    if limited(request, 'query', 15):
        return JsonResponse({'error': 'Query limit reached. Try again in a minute.'}, status=429)
    try:
        data = body(request)
        sql = data.get('sql')
        mode = data.get('mode', 'run')
        if mode not in ('run', 'submit'):
            raise ValueError('Choose run or submit.')
        seeds = (0, 7, 22) if mode == 'submit' else (0,)
        actual = execute_sql(sql, seeds)
        key = 'reference:' + hashlib.sha256((q['id'] + q['solution'] + str(seeds)).encode()).hexdigest()
        expected = cache.get(key)
        if expected is None:
            expected = execute_sql(q['solution'], seeds)
            cache.set(key, expected, 3600)
        checks = [same_result(a, e) for a, e in zip(actual, expected)]
        accepted = all(checks)
        if mode == 'submit':
            Attempt.objects.create(user=request.user, problem_id=slug, sql=sql, accepted=accepted)
        Draft.objects.update_or_create(user=request.user, problem_id=slug, defaults={'sql': sql})
        return JsonResponse({'actual': actual[0], 'expected': expected[0], 'accepted': accepted,
            'tests_passed': sum(checks), 'tests_total': len(checks), 'submitted': mode == 'submit'})
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

@require_POST
def reveal_solution(request, slug):
    if error := auth_error(request):
        return error
    q = BY_ID.get(slug)
    if not q:
        return JsonResponse({'error': 'Problem not found.'}, status=404)
    return JsonResponse({'sql': q['solution'], 'explanation': q['explanation']})

@require_POST
def delete_progress(request):
    if error := auth_error(request):
        return error
    Attempt.objects.filter(user=request.user).delete()
    Draft.objects.filter(user=request.user).delete()
    return JsonResponse({'deleted': True})
