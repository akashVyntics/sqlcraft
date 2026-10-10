"""Real HTTP checks against a disposable runner with no application credentials."""
import json
import os
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from unittest.mock import patch
from practice.judge import execute_sql

TOKEN = 'ci-only-runner-fixture-token-not-a-real-secret-92817'
process = subprocess.Popen([sys.executable, 'runner.py'], env={
    'PATH': os.defpath, 'SQL_RUNNER_TOKEN': TOKEN, 'PYTHONDONTWRITEBYTECODE': '1',
}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def request(path, data=None, token=TOKEN):
    req = Request('http://127.0.0.1:9000' + path, data=None if data is None else json.dumps(data).encode(),
                  headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
    try:
        with urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


try:
    for _ in range(50):
        try:
            if request('/health') == (200, {'status': 'ok'}):
                break
        except (URLError, TimeoutError):
            time.sleep(0.1)
    else:
        raise AssertionError('Runner did not start')
    assert request('/health', token='wrong')[0] == 403
    assert request('/execute', {'sql': 'SELECT 1', 'seeds': [0]}, token='wrong')[0] == 403
    assert request('/execute', {'sql': 'SELECT 1', 'seeds': [99]})[0] == 400
    assert request('/execute', {'sql': 'DROP TABLE orders', 'seeds': [0]})[0] == 400
    assert request('/execute', {'sql': "SELECT * FROM read_csv('/etc/passwd')", 'seeds': [0]})[0] == 400
    with patch.dict(os.environ, {'SQL_RUNNER_URL': 'http://127.0.0.1:9000', 'SQL_RUNNER_TOKEN': TOKEN}):
        results = execute_sql('SELECT COUNT(*) AS order_count FROM orders', (0, 7, 22))
        assert [r['rows'][0][0] for r in results] == [17, 21, 20]
        try:
            execute_sql('SELECT missing_column FROM orders')
        except ValueError as error:
            assert 'unavailable' not in str(error)
        else:
            raise AssertionError('Invalid SQL unexpectedly succeeded')
    print('PASS: private runner HTTP auth, dataset rules, read-only SQL, three result sets and query errors')
finally:
    process.terminate()
    process.wait(timeout=10)
