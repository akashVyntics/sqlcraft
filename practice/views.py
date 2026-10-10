import json
import hashlib
from django.core.cache import cache
from django.core.exceptions import RequestDataTooBig
from django.http import JsonResponse, Http404, StreamingHttpResponse
from django.core.paginator import Paginator, InvalidPage
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from allauth.account.models import EmailAddress
from .forms import PreferenceForm
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from .fixtures import SCHEMA, dataset
from .judge import execute_sql, same_result, RunnerUnavailable
from .models import Attempt, Draft, LearnerPreference
from .questions import QUESTIONS, BY_ID

DATASET_SIGNATURE = hashlib.sha256(json.dumps([dataset(seed) for seed in (0, 7, 22)], sort_keys=True).encode()).hexdigest()

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
    if not EmailAddress.objects.filter(user=request.user, verified=True).exists():
        return JsonResponse({'error': 'Verify your email before using your account.'}, status=403)

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
    except RequestDataTooBig:
        raise ValueError('Request body is too large.')
    except (ValueError, UnicodeDecodeError):
        raise ValueError('Invalid JSON request.')
    if not isinstance(value, dict):
        raise ValueError('Send a JSON object.')
    return value

@require_GET
def question_list(request):
    solved = set()
    if request.user.is_authenticated and EmailAddress.objects.filter(user=request.user, verified=True).exists():
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
    if request.user.is_authenticated and EmailAddress.objects.filter(user=request.user, verified=True).exists():
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
    activity = list(attempts.order_by('-created_at').values('id', 'problem_id', 'accepted', 'error', 'tests_passed', 'tests_total', 'created_at')[:20])
    total = attempts.count()
    accepted = attempts.filter(accepted=True).count()
    dates = set(attempts.dates('created_at', 'day'))
    day = timezone.now().date()
    if day not in dates:
        day -= timedelta(days=1)
    streak = 0
    while day in dates:
        streak += 1
        day -= timedelta(days=1)
    drafts = list(Draft.objects.filter(user=request.user).order_by('-updated_at').values('problem_id', 'updated_at')[:5])
    next_question = next((q for q in QUESTIONS if q['id'] not in solved), None)
    return JsonResponse({'solved': solved, 'total_attempts': total, 'accepted_attempts': accepted,
        'acceptance_rate': round(100 * accepted / total, 1) if total else 0,
        'attempted_count': attempts.values('problem_id').distinct().count(), 'streak_days': streak,
        'drafts': drafts, 'next_problem': next_question['id'] if next_question else None, 'activity': activity,
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
    sql, mode = None, None
    try:
        data = body(request)
        sql = data.get('sql')
        mode = data.get('mode', 'run')
        if mode not in ('run', 'submit'):
            raise ValueError('Choose run or submit.')
        seeds = (0, 7, 22) if mode == 'submit' else (0,)
        actual = execute_sql(sql, seeds)
        key = 'reference:' + hashlib.sha256((DATASET_SIGNATURE + q['id'] + q['solution'] + str(seeds)).encode()).hexdigest()
        expected = cache.get(key)
        if expected is None:
            expected = execute_sql(q['solution'], seeds)
            cache.set(key, expected, 3600)
        checks = [same_result(a, e) for a, e in zip(actual, expected)]
        accepted = all(checks)
        if mode == 'submit':
            Attempt.objects.create(user=request.user, problem_id=slug, sql=sql, accepted=accepted, tests_passed=sum(checks), tests_total=len(checks))
        Draft.objects.update_or_create(user=request.user, problem_id=slug, defaults={'sql': sql})
        return JsonResponse({'actual': actual[0], 'expected': expected[0], 'accepted': accepted,
            'tests_passed': sum(checks), 'tests_total': len(checks), 'submitted': mode == 'submit'})
    except RunnerUnavailable as exc:
        return JsonResponse({'error': str(exc)}, status=503)
    except ValueError as exc:
        if mode == 'submit' and isinstance(sql, str) and 0 < len(sql) <= 12000:
            Attempt.objects.create(user=request.user, problem_id=slug, sql=sql, accepted=False, error=str(exc)[:300])
            Draft.objects.update_or_create(user=request.user, problem_id=slug, defaults={'sql': sql})
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
    with transaction.atomic():
        Attempt.objects.filter(user=request.user).delete()
        Draft.objects.filter(user=request.user).delete()
    return JsonResponse({'deleted': True})


@login_required
def account_settings(request):
    preference, _ = LearnerPreference.objects.get_or_create(user=request.user)
    form = PreferenceForm(request.POST if request.method == 'POST' else None, initial={'language': preference.language})
    if request.method == 'POST' and form.is_valid():
        preference.language = form.cleaned_data['language']
        preference.save(update_fields=['language'])
        messages.success(request, 'Your preferences have been saved.')
        return redirect('account_settings')
    return render(request, 'practice/account_settings.html', {'form': form})


@require_POST
def save_preferences(request):
    if error := auth_error(request):
        return error
    try:
        form = PreferenceForm(body(request))
        if not form.is_valid():
            raise ValueError('Choose English or Hinglish.')
        LearnerPreference.objects.update_or_create(user=request.user, defaults=form.cleaned_data)
        return JsonResponse({'saved': True})
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)


@require_GET
def learning_guide(request):
    levels = [{'name': level, 'count': sum(q['level'] == level for q in QUESTIONS),
               'topics': sorted({q['topic'] for q in QUESTIONS if q['level'] == level})}
              for level in ('Basic', 'Intermediate', 'Advanced', 'Engineering')]
    return render(request, 'practice/guide.html', {'levels': levels})


def attempt_page(request):
    attempts = Attempt.objects.filter(user=request.user).order_by('-created_at', '-id')
    status = request.GET.get('status', 'all')
    slug = request.GET.get('problem', '')
    if status not in ('all', 'accepted', 'failed') or (slug and slug not in BY_ID):
        raise ValueError('Choose a valid status and problem.')
    if status != 'all':
        attempts = attempts.filter(accepted=status == 'accepted')
    if slug:
        attempts = attempts.filter(problem_id=slug)
    page_value = request.GET.get('page', '1')
    if not page_value.isdecimal() or not 1 <= int(page_value) <= 100000:
        raise ValueError('Choose a valid page number.')
    try:
        page = Paginator(attempts, 25).page(int(page_value))
    except InvalidPage:
        raise Http404('Page not found.')
    return page, status, slug


@login_required
@require_GET
def history_page(request):
    if error := auth_error(request):
        return error
    try:
        page, status, slug = attempt_page(request)
    except ValueError as exc:
        return render(request, 'practice/history.html', {'filter_error': str(exc), 'questions': QUESTIONS}, status=400)
    for attempt in page:
        q = BY_ID.get(attempt.problem_id)
        attempt.title = q['title'] if q else {'en': attempt.problem_id, 'hi': attempt.problem_id}
    return render(request, 'practice/history.html', {'attempts': page, 'status': status, 'problem': slug, 'questions': QUESTIONS})


@require_GET
def attempt_history(request):
    if error := auth_error(request):
        return error
    try:
        page, _, _ = attempt_page(request)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    return JsonResponse({'page': page.number, 'pages': page.paginator.num_pages, 'total': page.paginator.count,
        'attempts': [{'id': a.pk, 'problem_id': a.problem_id, 'accepted': a.accepted, 'error': a.error,
                      'tests_passed': a.tests_passed, 'tests_total': a.tests_total, 'created_at': a.created_at}
                     for a in page]})


@require_GET
def attempt_detail(request, attempt_id):
    if error := auth_error(request):
        return error
    attempt = Attempt.objects.filter(user=request.user, pk=attempt_id).first()
    if not attempt:
        return JsonResponse({'error': 'Submission not found.'}, status=404)
    return JsonResponse({'id': attempt.pk, 'problem_id': attempt.problem_id, 'sql': attempt.sql,
        'accepted': attempt.accepted, 'error': attempt.error, 'tests_passed': attempt.tests_passed,
        'tests_total': attempt.tests_total, 'created_at': attempt.created_at})


@require_GET
def export_progress(request):
    if error := auth_error(request):
        return error
    # Stream each account-scoped record; avoid loading an unbounded history in memory.
    def records():
        yield json.dumps({'format_version': 1, 'exported_at': timezone.now().isoformat(), 'email': request.user.email,
                          'language': LearnerPreference.objects.filter(user=request.user).values_list('language', flat=True).first() or 'en'})[:-1]
        for label, queryset, fields in [
            ('drafts', Draft.objects.filter(user=request.user).order_by('pk'), ('problem_id', 'sql', 'updated_at')),
            ('attempts', Attempt.objects.filter(user=request.user).order_by('pk'), ('problem_id', 'sql', 'accepted', 'error', 'tests_passed', 'tests_total', 'created_at')),
        ]:
            yield ', ' + json.dumps(label) + ': ['
            first = True
            for record in queryset.values(*fields).iterator(chunk_size=200):
                if not first:
                    yield ','
                yield json.dumps(record, default=lambda value: value.isoformat())
                first = False
            yield ']'
        yield '}'
    response = StreamingHttpResponse(records(), content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="sqlcraft-practice-data.json"'
    return response
