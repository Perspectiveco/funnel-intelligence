"""Tiny stdlib backend for the 'paste a funnel' demo (no extra deps).
 GET  /            -> analyze.html (paste box)
 POST /analyze     -> {text,name} | {cvid} | {url}  ->  engine JSON
Run:  .venv/bin/python server.py   (then open http://127.0.0.1:8754)"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import analyze
D=Path(__file__).parent
PORT=8754

class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def _send(self,code,body,ctype="application/json"):
        b=body.encode() if isinstance(body,str) else body
        self.send_response(code); self.send_header("Content-Type",ctype)
        self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path in ("/","/index.html","/analyze.html"):
            self._send(200,(D/"analyze.html").read_text(),"text/html; charset=utf-8")
        else: self._send(404,"not found","text/plain")
    def do_POST(self):
        if self.path!="/analyze": return self._send(404,"not found","text/plain")
        try:
            n=int(self.headers.get("Content-Length",0)); req=json.loads(self.rfile.read(n) or b"{}")
        except Exception as e: return self._send(400,json.dumps({"error":f"bad request: {e}"}))
        try:
            if req.get("funnel_id","").strip(): out=analyze.analyze_id(req["funnel_id"])
            elif req.get("cvid"): out=analyze.analyze_cvid(req["cvid"].strip())
            elif req.get("text","").strip(): out=analyze.analyze_text(req["text"],req.get("name",""))
            elif req.get("url","").strip():
                out={"error":"URL fetch isn't wired yet — published funnels are client-rendered, so I need a sample link to see how the content is served. For now paste the funnel's text (or a campaignVersionId)."}
            else: out={"error":"paste the funnel text, or pass a cvid"}
        except Exception as e: out={"error":f"{type(e).__name__}: {e}"}
        self._send(200,json.dumps(out,ensure_ascii=False))

if __name__=="__main__":
    import sys
    try:
        srv=ThreadingHTTPServer(("127.0.0.1",PORT),H)
    except OSError as e:
        if e.errno in (48,98):
            print(f"\nPort {PORT} is already in use (another server is running).\n"
                  f"Free it with:   lsof -ti :{PORT} | xargs kill -9\n"
                  f"then re-run:    .venv/bin/python server.py\n")
            sys.exit(1)
        raise
    print(f"serving on http://127.0.0.1:{PORT}   — open it in your browser, paste a campaign ID")
    srv.serve_forever()
