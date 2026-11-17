#!/usr/bin/env python3
"""Probe an OpenAI-compatible chat endpoint with a caller's real request shape.

Use before wiring a model into an agent's background work. A model that answers
a generic chat prompt can still fail here: it may reject the caller's pinned
parameters, return an empty completion, or emit a reasoning trace instead of the
answer.

    python3 probe_chat_endpoint.py \
        --base-url https://openrouter.ai/api/v1 \
        --model some/model:free \
        --api-key-env OPENROUTER_API_KEY

    # several candidates at once
    python3 probe_chat_endpoint.py --base-url ... --model a --model b --model c

Prints per model: latency, token usage, whether the expected marker is present,
whether a thinking block leaked, and the raw reply. Exit status is 0 when at
least one model passes.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

# A structured-extraction prompt in the shape most background observers use.
PROMPT = (
    "Answer with only this XML and nothing else:\n"
    "<result>\n"
    "  <type>bugfix|feature|refactor|discovery|decision|change</type>\n"
    "  <title>short title</title>\n"
    "  <summary>two sentences</summary>\n"
    "</result>\n\n"
    "Tool: Bash\n"
    'Input: {"command": "npm test -- http-client"}\n'
    "Output: PASS src/http/client.test.ts\n  4 passed\n"
    "  retry wrapper attempts 3 times on 503 then throws HttpClientError\n"
)

# Optional extras the caller sends that a model may reject outright.
EXTRA_BODY = {"temperature": 0.3, "max_tokens": 700, "stream": False}

THINKING = re.compile(r"<think\b|\bthinking process\b", re.IGNORECASE)


def probe(base_url, model, key, marker, timeout):
    body = {"model": model, "messages": [{"role": "user", "content": PROMPT}]}
    body.update(EXTRA_BODY)
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers=headers,
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:200]
        print("%-46s FAIL http %s  %s" % (model, exc.code, detail))
        return False
    except Exception as exc:  # noqa: BLE001 - probe reports whatever happened
        print("%-46s FAIL %s" % (model, str(exc)[:120]))
        return False

    elapsed = time.time() - started
    try:
        text = payload["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        print("%-46s FAIL no content: %s" % (model, json.dumps(payload)[:140]))
        return False

    usage = payload.get("usage") or {}
    completion = usage.get("completion_tokens") or 0
    rate = round(completion / elapsed, 1) if completion and elapsed else None
    has_marker = marker in text
    leaked = bool(THINKING.search(text))
    ok = has_marker and not leaked

    print("%-46s %s %5.1fs %s tok/s marker=%s thinking=%s" % (
        model, "OK  " if ok else "WEAK", elapsed, rate, has_marker, leaked))
    print("    %s" % text.strip()[:200].replace("\n", " "))
    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", action="append", required=True)
    parser.add_argument("--api-key-env", default="")
    parser.add_argument("--marker", default="<result>")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    key = os.environ.get(args.api_key_env, "") if args.api_key_env else ""
    if args.api_key_env and not key:
        print("warning: %s is not set; sending unauthenticated" % args.api_key_env)

    passed = [m for m in args.model if probe(args.base_url, m, key, args.marker, args.timeout)]
    print()
    print("passed %d/%d" % (len(passed), len(args.model)))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
