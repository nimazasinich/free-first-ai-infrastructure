#!/usr/bin/env python3
"""Minimal on-host probes. Print status and timings without credentials or bodies."""
import argparse
import json
from pathlib import Path
import sqlite3
import time
import urllib.error
import urllib.request


MODEL = "gemini-3.8-flash"
PILOT_MODEL = "gemini-3.5-flash-lite"
MODELS = frozenset({MODEL, PILOT_MODEL})


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def local_state(root):
    with sqlite3.connect(f"file:{root / 'data/db/data.sqlite'}?mode=ro", uri=True) as db:
        rows = db.execute("SELECT isActive, data FROM providerConnections").fetchall()
        if len(rows) != 1 or rows[0][0] != 1:
            raise RuntimeError("Expected one active provider")
        if db.execute("SELECT count(*) FROM combos").fetchone()[0] != 0:
            raise RuntimeError("Unexpected gateway combos")
        provider = json.loads(rows[0][1])
        config = provider["providerSpecificData"]
        if config["prefix"] != "free" or config["baseUrl"] != "http://172.20.0.1:20230/v1":
            raise RuntimeError("Unexpected provider")
        return provider["apiKey"], (root / "canary.key").read_text().strip()


def request(base, path, key=None, body=None, method=None):
    headers = {"Accept-Encoding": "identity"}
    if key is not None:
        headers["Authorization"] = f"Bearer {key}"
    if body is not None:
        headers["Content-Type"] = "application/json"
        if "stream" in body:
            headers["Accept"] = "text/event-stream" if body["stream"] else "application/json"
    req = urllib.request.Request(
        base + path,
        headers=headers,
        data=None if body is None else json.dumps(body).encode(),
        method=method,
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        return opener.open(req, timeout=100)
    except urllib.error.HTTPError as error:
        return error


def stream(base, key, model, responses=False, max_tokens=256):
    path = "/v1/responses" if responses else "/v1/chat/completions"
    prompt = "Write one complete sentence about the colors of a rainbow."
    body = {"model": model, "stream": True, "temperature": 0.2}
    if responses:
        body.update(input=prompt, max_output_tokens=max_tokens)
    else:
        body.update(messages=[{"role": "user", "content": prompt}], max_tokens=max_tokens)
    started = time.monotonic()
    with request(base, path, key, body) as reply:
        first_headers = time.monotonic()
        content_type = reply.headers.get_content_type()
        first_event = first_content = last_content = None
        events = content_events = 0
        done = failed = False
        finish = None
        response_models = set()
        if reply.status == 200 and content_type == "text/event-stream":
            for line in reply:
                if not line.startswith(b"data:"):
                    continue
                current = time.monotonic()
                if first_event is None:
                    first_event = current
                events += 1
                data = line[5:].strip()
                if data == b"[DONE]":
                    if not responses:
                        done = True
                    continue
                if not data:
                    continue
                event = json.loads(data)
                event_type = event.get("type")
                reported_model = event.get("model") or (event.get("response") or {}).get("model")
                if isinstance(reported_model, str):
                    response_models.add(reported_model)
                if event.get("error") or event_type in (
                    "error", "response.failed", "response.incomplete", "response.cancelled",
                ):
                    failed = True
                    finish = event_type or "error"
                choice = (event.get("choices") or [{}])[0]
                content = choice.get("delta", {}).get("content")
                if event_type == "response.output_text.delta":
                    content = event.get("delta")
                if content:
                    if first_content is None:
                        first_content = current
                    last_content = current
                    content_events += 1
                finish = choice.get("finish_reason") or finish
                if event_type == "response.completed":
                    done = True
                    finish = event_type
        ended = time.monotonic()
        return {
            "status": reply.status,
            "content_type": content_type,
            "headers_ms": round((first_headers - started) * 1000),
            "first_event_ms": None if first_event is None else round((first_event - started) * 1000),
            "first_content_ms": None if first_content is None else round((first_content - started) * 1000),
            "content_span_ms": None if last_content is None else round((last_content - first_content) * 1000),
            "total_ms": round((ended - started) * 1000),
            "events": events,
            "content_events": content_events,
            "complete": done and not failed and (
                responses or finish in ("stop", "length", "tool_calls", "function_call")
            ),
            "response_models": sorted(response_models),
            "finish": finish,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/opt/9router-clean"))
    parser.add_argument("--public-url", required=True)
    parser.add_argument("--responses", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--model", choices=("production", "pilot"), default="production")
    args = parser.parse_args()
    upstream_key, canary_key = local_state(args.root)
    model = PILOT_MODEL if args.model == "pilot" else MODEL
    alias = "free/" + model
    key = canary_key
    if args.model == "pilot":
        key = (args.root / "client-keys" / "pilot-lite.key").read_text().strip()
    for label, base, auth, target in (
        ("direct", "http://127.0.0.1:2048", upstream_key, model),
        ("gateway_https", args.public_url, key, alias),
    ):
        result = stream(base, auth, target, args.responses, args.max_tokens)
        print(json.dumps({"path": label, "model": target, **result}), flush=True)


if __name__ == "__main__":
    main()
