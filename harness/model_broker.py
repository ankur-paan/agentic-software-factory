#!/usr/bin/env python3
"""
Central Model Broker: tracks reliability across free/multi-provider models.

Endpoints:
  GET /pick?exclude=a,b                     -> best available model (plain text)
  GET /report?model=m&ok=1|0&kind=k&who=w   -> record one run outcome
  GET /status                               -> JSON table of model scores

Standard library only.
"""

import argparse
import json
import math
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

DEFAULT_HALF_LIFE = 3600.0
DEFAULT_KEEP_SECS = 6 * 3600
MAX_EVENTS_PER_MODEL = 500


class BrokerState:
    """Thread-safe model reliability tracker with exponential failure decay."""

    def __init__(self, models: List[str], state_file: Optional[Path] = None):
        self.models = models
        self.state_file = state_file
        self.lock = threading.Lock()
        self.events: Dict[str, List[Dict]] = {m: [] for m in models}
        self._load()

    def _load(self):
        if self.state_file and self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                for m, evs in data.get("events", {}).items():
                    if m in self.events:
                        self.events[m] = evs[-MAX_EVENTS_PER_MODEL:]
            except Exception:
                pass

    def _save(self):
        if not self.state_file:
            return
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps({"events": self.events}, indent=2), encoding="utf-8")

    def _prune(self, now: float):
        cutoff = now - DEFAULT_KEEP_SECS
        for m in self.events:
            self.events[m] = [e for e in self.events[m] if e.get("ts", 0) >= cutoff][-MAX_EVENTS_PER_MODEL:]

    def failure_score(self, model: str, now: Optional[float] = None) -> float:
        """Compute decayed failure penalty (lower is healthier)."""
        now = now or time.time()
        score = 0.0
        for e in self.events.get(model, []):
            if not e.get("ok", True):
                age = max(0.0, now - float(e.get("ts", now)))
                score += math.pow(0.5, age / DEFAULT_HALF_LIFE)
        return score

    def pick(self, exclude: Optional[List[str]] = None) -> str:
        excl = set(exclude or [])
        with self.lock:
            now = time.time()
            self._prune(now)
            candidates = [m for m in self.models if m not in excl]
            if not candidates:
                return ""
            # Stable sort by failure_score; ties preserve configured priority order
            ranked = sorted(candidates, key=lambda m: self.failure_score(m, now))
            return ranked[0]

    def report(self, model: str, ok: bool, kind: str = "run", who: str = ""):
        with self.lock:
            now = time.time()
            self._prune(now)
            if model not in self.events:
                self.events[model] = []
            self.events[model].append({"ts": now, "ok": ok, "kind": kind, "who": who})
            self.events[model] = self.events[model][-MAX_EVENTS_PER_MODEL:]
            self._save()

    def status(self) -> Dict:
        with self.lock:
            now = time.time()
            self._prune(now)
            return {
                m: {
                    "failure_score": round(self.failure_score(m, now), 4),
                    "recent_events": len(self.events.get(m, [])),
                }
                for m in self.models
            }


def make_handler(state: BrokerState):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)

            if parsed.path == "/pick":
                excl_raw = qs.get("exclude", [""])[0]
                excl = [x.strip() for x in excl_raw.split(",") if x.strip()]
                chosen = state.pick(exclude=excl)
                self._send(200, "text/plain", chosen)
            elif parsed.path == "/report":
                model = qs.get("model", [""])[0]
                ok = qs.get("ok", ["1"])[0] == "1"
                kind = qs.get("kind", ["run"])[0]
                who = qs.get("who", [""])[0]
                if model:
                    state.report(model, ok=ok, kind=kind, who=who)
                self._send(200, "text/plain", "ok")
            elif parsed.path == "/status":
                self._send(200, "application/json", json.dumps(state.status(), indent=2))
            else:
                self._send(404, "text/plain", "not found")

        def _send(self, code: int, ctype: str, body: str):
            raw = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, format, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Agentic Factory Central Model Broker")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--models", nargs="+", default=["default-model"])
    parser.add_argument("--state-file", default=".factory/state/model_broker_state.json")
    args = parser.parse_args()

    state = BrokerState(models=args.models, state_file=Path(args.state_file))
    server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    print(f"Model Broker listening on http://{args.host}:{args.port} with {len(args.models)} model(s).")
    server.serve_forever()


if __name__ == "__main__":
    main()
