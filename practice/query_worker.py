"""Disposable SQL process. Never connects to the application database."""
import json
import resource
import sys
from datetime import date, datetime
from decimal import Decimal
import duckdb
from fixtures import populate

def normalize(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)

def execute(sql, seed):
    connection = duckdb.connect(':memory:', config={'enable_external_access': 'false', 'threads': '1', 'memory_limit': '64MB', 'max_temp_directory_size': '0B'})
    try:
        populate(connection, seed)
        connection.execute('SET lock_configuration = true')
        cursor = connection.execute(sql)
        columns = [item[0] for item in cursor.description]
        rows = cursor.fetchmany(201)
        if len(rows) > 200 or len(columns) > 30:
            raise ValueError('Result exceeds practice limits.')
        result = {'columns': columns, 'rows': [[normalize(v) for v in row] for row in rows]}
        if len(json.dumps(result)) > 100000:
            raise ValueError('Result too large.')
        return result
    finally:
        connection.close()

if __name__ == '__main__':
    resource.setrlimit(resource.RLIMIT_CPU, (4, 4))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    try:
        payload = json.load(sys.stdin)
        print(json.dumps({'results': [execute(payload['sql'], seed) for seed in payload['seeds']]}, allow_nan=False))
    except Exception:
        print(json.dumps({'error': 'Query could not run. Check column names, types and syntax, or simplify the query.'}))
