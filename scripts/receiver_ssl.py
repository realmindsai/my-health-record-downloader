# ABOUTME: HTTPS relay server for My Health Record PDF downloads.
# ABOUTME: Accepts POSTed PDF blobs from browser JS and saves them to ~/Downloads/medical_records/.

import ssl
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

SAVE_DIR = os.path.expanduser('~/Downloads/medical_records')

class FileReceiver(BaseHTTPRequestHandler):
    """Receives binary file data via POST and saves to SAVE_DIR.

    The browser fetches PDFs from the My Health Record portal,
    then POSTs the blob to this server. This avoids Chrome's
    programmatic download blocking.

    Headers:
        X-Filename: desired filename for the saved file
    Body:
        Raw binary file data (application/octet-stream)
    """

    def do_OPTIONS(self):
        """Handle CORS preflight for cross-origin requests from portal."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Filename')
        self.end_headers()

    def do_POST(self):
        """Receive file data and save to disk."""
        filename = self.headers.get('X-Filename', 'unknown.pdf')
        filename = os.path.basename(filename)  # security: strip path components
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        os.makedirs(SAVE_DIR, exist_ok=True)
        filepath = os.path.join(SAVE_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(body)

        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        resp = json.dumps({'saved': filename, 'size': len(body)})
        self.wfile.write(resp.encode())
        print(f'Saved: {filename} ({len(body)} bytes)')

    def log_message(self, format, *args):
        print(f'[relay] {args[0]}')


def find_mkcert_certs():
    """Locate mkcert certificate files in /tmp."""
    cert = '/tmp/localhost+2.pem'
    key = '/tmp/localhost+2-key.pem'
    if os.path.exists(cert) and os.path.exists(key):
        return cert, key

    # Try generating them
    print('mkcert certificates not found in /tmp.')
    print('Run: cd /tmp && mkcert localhost 127.0.0.1 ::1')
    raise FileNotFoundError(
        f'Expected {cert} and {key}. '
        'Generate with: cd /tmp && mkcert localhost 127.0.0.1 ::1'
    )


if __name__ == '__main__':
    cert, key = find_mkcert_certs()

    server = HTTPServer(('127.0.0.1', 9877), FileReceiver)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert, key)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)

    print(f'HTTPS relay server on https://127.0.0.1:9877')
    print(f'Saving files to {SAVE_DIR}')
    print('Press Ctrl+C to stop')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServer stopped.')
