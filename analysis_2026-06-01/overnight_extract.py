#!/usr/bin/env python3
"""Overnight, prod-gentle activities extraction. Runs on a GCP VM (laptop-independent).
Per month (18 back), reads from a SECONDARY, _id-indexed window:
  A) drop-off: per (versionId, pageSlug) -> page-view event count   [Engine B, all funnels]
  B) A/B arms: per (pageId, sessionId) for TEST pages only          [per-arm CVR, joined to sessions_v2 in BQ]
Writes each month's outputs to GCS as gzip, then sleeps. Resumable (skips months already in GCS).
Env: MONGO_URI (Atlas, read-only), GCS_PREFIX (gs://bucket/path).
"""
import os, sys, gzip, time, subprocess, datetime as dt
from pymongo import MongoClient, ReadPreference

URI = os.environ["MONGO_URI"]
GCS = os.environ.get("GCS_PREFIX", "gs://perspective-bi-funnel-intelligence/overnight")
MONTHS = int(os.environ.get("MONTHS", "18"))
PAUSE = int(os.environ.get("PAUSE_SECONDS", "20"))

OUT = os.path.expanduser("~/out"); os.makedirs(OUT, exist_ok=True)
cli = MongoClient(URI, read_preference=ReadPreference.SECONDARY, serverSelectionTimeoutMS=30000)  # STRICT: never the primary
db = cli.get_database("heroku_8mgcnmlb")
def log(m): print(f"[{dt.datetime.utcnow().isoformat()}] {m}", flush=True)
def gcs_exists(name):
    try: return subprocess.run(["gsutil","-q","stat",f"{GCS}/{name}"]).returncode == 0
    except Exception: return False
def gcs_put(local,name):
    # non-fatal: if GCS upload fails, KEEP the local file as a backup (we scp it tomorrow)
    try:
        subprocess.run(["gsutil","-q","cp",local,f"{GCS}/{name}"], check=True)
        log(f"uploaded {name}")
    except Exception as e:
        log(f"GCS upload FAILED for {name} ({e}); local copy kept at {local}")

from bson import ObjectId
def oid_for_days_ago(days):
    secs = int((dt.datetime.utcnow() - dt.timedelta(days=days)).timestamp())
    return ObjectId.from_datetime(dt.datetime.utcfromtimestamp(secs))

# test pageIds from campaign_ab_tests (one light pass)
log("collecting A/B test pageIds...")
test_pages = set()
for d in db.campaign_ab_tests.find({}, {"abTests": 1}):
    for k, e in (d.get("abTests") or {}).items():
        if isinstance(e, dict):
            for f in ("controlPageId","variantPageId"):
                if e.get(f): test_pages.add(str(e[f]))   # hex string: activities stores perspective.pageId as a string
test_pages = list(test_pages)
log(f"{len(test_pages):,} distinct test pageIds")

for m in range(MONTHS, 0, -1):
    lo, hi = oid_for_days_ago(m*30), oid_for_days_ago((m-1)*30)
    tag = f"month_{m:02d}"
    if gcs_exists(f"dropoff_{tag}.csv.gz"):
        log(f"{tag} already done, skipping"); continue
    t0 = time.time()
    # A) drop-off counts (all pages)
    fa = f"{OUT}/dropoff_{tag}.csv.gz"
    with gzip.open(fa,"wt") as f:
        f.write("campaignVersionId,pageSlug,events\n")
        cur = db.activities.aggregate([
            {"$match":{"_id":{"$gte":lo,"$lt":hi},"content.type":"page"}},
            {"$group":{"_id":{"v":"$content.context.perspective.versionId",
                              "p":"$content.context.perspective.pageSlug"},"n":{"$sum":1}}}
        ], allowDiskUse=True, batchSize=5000)
        n=0
        for r in cur:
            v,p=r["_id"].get("v"),r["_id"].get("p")
            if v and p: f.write(f"{v},{p},{r['n']}\n"); n+=1
    log(f"{tag} dropoff: {n:,} rows in {int(time.time()-t0)}s"); gcs_put(fa,f"dropoff_{tag}.csv.gz")
    # B) test-page session reach (for per-arm CVR via BQ join to sessions_v2)
    fb=f"{OUT}/abreach_{tag}.csv.gz"; t1=time.time()
    with gzip.open(fb,"wt") as f:
        f.write("pageId,sessionId\n")
        cur = db.activities.aggregate([
            {"$match":{"_id":{"$gte":lo,"$lt":hi},"content.type":"page",
                       "content.context.perspective.pageId":{"$in":test_pages}}},
            {"$group":{"_id":{"pg":"$content.context.perspective.pageId","s":"$sessionId"}}}
        ], allowDiskUse=True, batchSize=5000)
        nb=0
        for r in cur:
            pg,s=r["_id"].get("pg"),r["_id"].get("s")
            if pg and s: f.write(f"{pg},{str(s)}\n"); nb+=1   # str(sessionId) -> hex for BQ join to sessions_v2._id
    log(f"{tag} abreach: {nb:,} rows in {int(time.time()-t1)}s"); gcs_put(fb,f"abreach_{tag}.csv.gz")
    log(f"{tag} done; sleeping {PAUSE}s"); time.sleep(PAUSE)
log("ALL DONE")
