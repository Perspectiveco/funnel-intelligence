#!/usr/bin/env python3
"""LEAN per-arm A/B reach, STREAMING (no $group barrier -> output flows continuously).
find() over [campaignId,pageId,...] index, scoped to each batch's arm pages. Emits raw
(pageId, sessionId) per page-view event; dedup happens in BigQuery. Strict secondary."""
import os, gzip, time, subprocess
from collections import defaultdict
from pymongo import MongoClient, ReadPreference

URI = os.environ.get("MONGO_URI") or open(os.path.expanduser("~/muri")).read().strip()
GCS = os.environ.get("GCS_PREFIX")  # optional; if unset, just keep the local file
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"); os.makedirs(OUT, exist_ok=True)
cli = MongoClient(URI, read_preference=ReadPreference.SECONDARY, serverSelectionTimeoutMS=30000)
db = cli.heroku_8mgcnmlb
def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

camp_pages = defaultdict(set)
for d in db.campaign_ab_tests.find({}, {"abTests": 1}):
    for k, e in (d.get("abTests") or {}).items():
        if isinstance(e, dict):
            for f in ("controlPageId","variantPageId"):
                if e.get(f): camp_pages[d["_id"]].add(e[f])
camps = list(camp_pages)
log(f"{len(camps):,} test campaigns")

fn = f"{OUT}/abreach_all.csv.gz"; B = 200; total = 0; nb = (len(camps)+B-1)//B
with gzip.open(fn, "wt") as out:
    out.write("pageId,sessionId\n")
    for i in range(0, len(camps), B):
        batch = camps[i:i+B]
        bpages = [p for c in batch for p in camp_pages[c]]
        t0 = time.time(); n = 0
        # SELECTIVE: scoped to this batch's campaigns+arm pages (indexed prefix, ~3:1 examined:returned).
        # maxTimeMS kills any runaway batch instead of hammering the node. Skip type filter in query
        # (it's deep in the index); filter content.type client-side while streaming.
        try:
            cur = db.activities.find(
                {"campaignId": {"$in": batch}, "pageId": {"$in": bpages}},
                {"pageId": 1, "sessionId": 1, "content.type": 1, "_id": 0}
            ).batch_size(5000).max_time_ms(30000)
            for doc in cur:
                if (doc.get("content") or {}).get("type") != "page": continue
                pg, s = doc.get("pageId"), doc.get("sessionId")
                if pg and s: out.write(f"{pg},{s}\n"); n += 1
        except Exception as e:
            log(f"batch {i//B+1}/{nb} TIMED OUT/err ({str(e)[:50]}) — skipped, will note")
        total += n
        log(f"batch {i//B+1}/{nb}: +{n:,} (total {total:,}) {int(time.time()-t0)}s")
        out.flush(); time.sleep(2)  # brief pause so cache can breathe between batches
log(f"DONE: {total:,} (page,session) event rows -> {fn}")
if GCS:
    try:
        subprocess.run(["gsutil","cp",fn,f"{GCS}/abreach_all.csv.gz"], check=True); log("uploaded to GCS")
    except Exception as e:
        log(f"GCS upload failed ({e}); local kept at {fn}")
log("ALL DONE")
