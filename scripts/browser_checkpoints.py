"""Exercise real UI/API behavior with an ephemeral non-staff account."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from practice.questions import QUESTIONS, BY_ID

BASE = 'http://127.0.0.1:8000'
OUTPUT = Path('browser-artifacts')
OUTPUT.mkdir(exist_ok=True)

with sync_playwright() as driver:
    browser = driver.chromium.launch()
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE, wait_until='networkidle')
    expect(page.locator('.problem-title-link')).to_have_count(len(QUESTIONS))
    page.locator('#topic-filter').select_option('Product analytics')
    expect(page.locator('.problem-title-link')).to_have_count(4)
    page.locator('#search').fill('no such question 928162')
    expect(page.locator('#list-message')).to_have_text('No problems match these filters.')
    page.locator('#search').fill('')
    page.locator('#topic-filter').select_option('all')
    page.locator('.tab[data-level=Engineering]').click()
    expect(page.locator('.problem-title-link')).to_have_count(8)
    page.goto(BASE + '/learn/', wait_until='networkidle')
    expect(page.locator('h1')).to_have_text('Your SQL learning path')

    page.goto(BASE + '/accounts/login/', wait_until='networkidle')
    page.locator('input[name=login]').fill('browser@example.invalid')
    page.locator('input[name=password]').fill('ci-browser-only-fixture-passphrase-8274')
    page.locator('button[type=submit]').click()
    page.wait_for_url(BASE + '/')
    page.goto(BASE + '/account/settings/', wait_until='networkidle')
    page.locator('select[name=language]').select_option('hi')
    page.locator('button[type=submit]').click()
    expect(page.locator('.messages')).to_contain_text('Your preferences have been saved.')
    page.goto(BASE + '/problems/completed-orders/', wait_until='networkidle')
    expect(page.locator('#problem-title')).to_have_text(BY_ID['completed-orders']['title']['hi'])
    query = BY_ID['completed-orders']['solution']
    page.locator('#sql-editor').fill(query)
    page.locator('#save-draft').click()
    expect(page.locator('#save-status')).to_have_text('Draft saved to your account')
    page.reload(wait_until='networkidle')
    expect(page.locator('#sql-editor')).to_have_value(query)
    page.locator('#run').click()
    expect(page.locator('#result-status')).to_have_text('Public test passed · 1/1 tests', timeout=30000)
    assert page.request.get(BASE + '/api/progress/').json()['solved'] == []
    page.locator('#submit').click()
    expect(page.locator('#result-status')).to_have_text('Accepted · 3/3 tests', timeout=30000)
    page.locator('#reveal-solution').click()
    expect(page.locator('#solution-explanation')).to_have_text(BY_ID['completed-orders']['explanation']['hi'])
    page.screenshot(path=str(OUTPUT / 'workspace-hinglish.png'))
    page.locator('#sql-editor').fill('SELECT missing_column FROM orders')
    page.locator('#submit').click()
    expect(page.locator('#result-status')).to_have_text('Query could not complete', timeout=30000)
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('#reset-editor').click()
    expect(page.locator('#sql-editor')).to_have_value(BY_ID['completed-orders']['starter'])
    page.locator('#save-draft').click()
    expect(page.locator('#save-status')).to_have_text('Draft saved to your account')
    page.reload(wait_until='networkidle')
    expect(page.locator('#sql-editor')).to_have_value(BY_ID['completed-orders']['starter'])
    page.goto(BASE + '/history/', wait_until='networkidle')
    expect(page.locator('main .progress-card')).to_have_count(2)
    expect(page.locator('main')).to_contain_text('Query error')
    page.locator('select[name=status]').select_option('accepted')
    page.locator('button[type=submit]').click()
    expect(page.locator('main .progress-card')).to_have_count(1)
    exported = page.request.get(BASE + '/api/progress/export/').json()
    assert len(exported['attempts']) == 2 and exported['language'] == 'hi'
    assert exported['email'] == 'browser@example.invalid'
    page.goto(BASE, wait_until='networkidle')
    expect(page.locator('#solved-stat')).to_contain_text('1')
    expect(page.locator('#attempt-stat')).to_contain_text('2')
    page.screenshot(path=str(OUTPUT / 'dashboard.png'))
    with page.expect_response('**/api/account/preferences/') as saved:
        page.locator('#language').select_option('en')
    assert saved.value.ok
    page.reload(wait_until='networkidle')
    expect(page.locator('#language')).to_have_value('en')
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(OUTPUT / 'mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), str(page.evaluate("Array.from(document.querySelectorAll('body *')).filter(e => e.getBoundingClientRect().right > innerWidth).slice(0,15).map(e => [e.tagName,e.id,e.className,e.getBoundingClientRect().right])"))
    page.goto(BASE + '/history/', wait_until='networkidle')
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile history overflows horizontally'
    page.screenshot(path=str(OUTPUT / 'history-mobile.png'))
    page.goto(BASE + '/accounts/logout/', wait_until='networkidle')
    page.locator('button[type=submit]').click()
    page.wait_for_url(BASE + '/')
    assert page.request.get(BASE + '/api/progress/').status == 401
    assert page.request.get(BASE + '/api/attempts/').status == 401
    assert not errors, errors
    browser.close()
print('PASS: catalog filters, learning guide, sign-in, account preferences, draft persistence, Run/Submit, failed submissions, solutions, history filters, export, progress, mobile rendering and POST sign-out')
