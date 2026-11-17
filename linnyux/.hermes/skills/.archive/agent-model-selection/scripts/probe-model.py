#!/usr/bin/env python3
"""Probe candidate models with a background-workload request shape before wiring them.

Background jobs (memory observers, summarisers, classifiers) send a fixed shape:
model, messages, temperature, max_tokens, stream=false. A model that rejects any
of those, or that answers with a reasoning trace instead of the expected marker,
is unusable no matter how good it looks on a leaderboard.

Usage:
  OPENROUTER_API_KEY=... python3 probe-model.py \
      --endpoint https://openrouter.ai/api/v1 \
      --key-env OPENROUTER_API_KEY \
      --marker '<observation>' \
      --model vendor/model-a:free --model vendor/model-b:free

  # an endpoint that needs no key
  python3 probe-model.py --endpoint http://127.0.0.1:8081/v1 --model local.gguf

Exits non-zero when no model passed, so it can gate a swap.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_PROMPT = (
    "Summarise the following tool use as a single structured record.\n"
    "Reply with only this XML, nothing else:\n"
    "<observation>\n"
    "  <type>bugfix|feature|refactor|discovery|decision|change</type>\n"
    "  <title>short title</title>\n"
    "  <subtitle>one concrete line</subtitle>\n"
    "  <narrative>two sentences</narrative>\n"
    "</observation>\n\n"
    "Tool: Bash\n"
    'Input: {"command": "npm test -- http-client"}\n'
    'Output: PASS src/http/client.test.ts\n  4 passed\n'
    "  retry wrapper attempts 3 times on 503 then throws HttpClientError\n"
)

# Phrases a thinking model emits into `content` instead of the answer.
REASONING_MARKERS = (" thinking", "<think", "thinking process", "Here's a thinking")


def chat_url(endpoint: str) -> str:
    base = endpoint.rstrip("/")
    # Tolerate a base that already names the completion path.
    return base if base.endswith("/chat/completions") else base + "/chat/completions"


def probe(endpoint: str, model: str, api_key: str, prompt: str,
          temperature: float, max_tokens: int, marker: str, timeout: int) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    request = urllib.request.Request(
        chat_url(endpoint), data=json.dumps(body).encode(), headers=headers)

    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:200].replace("\n", " ")
        return {"model": model, "ok": False, "why": "HTTP %s %s" % (exc.code, detail)}
    except Exception as exc:  # noqa: BLE001 - a probe reports whatever happened
        return {"model": model, "ok": False, "why": str(exc)[:200]}
    elapsed = round(time.time() - started, 1)

    try:
        text = payload["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return {"model": model, "ok": False,
                "why": "no choices/message/content in response"}

    usage = payload.get("usage") or {}
    completion = usage.get("completion_tokens") or 0
    result = {
        "model": model,
        "ok": False,
        "elapsed_s": elapsed,
        "completion_tokens": completion,
        "tok_per_s": round(completion / elapsed, 1) if completion and elapsed else None,
        "chars": len(text),
        "head": text.strip().splitlines()[0][:80] if text.strip() else "(empty)",
    }

    lowered = text.lower()
    if not text.strip():
        result["why"] = "empty content with HTTP 200"
    elif any(m in lowered for m in REASONING_MARKERS):
        result["why"] = "leaked a reasoning trace instead of the answer"
    elif marker and marker not in text:
        result["why"] = "missing expected marker %r" % marker
    else:
        result["ok"] = True
        result.pop("why", None)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--endpoint", required=True,
                        help="OpenAI-shaped base URL, e.g. https://openrouter.ai/api/v1")
    parser.add_argument("--model", action="append", required=True,
                        help="model id; repeat for each candidate")
    parser.add_argument("--key-env", default="",
                        help="env var holding the API key; omit for a local endpoint")
    parser.add_argument("--marker", default="<observation>",
                        help="substring the reply must contain ('' to skip)")
    parser.add_argument("--temperature", type=float, default=0.3,
                        help="send the temperature the real caller uses (default 0.3)")
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--prompt-file", default="",
                        help="use this prompt instead of the built-in observer prompt")
    args = parser.parse_args()

    api_key = os.environ.get(args.key_env, "") if args.key_env else ""
    if args.key_env and not api_key:
        print("error: %s is not set" % args.key_env, file=sys.stderr)
        return 2

    prompt = args.prompt_file and open(args.prompt_file).read() or DEFAULT_PROMPT

    passed = []
    for model in args.model:
        result = probe(args.endpoint, model, api_key, prompt,
                       args.temperature, args.max_tokens, args.marker, args.timeout)
        if result["ok"]:
            passed.append(model)
            print("PASS  %-46s %5ss %5s chars %6s tok/s  %s" % (
                model, result["elapsed_s"], result["chars"],
                result["tok_per_s"], result["head"]))
        else:
            print("FAIL  %-46s %s" % (model, result["why"]))

    print()
    if not passed:
        print("no candidate passed; do not wire any of these")
        return 1
    print("usable: %s" % ", ".join(passed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
