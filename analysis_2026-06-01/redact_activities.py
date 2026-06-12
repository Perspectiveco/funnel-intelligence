#!/usr/bin/env python3
"""Local PII redactor for mongoexport output. Reads raw extended-JSON .jsonl,
writes a structure-only file safe to share. Run:
    python3 redact_activities.py activities_raw.jsonl > activities_schema_sample.jsonl
Then delete activities_raw.jsonl.
"""
import sys, json, re

SAFE = {"eventType","type","__t","action","event","eventName","kind","category","status","state",
        "step","stepIndex","index","position","pageIndex","slug","pageSlug","pageId","page",
        "campaignId","campaignVersionId","platform","device","deviceType","browser","os",
        "locale","language","source","medium","utm_source"}
PII   = re.compile(r"(email|mail|phone|tel|mobile|telefon|first.?name|last.?name|vorname|nachname|"
                   r"fullname|answer|values?|inputs?|message|comment|text|content|address|strasse|"
                   r"street|city|plz|zip|postal|contact|ip|user.?agent|payload|data)", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"\+?\d[\d\s().\/-]{6,}\d")

def red(v, key=None, depth=0):
    if depth > 7: return "<deep>"
    if v is None: return v
    if isinstance(v, list): return [red(x, key, depth+1) for x in v[:4]]
    if isinstance(v, dict):
        if "$oid" in v: return "<oid>"
        if "$date" in v: return "<date>"
        if "$binary" in v: return "<bin>"
        for nk in ("$numberLong","$numberInt","$numberDouble","$numberDecimal"):
            if nk in v:
                try: return float(v[nk])
                except: return 0
        return {k: red(val, k, depth+1) for k, val in v.items()}
    if isinstance(v, str):
        if key and PII.search(key): return "<redacted>"
        if EMAIL.search(v) or PHONE.search(v): return "<pii>"
        if key and key in SAFE and len(v) <= 60: return v
        return f"<str:{len(v)}>"
    return v

for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()
    if not line: continue
    try:
        print(json.dumps(red(json.loads(line))))
    except Exception as e:
        print(json.dumps({"_err": str(e)[:90]}))
