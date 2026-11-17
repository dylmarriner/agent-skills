#!/usr/bin/env python3
"""Single-flow PKCE login for an OAuth-protected remote MCP server in Hermes.

Use when `hermes mcp login <name> --flow browser` dies with
`[Errno 98] Address already in use` (it runs the flow twice in one process and
re-binds its own callback port). This runs one listener, one bind, one token
exchange, and writes Hermes' token file directly.

  python3 oauth_pkce_login.py <server-name>

Reads the client that `hermes mcp add <name> --url <url> --auth oauth` already
registered (`$HERMES_HOME/mcp-tokens/<name>.client.json`) and the server URL from
`$HERMES_HOME/config.yaml`, so nothing needs retyping.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import pathlib
import re
import secrets
import socketserver
import sys
import threading
import urllib.parse
import urllib.request

TIMEOUT = 900


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def server_url(config: pathlib.Path, name: str) -> str:
    """Lazy YAML-free read of mcp_servers.<name>.url (avoids a pyyaml dependency)."""
    lines = config.read_text().splitlines()
    for i, line in enumerate(lines):
        if re.fullmatch(r"\s{2}%s:\s*" % re.escape(name), line):
            for follow in lines[i + 1:i + 12]:
                m = re.match(r"\s+url:\s*(\S+)", follow)
                if m:
                    return m.group(1).strip('"\'')
                if re.match(r"\s{2}\S", follow):
                    break
    raise SystemExit(f"no mcp_servers.{name}.url in {config}")


def metadata(issuer: str) -> dict:
    req = urllib.request.Request(
        f"{issuer}/.well-known/oauth-authorization-server",
        headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def post(url: str, form: dict) -> dict:
    req = urllib.request.Request(
        url, data=urllib.parse.urlencode(form).encode(), method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="MCP server name as configured in Hermes")
    ap.add_argument("--hermes-home", default=str(pathlib.Path.home() / ".hermes"))
    ap.add_argument("--quiet", action="store_true", help="print only the URL")
    args = ap.parse_args()

    home = pathlib.Path(args.hermes_home)
    client_path = home / "mcp-tokens" / f"{args.name}.client.json"
    token_path = home / "mcp-tokens" / f"{args.name}.json"
    if not client_path.exists():
        raise SystemExit(
            f"no registered client at {client_path} — run "
            f"`hermes mcp add {args.name} --url <url> --auth oauth` first")

    client = json.loads(client_path.read_text())
    redirect_uri = client["redirect_uris"][0]
    port = urllib.parse.urlparse(redirect_uri).port or 27890
    resource = server_url(home / "config.yaml", args.name)
    parts = urllib.parse.urlparse(resource)
    issuer = client.get("issuer") or f"{parts.scheme}://{parts.netloc}"
    md = metadata(issuer)
    scope = client.get("scope") or " ".join(md.get("scopes_supported", []))

    verifier = secrets.token_urlsafe(64)
    challenge = b64(hashlib.sha256(verifier.encode()).digest())
    state = secrets.token_urlsafe(32)
    got: dict = {}
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update(q)
            ok = bool(q.get("code")) and q.get("state", [""])[0] == state
            body = b"Authorized. Close this tab." if ok else b"State mismatch or missing code."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            done.set()

    class Server(socketserver.TCPServer):
        allow_reuse_address = True

    url = md["authorization_endpoint"] + "?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client["client_id"],
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "resource": resource,
        "scope": scope,
    })

    with Server(("127.0.0.1", port), Handler) as httpd:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        if not args.quiet:
            print(f"LISTENING on 127.0.0.1:{port}", flush=True)
        print(url, flush=True)
        if not done.wait(TIMEOUT):
            print(f"TIMEOUT: no callback within {TIMEOUT}s", file=sys.stderr)
            return 1

    if got.get("state", [""])[0] != state:
        print("STATE MISMATCH — aborting", file=sys.stderr)
        return 1
    if "code" not in got:
        print(f"provider error: {got}", file=sys.stderr)
        return 1

    tok = post(md["token_endpoint"], {
        "grant_type": "authorization_code",
        "code": got["code"][0],
        "redirect_uri": redirect_uri,
        "client_id": client["client_id"],
        "client_secret": client.get("client_secret", ""),
        "code_verifier": verifier,
        "resource": resource,
    })
    assert tok.get("access_token"), f"no access_token in token response: {sorted(tok)}"
    assert tok.get("refresh_token"), "no refresh_token — Hermes cannot refresh without one"

    token_path.write_text(json.dumps({
        "access_token": tok["access_token"],
        "token_type": tok.get("token_type", "Bearer"),
        "expires_in": tok.get("expires_in", 3600),
        "scope": tok.get("scope", scope),
        "refresh_token": tok["refresh_token"],
    }, indent=2))
    token_path.chmod(0o600)
    print(f"TOKENS WRITTEN: {token_path} (expires_in={tok.get('expires_in')}, refresh present)")
    print(f"next: hermes mcp test {args.name} && "
          f"hermes config set mcp_servers.{args.name}.enabled true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
