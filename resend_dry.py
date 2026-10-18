#!/usr/bin/env python3
"""resend-dry: a local Resend that doesn't send.

Point RESEND_BASE_URL (or your SDK's baseUrl) at http://localhost:3123 in dev. Every
POST /emails is accepted, stored, and viewable at http://localhost:3123/ with the
rendered HTML. Nothing leaves your machine. Replies look exactly like Resend's.

  python resend_dry.py            # listens on 3123
  python resend_dry.py --port 4000 --store ./outbox
"""
# --- windows-safe preamble: utf-8 console, load .env, readable API errors ---
import os as _os, sys as _sys
from pathlib import Path as _Path
try: _sys.stdout.reconfigure(encoding="utf-8", errors="replace"); _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
def _load_env():
    here = _Path(__file__).resolve().parent
    for p in (_Path.cwd() / ".env", here / ".env", here.parent / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line: continue
                k, v = line.split("=", 1); v = v.strip().strip('"').strip("'")
                if v: _os.environ.setdefault(k.strip(), v)
            return
_load_env()
def _ok(r):
    if r.status_code >= 400:
        raise SystemExit(f"API error {r.status_code} on {r.request.method} {r.url}\n{r.text[:800]}")
    return r
# --- end preamble ---
import argparse, json, html, os, time, uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

STORE = "outbox"

def _save(msg):
    os.makedirs(STORE, exist_ok=True)
    msg["id"] = str(uuid.uuid4()); msg["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(os.path.join(STORE, f"{int(time.time()*1000)}-{msg['id']}.json"), "w") as f: json.dump(msg, f, indent=1)
    return msg

def _all():
    if not os.path.isdir(STORE): return []
    out = []
    for fn in sorted(os.listdir(STORE), reverse=True):
        if fn.endswith(".json"):
            with open(os.path.join(STORE, fn)) as f: out.append(json.load(f))
    return out

def _by_id(i):
    return next((m for m in _all() if m["id"] == i), None)

import re
EMAIL = re.compile(r"^[^<>@\s]+@[^<>@\s]+\.[^<>@\s]+$")
NAMED = re.compile(r"^[^<>]*<[^<>@\s]+@[^<>@\s]+\.[^<>@\s]+>$")

def validate(msg):
    """First problem as (name, message), matching the live Resend API's names and wording, or None."""
    if not msg.get("from"): return ("validation_error", "Missing `from` field.")
    to = msg.get("to")
    if not to: return ("missing_required_field", "Missing `to` field.")   # Resend names this one differently
    if not msg.get("subject"): return ("validation_error", "Missing `subject` field.")
    if not (msg.get("html") or msg.get("text") or msg.get("react")): return ("validation_error", "Missing `html` or `text` field.")
    f = str(msg.get("from")).strip()
    if not (EMAIL.match(f) or NAMED.match(f)):
        return ("validation_error", "Invalid `from` field. The email address needs to follow the `email@example.com` or `Name <email@example.com>` format.")
    if isinstance(to, list) and len(to) > 50: return ("validation_error", "Field `to` has a maximum of 50 items.")
    return None

class H(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code)
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _html(self, body):
        b = body.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        p = urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0); raw = self.rfile.read(n) if n else b"{}"
        try: body = json.loads(raw or b"{}")
        except Exception: return self._json(400, {"name": "validation_error", "message": "invalid JSON"})
        if p == "/emails":
            err = validate(body)
            if err: return self._json(422, {"statusCode": 422, "name": err[0], "message": err[1]})
            m = _save(body); return self._json(200, {"id": m["id"]})
        if p == "/emails/batch":
            if not isinstance(body, list): return self._json(400, {"name": "validation_error", "message": "batch body must be a list"})
            for item in body:                       # check the whole batch before saving any of it
                err = validate(item)
                if err: return self._json(422, {"statusCode": 422, "name": err[0], "message": err[1]})
            ids = [{"id": _save(item)["id"]} for item in body]
            return self._json(200, {"data": ids})
        self._json(404, {"name": "not_found", "message": p})
    def do_GET(self):
        p = urlparse(self.path).path
        if p.startswith("/emails/") and len(p) > 8 and self.headers.get("Accept", "").startswith("application/json"):
            m = _by_id(p[8:]); return self._json(200, m) if m else self._json(404, {"name": "not_found"})
        if p.startswith("/emails/") and len(p) > 8:
            m = _by_id(p[8:])
            if not m: return self._html("<h1>not found</h1>")
            content = m.get("html") or f"<pre>{html.escape(m.get('text') or '')}</pre>"
            return self._html(f"<p><a href='/'>← outbox</a></p><h3>{html.escape(m.get('subject',''))}</h3>"
                              f"<p><b>from</b> {html.escape(str(m.get('from')))} · <b>to</b> {html.escape(str(m.get('to')))}</p>"
                              f"<iframe sandbox style='width:100%;height:80vh;border:1px solid #ddd' srcdoc=\"{html.escape(content, quote=True)}\"></iframe>")
        rows = "".join(f"<tr><td>{html.escape(m['created_at'])}</td><td>{html.escape(str(m.get('to')))}</td>"
                       f"<td><a href='/emails/{m['id']}'>{html.escape(m.get('subject',''))}</a></td></tr>" for m in _all())
        self._html(f"<h2>resend-dry outbox ({len(_all())})</h2><table border=1 cellpadding=6><tr><th>time</th><th>to</th><th>subject</th></tr>{rows}</table>")
    def log_message(self, *a): pass

def main():
    global STORE
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=3123); ap.add_argument("--store", default="outbox"); ap.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 only inside a trusted network")
    a = ap.parse_args(); STORE = a.store
    print(f"resend-dry on http://{a.host}:{a.port}  (set your SDK base URL here; outbox at /)")
    HTTPServer((a.host, a.port), H).serve_forever()

if __name__ == "__main__": main()
