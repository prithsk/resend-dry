"""Send the same requests to the live Resend API and to resend-dry and compare what comes back.

  python fidelity.py          # needs RESEND_API_KEY in .env; starts resend-dry itself
Uses Resend's documented test inbox delivered@resend.dev, so live sends go nowhere real.
"""
import json, os, subprocess, sys, time, urllib.request, urllib.error, datetime
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
ROOT = Path(__file__).parent
for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines() if (ROOT / ".env").exists() else []:
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        if v.strip(): os.environ.setdefault(k.strip(), v.strip())
KEY = os.environ.get("RESEND_API_KEY")
FROM = os.environ.get("RESEND_FROM", "onboarding@resend.dev")
TO = os.environ.get("RESEND_TO", "delivered@resend.dev")
ok = {"from": FROM, "to": [TO], "subject": "fidelity check", "html": "<p>test</p>"}
CASES = [
    ("valid send", "/emails", ok),
    ("text body only", "/emails", {**{k: v for k, v in ok.items() if k != "html"}, "text": "plain"}),
    ("missing subject", "/emails", {k: v for k, v in ok.items() if k != "subject"}),
    ("missing from", "/emails", {k: v for k, v in ok.items() if k != "from"}),
    ("missing to", "/emails", {k: v for k, v in ok.items() if k != "to"}),
    ("no html or text", "/emails", {k: v for k, v in ok.items() if k != "html"}),
    ("51 recipients", "/emails", {**ok, "to": [TO] * 51}),
    ("invalid from address", "/emails", {**ok, "from": "not-an-email"}),
    ("batch of two", "/emails/batch", [ok, {**ok, "subject": "second"}]),
    ("batch with one bad", "/emails/batch", [ok, {k: v for k, v in ok.items() if k != "subject"}]),
]

def call(base, path, body):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY or 'dry'}", "User-Agent": "resend-dry-fidelity"})
    try:
        r = urllib.request.urlopen(req, timeout=30); j = json.loads(r.read() or b"{}"); return r.status, j
    except urllib.error.HTTPError as e:
        try: j = json.loads(e.read() or b"{}")
        except Exception: j = {}
        return e.code, j

def shape(status, j):
    if status < 300: return f"{status} ok"
    return f"{status} {j.get('name', '?')}"

def main():
    if not KEY: raise SystemExit("RESEND_API_KEY is not set in .env")
    srv = subprocess.Popen([sys.executable, str(ROOT / "resend_dry.py"), "--port", "3124", "--store", str(ROOT / "outbox-fidelity")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2); rows = []
    try:
        for name, path, body in CASES:
            live = call("https://api.resend.com", path, body); time.sleep(0.6)   # stay under Resend's rate limit
            dry = call("http://127.0.0.1:3124", path, body)
            rows.append({"case": name, "live": shape(*live), "dry": shape(*dry), "live_message": live[1].get("message", ""),
                         "dry_message": dry[1].get("message", ""), "match": shape(*live) == shape(*dry),
                         "msg_match": live[1].get("message", "") == dry[1].get("message", "")})
    finally:
        srv.terminate()
    n = sum(r["match"] for r in rows)
    out = [f"# resend-dry fidelity, {datetime.date.today()}", "", f"**Matched the live API's status and error name on {n} of {len(rows)} cases.**", "",
           f"Error messages matched word for word on {sum(r['msg_match'] for r in rows if r['live_message'])} of {sum(1 for r in rows if r['live_message'])} error cases.", "",
           "| Case | Live Resend | resend-dry | Match |", "|---|---|---|---|"]
    out += [f"| {r['case']} | {r['live']} | {r['dry']} | {'yes' if r['match'] else 'NO'} |" for r in rows]
    out += ["", "Live error messages, for calibrating mismatches:", ""] + [f"- {r['case']}: {r['live_message']}" for r in rows if r["live_message"]]
    md = "\n".join(out); (ROOT / "fidelity-results.md").write_text(md, encoding="utf-8"); print(md)

if __name__ == "__main__": main()
