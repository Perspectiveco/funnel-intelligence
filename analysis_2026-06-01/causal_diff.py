"""CAUSAL: diff control vs variant page structure per A/B test, join kept_original verdict,
compute challenger-win-rate by change type. The 'which change causes lift' analysis."""
import json, re, pandas as pd, numpy as np
from datetime import datetime, timedelta
from pathlib import Path
D=Path(__file__).parent

# 1. page features (skip diagnostic lines)
feats={}
hexre=re.compile(r"^[0-9a-f]{24},")
for l in open(D/"abtest_pagefeats.csv"):
    if not hexre.match(l): continue
    p=l.strip().split(",")
    feats[p[0]]=dict(n=int(p[1]),qm=int(p[2]),qt=int(p[3]),qc=int(p[4]),qf=int(p[5]),
                     inp=int(p[6]),btn=int(p[7]),soc=int(p[8]),med=int(p[9]))
print(f"pages with structure: {len(feats):,}")

# 2. test entries (campaignId, control, variant, testKey)
rows=[json.loads(l) for l in open(D/"abtests_pairs.jsonl") if l.strip()]
ents=[r for r in rows if not r.get("_done")]
df=pd.DataFrame([{"campaignId":r["_campaignId"],"control":r["controlPageId"]["$oid"],
                  "variant":r["variantPageId"]["$oid"],
                  "create":datetime.utcfromtimestamp(int(r["_testKey"])/1000).date()} for r in ents])
df=df[df.control.isin(feats)&df.variant.isin(feats)].copy()
print(f"test entries with BOTH pages known: {len(df):,}")

# 3. join kept_original verdict by campaignId + start_date(=end-duration) ~ create_date
ste=pd.read_csv(D/"data/split_test_ended.csv",dtype={"funnel_id":str})
ste=ste[ste.duration_days>=1].copy()
ste["end"]=pd.to_datetime(ste.date).dt.date
ste["start"]=ste.apply(lambda r:r.end - timedelta(days=int(r.duration_days)),axis=1)
ste["challenger_won"]=(ste.kept_original.astype(str).str.lower()=="false").astype(int)
by_camp={}
for r in ste.itertuples():
    by_camp.setdefault(r.funnel_id,[]).append((r.start,r.challenger_won))
def match(c,cr):
    if c not in by_camp: return None
    best=None;bd=3
    for (s,w) in by_camp[c]:
        d=abs((s-cr).days)
        if d<=2 and d<bd: bd=d;best=w
    return best
df["won"]=[match(c,cr) for c,cr in zip(df.campaignId,df.create)]
m=df.dropna(subset=["won"]).copy()
print(f"tests linked to a kept_original verdict (±2d): {len(m):,}  (challenger-win baseline {100*m.won.mean():.1f}%)")

# 4. structural changes variant-vs-control -> challenger-win-rate per change
def cf(p,k): return feats[p][k]
def delta(r,k): return cf(r.variant,k)-cf(r.control,k)
changes={
 "added a form-question (q_form↑)": lambda r: delta(r,"qf")>0,
 "removed a form-question (q_form↓)": lambda r: delta(r,"qf")<0,
 "added input fields":             lambda r: delta(r,"inp")>0,
 "removed input fields":           lambda r: delta(r,"inp")<0,
 "added any question":             lambda r: (delta(r,"qm")+delta(r,"qt")+delta(r,"qc")+delta(r,"qf"))>0,
 "removed any question":           lambda r: (delta(r,"qm")+delta(r,"qt")+delta(r,"qc")+delta(r,"qf"))<0,
 "added media":                    lambda r: delta(r,"med")>0,
 "removed media":                  lambda r: delta(r,"med")<0,
 "added social proof":             lambda r: delta(r,"soc")>0,
 "added a CTA/button":             lambda r: delta(r,"btn")>0,
 "more components overall":        lambda r: delta(r,"n")>0,
 "fewer components overall":       lambda r: delta(r,"n")<0,
}
base=m.won.mean()
print(f"\n=== challenger-win-rate by change type (variant did X). baseline {100*base:.1f}% ===")
res=[]
for name,fn in changes.items():
    mask=m.apply(fn,axis=1)
    if mask.sum()<40: continue
    wr=m[mask].won.mean()
    res.append((name,mask.sum(),100*wr,100*(wr-base)))
res.sort(key=lambda x:-x[2])
for name,n,wr,lift in res:
    flag="  <-- helps" if lift>3 else ("  <-- hurts" if lift<-3 else "")
    print(f"  {wr:5.1f}%  (n={n:>5}, {lift:+.1f}pp vs base)  {name}{flag}")
