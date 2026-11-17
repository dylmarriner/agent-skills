#!/usr/bin/env python3
"""OpenAI-compatible stub server for offline agent-CLI plumbing checks.

Answers POST /v1/chat/completions with a fixed reply and logs every request
body to --log so you can see what the CLI actually sent.

    python3 fake_openai_stub.py --port 8899 --log /tmp/req.log &
    OPENAI_BASE_URL=http://127.0.0.1:8899/v1 OPENAI_API_KEY=x \
      myagent -p "hi"
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

REPLY = 'OK'


class Handler(BaseHTTPRequestHandler):
    log_path = '/tmp/fake_openai_stub.log'

    def log_message(self, *args):  # silence per-request stderr noise
        pass

    def do_POST(self):
        n = int(self.headers.get('content-length') or 0)
        body = self.rfile.read(n)
        with open(self.log_path, 'ab') as fh:
            fh.write(self.path.encode() + b'\n' + body[:4000] + b'\n---\n')
        payload = {
            'id': 'chatcmpl-stub',
            'object': 'chat.completion',
            'created': 0,
            'model': 'stub-model',
            'choices': [{
                'index': 0,
                'message': {'role': 'assistant', 'content': REPLY},
                'finish_reason': 'stop',
            }],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 1, 'total_tokens': 11},
        }
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('content-type', 'application/json')
        self.send_header('content-length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8899)
    ap.add_argument('--log', default='/tmp/fake_openai_stub.log')
    args = ap.parse_args()
    Handler.log_path = args.log
    HTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
