"""Capture the real Django UI in CI; generated images contain no account secrets."""
import base64
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from practice.questions import BY_ID

OUTPUT = Path('.preview')
OUTPUT.mkdir(exist_ok=True)
BASE = 'http://127.0.0.1:8000'

def capture(page, name):
    raw = page.screenshot(full_page=False)
    (OUTPUT / f'{name}.png.base64').write_text(base64.b64encode(raw).decode())

with sync_playwright() as browser_tools:
    browser = browser_tools.chromium.launch()
    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE, wait_until='networkidle')
    page.locator('.problem-title-link').first.wait_for()
    assert page.locator('.problem-title-link').count() == 24
    capture(page, 'dashboard')

    page.goto(BASE + '/accounts/login/', wait_until='networkidle')
    capture(page, 'login')
    page.locator('input[name=login]').fill('preview@example.invalid')
    page.locator('input[name=password]').fill('ci-preview-only-passphrase-2917')
    page.locator('button[type=submit]').click()
    page.wait_for_url(BASE + '/')
    page.goto(BASE + '/problems/completed-orders/', wait_until='networkidle')
    expect(page.locator('#problem-title')).to_have_text('The fulfilled order list')
    page.locator('#sql-editor').fill(BY_ID['completed-orders']['solution'])
    page.locator('#submit').click()
    expect(page.locator('#result-status')).to_have_text('Accepted · 3/3 tests', timeout=30000)
    capture(page, 'workspace')
    page.locator('#language').select_option('hi')
    expect(page.locator('#problem-title')).to_have_text('Complete hue orders ki list')
    capture(page, 'hinglish')

    page.goto(BASE, wait_until='networkidle')
    expect(page.locator('#solved-stat')).to_contain_text('1')
    page.locator('#language').select_option('en')
    page.set_viewport_size({'width': 390, 'height': 844})
    capture(page, 'mobile')
    assert not errors, errors
    browser.close()

(OUTPUT / 'summary.json').write_text(json.dumps({
    'source_branch': 'development',
    'checks': ['24 visible questions', 'email login', 'SQL submit accepted on three datasets', 'Hinglish switch', 'saved solved status', 'mobile layout', 'no browser JavaScript exceptions'],
    'screenshots': ['dashboard', 'login', 'workspace', 'hinglish', 'mobile'],
    'note': 'Screenshots of a local CI app, not a hosted production website. Preview user and database are disposable.',
}, indent=2))
print('Browser preview checks passed. Screenshots generated.')
