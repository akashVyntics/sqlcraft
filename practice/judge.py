import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import sqlglot
from sqlglot import exp
from .fixtures import SCHEMA

class RunnerUnavailable(ValueError):
    """An infrastructure failure that must not be graded as a learner failure."""


def checked_results(payload, seeds):
    if not isinstance(payload, dict):
        raise RunnerUnavailable('The query runner returned an invalid response.')
    if payload.get('error'):
        if not isinstance(payload['error'], str):
            raise RunnerUnavailable('The query runner returned an invalid response.')
        raise ValueError(payload['error'][:300])
    results = payload.get('results')
    if not isinstance(results, list) or len(results) != len(seeds):
        raise RunnerUnavailable('The query runner returned incomplete test results.')
    for result in results:
        if not isinstance(result, dict):
            raise RunnerUnavailable('The query runner returned an invalid result.')
        columns, rows = result.get('columns'), result.get('rows')
        if (not isinstance(columns, list) or not 1 <= len(columns) <= 30
                or not all(isinstance(column, str) for column in columns)
                or not isinstance(rows, list) or len(rows) > 200):
            raise RunnerUnavailable('The query runner returned an invalid result.')
        for row in rows:
            if not isinstance(row, list) or len(row) != len(columns):
                raise RunnerUnavailable('The query runner returned an invalid row.')
            for value in row:
                if value is not None and not isinstance(value, (str, int, float, bool)):
                    raise RunnerUnavailable('The query runner returned an invalid value.')
                if isinstance(value, float) and not math.isfinite(value):
                    raise RunnerUnavailable('The query runner returned a non-finite number.')
        if len(json.dumps(result)) > 100000:
            raise RunnerUnavailable('The query runner returned an oversized result.')
    return results


SLOTS = threading.BoundedSemaphore(2)
WORKER = Path(__file__).with_name('query_worker.py')

def validate_sql(sql):
    if not isinstance(sql, str) or not sql.strip() or len(sql) > 12000:
        raise ValueError('Write a query between 1 and 12,000 characters.')
    try:
        statements = sqlglot.parse(sql, read='duckdb')
    except (sqlglot.errors.ParseError, sqlglot.errors.TokenError, RecursionError):
        raise ValueError('SQL syntax could not be parsed. Use the DuckDB dialect.')
    if len(statements) != 1 or not isinstance(statements[0], (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise ValueError('Use one SELECT query, optionally with CTEs. Mutating statements are not supported.')
    root = statements[0]
    forbidden = (exp.Into, exp.Command, exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter)
    if any(isinstance(node, forbidden) for node in root.walk()):
        raise ValueError('Only read-only SELECT queries are supported.')
    ctes = {cte.alias_or_name.lower() for cte in root.find_all(exp.CTE)}
    for table in root.find_all(exp.Table):
        if not isinstance(table.this, exp.Identifier) or table.catalog or table.db:
            raise ValueError('File access, table functions and external databases are not supported.')
        if table.name.lower() not in set(SCHEMA) | ctes:
            raise ValueError('Use the tables listed in the problem schema.')
    for function in root.find_all(exp.Anonymous):
        if function.name.lower() not in {'date_trunc', 'datediff', 'date_diff', 'strftime', 'strptime', 'try_strptime', 'greatest', 'least', 'median', 'quantile_cont', 'epoch', 'isfinite'}:
            raise ValueError(f'Function {function.name} is not supported in this practice sandbox.')
    return sql

def execute_sql(sql, seeds=(0,)):
    validate_sql(sql)
    runner_url = os.getenv('SQL_RUNNER_URL', '')
    runner_token = os.getenv('SQL_RUNNER_TOKEN', '')
    if runner_url and runner_token:
        request = Request(runner_url.rstrip('/') + '/execute', data=json.dumps({'sql': sql, 'seeds': list(seeds)}).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + runner_token}, method='POST')
        try:
            with urlopen(request, timeout=10) as response:
                raw = response.read(320001)
                if len(raw) > 320000:
                    raise RunnerUnavailable('The query runner response is too large.')
                payload = json.loads(raw)
        except HTTPError as error:
            if error.code == 400:
                try:
                    payload = json.loads(error.read(32768))
                except (ValueError, UnicodeDecodeError):
                    raise RunnerUnavailable('The query runner is unavailable. Try again shortly.')
                if isinstance(payload, dict) and isinstance(payload.get('error'), str):
                    raise ValueError(payload['error'][:300])
            raise RunnerUnavailable('The query runner is unavailable or busy. Try again shortly.')
        except (URLError, TimeoutError, ValueError, UnicodeDecodeError):
            raise RunnerUnavailable('The query runner is unavailable. Try again shortly.')
        return checked_results(payload, seeds)
    if os.getenv('DJANGO_DEBUG', '').lower() != 'true':
        raise RunnerUnavailable('The isolated query runner must be configured before production use.')
    return execute_local(sql, seeds)

def execute_local(sql, seeds=(0,)):
    validate_sql(sql)
    if not SLOTS.acquire(blocking=False):
        raise RunnerUnavailable('The query runner is busy. Try again shortly.')
    try:
        child_env = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'}
        try:
            result = subprocess.run([sys.executable, '-B', str(WORKER)], input=json.dumps({'sql': sql, 'seeds': seeds}), text=True, capture_output=True, timeout=8, env=child_env, cwd='/tmp')
        except subprocess.TimeoutExpired:
            raise ValueError('Query timed out. Simplify the query and try again.')
        if result.returncode:
            raise ValueError('Query exceeded a resource limit or could not run.')
        try:
            payload = json.loads(result.stdout)
        except (ValueError, TypeError):
            raise ValueError('Query could not run.')
        return checked_results(payload, seeds)
    finally:
        SLOTS.release()

def same_result(actual, expected):
    if actual['columns'] != expected['columns'] or len(actual['rows']) != len(expected['rows']):
        return False
    for arow, erow in zip(actual['rows'], expected['rows']):
        if len(arow) != len(erow):
            return False
        for a, e in zip(arow, erow):
            if isinstance(a, bool) != isinstance(e, bool):
                return False
            if isinstance(a, (int, float)) and isinstance(e, (int, float)):
                if not math.isclose(a, e, rel_tol=1e-9, abs_tol=1e-6):
                    return False
            elif a != e:
                return False
    return True
