import json, threading, time, urllib.request, tempfile, os
import resend_dry
from http.server import HTTPServer
resend_dry.STORE = tempfile.mkdtemp()
srv = HTTPServer(("127.0.0.1", 0), resend_dry.H); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
def post(path, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(), headers={"Content-Type":"application/json"}, method="POST")
    try: return urllib.request.urlopen(req).getcode(), json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e: return e.code, json.load(e)
# valid send -> 200 with id, same shape as Resend
c, j = post("/emails", {"from":"a@x.dev","to":["b@y.com"],"subject":"hi","html":"<b>yo</b>"}); assert c==200 and "id" in j, (c,j)
# missing subject -> 422 validation_error like Resend
c, j = post("/emails", {"from":"a@x.dev","to":"b@y.com","html":"x"}); assert c==422 and j["name"]=="validation_error" and "subject" in j["message"]
# >50 recipients rejected
c, j = post("/emails", {"from":"a@x.dev","to":[f"u{i}@y.com" for i in range(51)],"subject":"s","text":"t"}); assert c==422 and "50" in j["message"]
# batch
c, j = post("/emails/batch", [{"from":"a@x.dev","to":"b@y.com","subject":"1","text":"t"},{"from":"a@x.dev","to":"c@y.com","subject":"2","text":"t"}]); assert c==200 and len(j["data"])==2
# outbox lists them; detail renders
page = urllib.request.urlopen(f"http://127.0.0.1:{port}/").read().decode(); assert "outbox" in page and ">hi<" in page or "hi</a>" in page
assert len(resend_dry._all()) >= 4
print("all tests passed")
