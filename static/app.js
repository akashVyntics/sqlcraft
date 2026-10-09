'use strict';
(() => {
  const $ = (selector) => document.querySelector(selector);
  const authenticated = document.body.dataset.authenticated === 'true';
  let language = 'en';
  try { language = localStorage.getItem('sqlcraft-language') === 'hi' ? 'hi' : 'en'; } catch (_) {}
  const languageSelect = $('#language');
  languageSelect.value = language;
  let questions = [];
  let currentProblem = null;
  let solution = null;
  let level = 'all';
  let draftTimer;
  let draftSequence = 0;
  let draftChain = Promise.resolve();
  let busy = false;
  const el = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  };
  const token = () => {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : '';
  };
  async function api(path, data) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    let response;
    try { response = await fetch(path, {
      credentials: 'same-origin',
      signal: controller.signal,
      headers: data === undefined ? {} : {'Content-Type': 'application/json', 'X-CSRFToken': token()},
      method: data === undefined ? 'GET' : 'POST',
      body: data === undefined ? undefined : JSON.stringify(data),
    }); } catch (error) {
      if (error.name === 'AbortError') throw new Error('Request timed out. Please try again.');
      throw new Error('Could not reach the server. Check your connection and try again.');
    } finally { clearTimeout(timeout); }
    let result;
    try { result = await response.json(); } catch (_) { throw new Error('The server could not complete this request. Please try again.'); }
    if (!response.ok) throw new Error(result.error || 'Request failed. Please try again.');
    return result;
  }
  function badge(value) { return el('span', value, 'badge ' + value.toLowerCase()); }
  function dataTable(columns, rows, types) {
    const wrap = el('div', undefined, 'result-scroll');
    const table = el('table', undefined, 'data-table');
    const head = el('thead'); const headRow = el('tr');
    columns.forEach((column, index) => { const th = el('th', column); th.scope = 'col'; if (types) th.append(el('small', types[index])); headRow.append(th); });
    head.append(headRow); table.append(head);
    const body = el('tbody');
    rows.forEach(row => { const tr = el('tr'); row.forEach(value => { const td = el('td', value === null ? 'NULL' : value, value === null ? 'null' : undefined); td.title = value === null ? 'NULL' : String(value); tr.append(td); }); body.append(tr); });
    table.append(body); wrap.append(table);
    if (!rows.length) wrap.append(el('p', 'No rows returned.', 'empty-state'));
    return wrap;
  }
  function renderQuestions() {
    const target = $('#problem-list'); if (!target) return;
    target.replaceChildren();
    const text = ($('#search').value || '').toLowerCase();
    const status = $('#status-filter').value;
    const visible = questions.filter(q => (level === 'all' || q.level === level) &&
      (status === 'all' || (status === 'solved') === q.solved) &&
      [q.title.en, q.title.hi, q.topic].some(v => v.toLowerCase().includes(text)));
    visible.forEach(q => {
      const tr = el('tr');
      const statusCell = el('td'); const dot = el('span', q.solved ? '✓' : '○', q.solved ? 'solved-dot' : 'unsolved-dot'); dot.setAttribute('aria-label', q.solved ? 'Solved' : 'Unsolved'); statusCell.append(dot);
      const titleCell = el('td'); const link = el('a', undefined, 'problem-title-link'); link.href = '/problems/' + q.id + '/'; link.append(el('span', String(questions.indexOf(q) + 1).padStart(2, '0'), 'problem-number'), el('span', q.title[language])); titleCell.append(link);
      const levelCell = el('td'); levelCell.append(badge(q.level));
      const arrow = el('td'); const arrowLink = el('a', '↗'); arrowLink.href = link.href; arrowLink.setAttribute('aria-label', 'Open ' + q.title[language]); arrow.append(arrowLink);
      tr.append(statusCell, titleCell, levelCell, el('td', q.topic, 'topic-text'), arrow); target.append(tr);
    });
    $('#problem-count').textContent = visible.length + ' of ' + questions.length + ' problems';
    $('#list-message').hidden = visible.length > 0;
    $('#list-message').textContent = 'No problems match these filters.';
  }
  function setLevel(value) {
    level = value;
    document.querySelectorAll('.tab').forEach(button => { const selected = button.dataset.level === level; button.classList.toggle('selected', selected); button.setAttribute('aria-pressed', String(selected)); });
    renderQuestions();
  }
  async function loadProgress() {
    if (!authenticated || !$('#progress-content')) return;
    try {
      const data = await api('/api/progress/');
      $('#solved-stat').replaceChildren(el('span', data.solved.length), el('small', 'of ' + questions.length));
      $('#attempt-stat').replaceChildren(el('span', data.total_attempts), el('small', 'recorded submissions'));
      questions.forEach(q => { q.solved = data.solved.includes(q.id); }); renderQuestions();
      const container = $('#progress-content'); container.replaceChildren();
      const levels = el('div', undefined, 'progress-levels');
      ['Basic', 'Intermediate', 'Advanced', 'Engineering'].forEach(value => {
        const total = questions.filter(q => q.level === value).length;
        const card = el('div', undefined, 'progress-level'); card.append(el('h3', value), el('p', data.by_level[value] + ' / ' + total + ' solved'));
        const meter = el('progress'); meter.max = total; meter.value = data.by_level[value]; meter.setAttribute('aria-label', value + ' progress'); card.append(meter); levels.append(card);
      }); container.append(levels);
      const activity = el('div', undefined, 'activity-list'); activity.append(el('h3', 'Recent submissions'));
      if (!data.activity.length) activity.append(el('p', 'Your first submission will appear here.'));
      data.activity.forEach(item => { const q = questions.find(q => q.id === item.problem_id); const row = el('div', undefined, 'activity-row'); const a = el('a', q ? q.title[language] : item.problem_id); a.href = '/problems/' + item.problem_id + '/'; const time = el('time', new Date(item.created_at).toLocaleString()); time.dateTime = item.created_at; row.append(a, el('span', item.accepted ? 'Accepted' : 'Try again', item.accepted ? 'result-status-pass' : ''), time); activity.append(row); });
      container.append(activity);
    } catch (error) { $('#progress-content').replaceChildren(el('p', error.message, 'load-error')); $('#solved-caption').textContent = 'Progress could not load. Refresh to retry.'; }
  }
  function renderProblemLanguage() {
    if (!currentProblem) return;
    $('#problem-title').textContent = currentProblem.title[language];
    document.title = currentProblem.title[language] + ' — SQLCraft';
    $('#problem-prompt').textContent = currentProblem.prompt[language];
    $('#problem-hint').textContent = currentProblem.hint[language];
    if (solution) $('#solution-explanation').textContent = solution.explanation[language];
  }
  async function loadProblem() {
    const slug = $('.workspace').dataset.problem;
    try {
      currentProblem = await api('/api/questions/' + slug + '/');
      renderProblemLanguage();
      $('#problem-badges').append(badge(currentProblem.level), el('span', currentProblem.topic, 'muted'));
      if (currentProblem.solved) $('#problem-badges').append(el('span', '✓ Solved', 'result-status-pass'));
      $('#sql-editor').value = currentProblem.draft ?? currentProblem.starter;
      currentProblem.schema.forEach(table => { const card = el('section', undefined, 'schema-card'); const title = el('div', undefined, 'schema-name'); title.append(el('span', table.name), el('small', table.row_count + ' rows')); card.append(title, dataTable(table.columns.map(c => c[0]), table.rows, table.columns.map(c => c[1]))); $('#schema-list').append(card); });
      const list = await api('/api/questions/'); const index = list.questions.findIndex(q => q.id === slug); const next = list.questions[index + 1];
      if (next) $('#next-problem').href = '/problems/' + next.id + '/'; else $('#next-problem').textContent = 'Back to question bank →';
    } catch (error) { $('#problem-title').textContent = 'Could not load this problem'; $('#problem-prompt').textContent = error.message; }
  }
  function saveDraft() {
    draftTimer = null;
    if (!authenticated || !currentProblem) return Promise.resolve();
    const sql = $('#sql-editor').value;
    const sequence = ++draftSequence;
    $('#save-status').textContent = 'Saving draft…';
    draftChain = draftChain.catch(() => {}).then(() => api('/api/questions/' + currentProblem.id + '/draft/', {sql})).then(() => {
      if (sequence === draftSequence) $('#save-status').textContent = 'Draft saved to your account';
    }).catch(error => { if (sequence === draftSequence) $('#save-status').textContent = error.message; });
    return draftChain;
  }
  async function run(mode) {
    if (!currentProblem || busy) return;
    if (!authenticated) { window.location.assign('/accounts/login/?next=' + encodeURIComponent(window.location.pathname)); return; }
    busy = true; $('#run').disabled = true; $('#submit').disabled = true; $('#sql-editor').readOnly = true;
    clearTimeout(draftTimer); await draftChain;
    $('#result-status').textContent = mode === 'submit' ? 'Checking test datasets…' : 'Running query…';
    $('#result-status').className = '';
    try {
      const data = await api('/api/questions/' + currentProblem.id + '/run/', {sql: $('#sql-editor').value, mode});
      const output = $('#results'); output.className = 'results'; output.replaceChildren();
      $('#result-status').textContent = (mode === 'submit' ? (data.accepted ? 'Accepted · ' : 'Try again · ') : (data.accepted ? 'Public test passed · ' : 'Public test differs · ')) + data.tests_passed + '/' + data.tests_total + ' tests';
      $('#result-status').className = data.accepted ? 'result-status-pass' : 'result-status-fail';
      output.append(el('p', 'Your output · ' + data.actual.rows.length + ' rows', 'result-label'), dataTable(data.actual.columns, data.actual.rows));
      if (!data.accepted) output.append(el('p', 'Expected output on the public dataset', 'result-label'), dataTable(data.expected.columns, data.expected.rows));
      if (mode === 'submit' && data.accepted && !currentProblem.solved) { currentProblem.solved = true; $('#problem-badges').append(el('span', '✓ Solved', 'result-status-pass')); }
      $('#save-status').textContent = 'Draft saved to your account';
    } catch (error) { $('#results').className = 'results'; $('#results').replaceChildren(el('p', error.message, 'error-box')); $('#result-status').textContent = 'Query could not complete'; $('#result-status').className = 'result-status-fail'; }
    finally { busy = false; $('#run').disabled = false; $('#submit').disabled = false; $('#sql-editor').readOnly = false; }
  }
  languageSelect.addEventListener('change', () => { language = languageSelect.value; try { localStorage.setItem('sqlcraft-language', language); } catch (_) {} renderQuestions(); renderProblemLanguage(); if ($('#progress-content')) loadProgress(); });
  if (document.body.dataset.page === 'home') {
    api('/api/questions/').then(data => { questions = data.questions; renderQuestions(); return loadProgress(); }).catch(error => { $('#list-message').textContent = error.message; $('#problem-count').textContent = 'Could not load'; });
    $('#search').addEventListener('input', renderQuestions); $('#status-filter').addEventListener('change', renderQuestions);
    document.querySelectorAll('[data-level]').forEach(button => button.addEventListener('click', () => { setLevel(button.dataset.level); if (button.classList.contains('path-link')) $('#practice').scrollIntoView(); }));
    const reset = $('#reset-progress');
    if (reset) reset.addEventListener('click', () => {
      if ($('.reset-confirm')) return;
      const box = el('div', undefined, 'reset-confirm'); box.append(el('p', 'Delete your drafts and submission history? This cannot be undone.'));
      const confirm = el('button', 'Delete my progress', 'button subtle small'); const cancel = el('button', 'Keep my progress', 'button subtle small');
      confirm.addEventListener('click', async () => { confirm.disabled = true; try { await api('/api/progress/delete/', {}); box.remove(); await loadProgress(); } catch (error) { box.append(el('p', error.message)); confirm.disabled = false; } });
      cancel.addEventListener('click', () => box.remove()); box.append(confirm, cancel); $('#progress-content').before(box);
    });
  }
  if (document.body.dataset.page === 'problem') {
    loadProblem();
    $('#sql-editor').addEventListener('input', () => { if (!authenticated) return; clearTimeout(draftTimer); $('#save-status').textContent = 'Unsaved changes'; draftTimer = setTimeout(saveDraft, 1200); });
    $('#sql-editor').addEventListener('keydown', event => { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); run('run'); } });
    $('#run').addEventListener('click', () => run('run')); $('#submit').addEventListener('click', () => run('submit'));
    $('#reveal-solution').addEventListener('click', async () => { if (!currentProblem) return; if (!authenticated) { window.location.assign('/accounts/login/?next=' + encodeURIComponent(window.location.pathname)); return; } try { solution = await api('/api/questions/' + currentProblem.id + '/solution/', {}); $('#solution-explanation').textContent = solution.explanation[language]; $('#solution-sql').textContent = solution.sql; $('#solution-content').hidden = false; $('#reveal-solution').textContent = 'Explained solution'; } catch (error) { $('#save-status').textContent = error.message; } });
    window.addEventListener('beforeunload', event => { if (authenticated && (draftTimer || busy) && $('#save-status').textContent !== 'Draft saved to your account') { event.preventDefault(); event.returnValue = ''; } });
  }
})();
