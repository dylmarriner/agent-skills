#!/usr/bin/env python3
"""Verify every server configured in ~/.pi/agent/pi-lsp.json.

Spawning alone proves nothing: a server can start, answer `initialize`, and still deliver zero
diagnostics because the client never answered its requests. So this script is a real LSP client.

Tier 1 (asserted for all): the configured command spawns and answers `initialize`.
Tier 2 (asserted for A_GRADED): a generated file with a known defect produces diagnostics.

Run: python3 scripts/lsp_check.py
"""
import json
import pathlib
import queue
import subprocess
import threading
import time

CFG = pathlib.Path.home() / ".pi/agent/pi-lsp.json"
SAMPLES = pathlib.Path(__file__).resolve().parent / "samples"

# Servers that publish diagnostics on didOpen without a build context.
A_GRADED = {"pylsp", "clangd", "biome"}

SAMPLE_BODY = {
    "py": 'def f():\n    return undefined_thing + 1\n',
    "ts": 'const x: number = "str"\nconst y = ;\n',
    "cpp": 'int main() { return undefined_symbol; }\n',
    "go": 'package main\nfunc main() { _ = undefinedThing }\n',
    "rs": 'fn main() { let x: i32 = "s"; }\n',
    "asm": 'section .text\nglobal _start\n_start:\n    mov rax, nonsense_thing\n',
}

LANG_ID = {
    "py": "python", "pyi": "python", "ts": "typescript", "tsx": "typescriptreact",
    "js": "javascript", "jsx": "javascriptreact", "mjs": "javascript", "cjs": "javascript",
    "mts": "typescript", "cts": "typescript", "json": "json", "jsonc": "json", "css": "css",
    "c": "c", "h": "c", "hpp": "cpp", "cpp": "cpp", "go": "go", "rs": "rust",
    "asm": "asm", "s": "asm",
}


def ensure_samples():
    SAMPLES.mkdir(exist_ok=True)
    for ext, body in SAMPLE_BODY.items():
        f = SAMPLES / f"sample.{ext}"
        if not f.exists():
            f.write_text(body)


def handshake(entry, sample, lang, wait=25):
    proc = subprocess.Popen(entry["command"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, cwd=str(sample.parent))
    q = queue.Queue()

    def send(msg):
        body = json.dumps(msg).encode()
        proc.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        proc.stdin.flush()

    def reader():
        try:
            while True:
                n = 0
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        return
                    if line in (b"\r\n", b"\n"):
                        break
                    if line.lower().startswith(b"content-length:"):
                        n = int(line.split(b":")[1])
                q.put(json.loads(proc.stdout.read(n)))
        except Exception:
            return

    threading.Thread(target=reader, daemon=True).start()
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"processId": None, "rootUri": sample.parent.as_uri(), "capabilities": {}}})

    initialized, diags, t0 = False, None, time.time()
    try:
        while time.time() - t0 < wait:
            try:
                msg = q.get(timeout=wait - (time.time() - t0))
            except queue.Empty:
                break
            if not initialized and msg.get("result", {}).get("capabilities"):
                initialized = True
                send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
                send({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {"textDocument": {
                    "uri": sample.as_uri(), "languageId": lang, "version": 1,
                    "text": sample.read_text()}}})
            elif "method" in msg and "id" in msg:
                # Server -> client request. Biome blocks here until it is answered.
                result = [None] if msg["method"] == "workspace/configuration" else None
                send({"jsonrpc": "2.0", "id": msg["id"], "result": result})
            elif msg.get("method") == "textDocument/publishDiagnostics" and msg["params"]["diagnostics"]:
                diags = msg["params"]["diagnostics"]
                break
    finally:
        proc.kill()
    return initialized, diags


def main():
    ensure_samples()
    servers = json.loads(CFG.read_text())["servers"]
    failures = []
    for sid, entry in servers.items():
        exts = [e.lstrip(".") for e in entry.get("extensions", [])]
        ext = next((e for e in exts if (SAMPLES / f"sample.{e}").exists()), None)
        if ext is None:
            print(f"{sid:28} SKIP (no sample.{'/'.join(exts)})")
            continue
        ok, diags = handshake(entry, SAMPLES / f"sample.{ext}", LANG_ID.get(ext, ext))
        if not ok:
            print(f"{sid:28} FAIL  did not initialize")
            failures.append(f"{sid}: no initialize response")
        elif sid in A_GRADED and not diags:
            print(f"{sid:28} FAIL  initialized but published no diagnostics")
            failures.append(f"{sid}: no diagnostics")
        else:
            first = diags[0]["message"][:60] if diags else "(quiet, expected for this server)"
            print(f"{sid:28} OK    diagnostics={len(diags) if diags else 0} {first}")
    print()
    assert not failures, "FAILED: " + "; ".join(failures)
    print("ALL SERVERS OK")


if __name__ == "__main__":
    main()
