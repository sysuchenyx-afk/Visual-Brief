#!/usr/bin/env python3
"""Serve one offline brief at a localhost URL; no external dependencies."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path, help='HTML file or directory containing HTML')
    parser.add_argument('--port', type=int, default=0, help='Default: let the system choose an available port')
    args = parser.parse_args()
    path = args.path.resolve()
    if path.is_dir():
        options = sorted(path.glob('*.html'))
        if (path / 'index.html').is_file():
            path = path / 'index.html'
        elif len(options) == 1:
            path = options[0]
        else:
            parser.error('Directory does not contain a unique HTML file; specify a particular file')
    if not path.is_file() or path.suffix.lower() != '.html':
        parser.error('Specify an existing HTML file')

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.split('?', 1)[0] not in ('/', '/index.html', '/' + path.name):
                self.send_error(404)
                return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError as e:
        parser.error(str(e))
    print(f'Open in a browser: http://127.0.0.1:{server.server_port}/', flush=True)
    print(f'File: {path}\nStop: Ctrl+C', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
