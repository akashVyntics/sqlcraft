"""Dependency-free content checks and SQLite portability smoke checks.

This does NOT replace the DuckDB/Django integration suite.
"""
import sqlite3
from practice.fixtures import SCHEMA, dataset
from practice.questions import QUESTIONS, BY_ID

assert len(QUESTIONS) == len(BY_ID) == 40
for q in QUESTIONS:
    for field in ('title', 'prompt', 'hint', 'explanation'):
        assert set(q[field]) == {'en', 'hi'} and all(q[field].values()), (q['id'], field)
    assert q['ordered'] is True
    assert set(q['tables']) <= set(SCHEMA)
    assert q['solution'].strip()

smoke_checked = set()
for seed in (0, 7, 22):
    con = sqlite3.connect(':memory:')
    data = dataset(seed)
    for table, columns in SCHEMA.items():
        con.execute(f'CREATE TABLE {table} (' + ', '.join(f'{name} {kind}' for name, kind in columns) + ')')
        con.executemany(f'INSERT INTO {table} VALUES (' + ','.join('?' for _ in columns) + ')', data[table])
    for q in QUESTIONS:
        if q['id'] in {'february-orders', 'monthly-growth', 'first-purchase', 'late-arrivals'}:
            continue  # DuckDB-specific date syntax.
        cursor = con.execute(q['solution'])
        rows = cursor.fetchall()
        assert cursor.description and len(rows) <= 200, q['id']
        smoke_checked.add(q['id'])
    expected_total = sum(row[4] for row in data['orders'] if row[3] == 'completed')
    assert con.execute(BY_ID['revenue-total']['solution']).fetchone()[0] == expected_total
    assert len(con.execute(BY_ID['customer-revenue']['solution']).fetchall()) == len(data['customers'])
    states = {row[0]: row[2] for row in con.execute(BY_ID['payment-latest-state']['solution'])}
    assert states['pay_d'] == 'refunded' and states['pay_b'] == 'succeeded'
    for customer, region, start, end in con.execute(BY_ID['scd-history']['solution']):
        assert end is None or end > start
    con.close()
print(f'PASS: {len(QUESTIONS)} bilingual question records; {len(smoke_checked)} portable reference queries on three datasets; revenue, customer coverage, payment ties and SCD intervals.')
print('Not run: DuckDB execution, Django authentication/API integration, browser QA or hosted deployment.')
