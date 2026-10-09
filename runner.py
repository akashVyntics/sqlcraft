"""Private runner service. Deploy separately, with no application DB credentials."""
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
from practice.judge import execute_local

TOKEN = os.environ.get('SQL_RUNNER_TOKEN', '')
if len(TOKEN) < 32:
    raise RuntimeError('Set a strong SQL_RUNNER_TOKEN of at least 32 characters.')
HANDLERS = threading.BoundedSemaphore(4)

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, value):
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        self.connection.settimeout(12)
        if self.path != '/execute' or not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + TOKEN):
            self.reply(403, {'error': 'Forbidden.'})
            return
        if not HANDLERS.acquire(blocking=False):
            self.reply(429, {'error': 'Runner is busy.'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > 32768:
                raise ValueError('Invalid request size.')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('Invalid request.')
            seeds = payload.get('seeds', [0])
            if seeds not in ([0], [0, 7, 22]):
                raise ValueError('Invalid dataset selection.')
            self.reply(200, {'results': execute_local(payload.get('sql'), seeds)})
        except (ValueError, TypeError) as error:
            self.reply(400, {'error': str(error)})
        except Exception:
            self.reply(500, {'error': 'Runner unavailable.'})
        finally:
            HANDLERS.release()

    def log_message(self, format, *args):
        pass  # Do not log headers or learner SQL.

if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 9000), Handler).serve_forever()
