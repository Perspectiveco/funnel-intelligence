"""Improved causal linkage: testKey(ms) -> nearest split_test_created (precise) -> next ended -> kept_original.
Then change-type -> challenger-win-rate, overall + per niche."""
import json, re, pandas as pd, numpy as np
from collections import defaultdict
from pathlib import Path
D=Path(__file__).parent
DAY=86400000

# page features
feats={}; hexre=re.compile(r"^[0-9a-f]{24},")
for l in open(D/"abtest_pagefeats.csv"):
    if not hexre.match(l): continue
    p=l.strip().split(","); feats[p[0]]=dict(n=int(p[1]),qm=int(p[2]),qt=int(p[3]),qc=int(p[4]),
        qf=int(p[5]),inp=int(p[6]),btn=int(p[7]),soc=int(p[8]),med=int(p[9]))

# split events -> per funnel created[] / ended[]
ev=pd.read_csv(D/"data/split_events.csv",dtype={"funnel_id":str})
created=defaultdict(list); ended=defaultdict(list)
for r in ev.itertuples():
    if pd.isna(r.ts_ms): continue
    if r.event_name=="split_test_created": created[r.funnel_id].append(int(r.ts_ms))
    else: ended[r.funnel_id].append((int(r.ts_ms), str(r.kept_original).lower()=="false"))
for f in created: created[f].sort()
for f in ended: ended[f].sort()

# abtest entries
rows=[json.loads(l) for l in open(D/"abtests_pairs.jsonl") if l.strip()]
ents=[r for r in rows if not r.get("_done")]
df=pd.DataFrame([{"campaignId":r["_campaignId"],"control":r["controlPageId"]["$oid"],
                  "variant":r["variantPageId"]["$oid"],"tk":int(r["_testKey"])} for r in ents])
df=df[df.control.isin(feats)&df.variant.isin(feats)].drop_duplicates(["campaignId","tk"]).copy()
print(f"distinct (campaign,testKey) with both pages known: {len(df):,}")

def nearest(arr,x):
    if not arr: return None,None
    import bisect; i=bisect.bisect_left(arr,x)
    best=None;bd=None
    for j in (i-1,i):
        if 0<=j<len(arr):
            d=abs(arr[j]-x)
            if bd is None or d<bd: bd=d;best=arr[j]
    return best,bd

def link(c,tk):
    cr,d=nearest(created.get(c,[]),tk)
    if cr is None or d>DAY: return None        # testKey must sit near a real created event (<=1 day)
    after=[(t,w) for (t,w) in ended.get(c,[]) if t>cr-3600000]   # ended at/after creation
    if not after: return None
    after.sort(); return after[0][1]            # first ended after creation = this test's verdict
df["won"]=[link(c,tk) for c,tk in zip(df.campaignId,df.tk)]
m=df.dropna(subset=["won"]).copy()
print(f"linked to a verdict (precise): {len(m):,}  (baseline challenger-win {100*m.won.mean():.1f}%)")

# niche map
st=pd.read_csv(D/"data/funnel_struct.csv",low_memory=False,dtype={"campaignId":str,"campaignVersionId":str})
ver=pd.read_csv(D/"data/funnel_vertical_v2.csv",dtype={"campaignVersionId":str})[["campaignVersionId","vertical","subtype"]]
cv=st[["campaignId","campaignVersionId"]].merge(ver,on="campaignVersionId")
cv["niche"]=np.where(cv.vertical=="Recruiting","R: "+cv.subtype,cv.vertical)
c2n=cv.groupby("campaignId").niche.agg(lambda s:s.mode().iloc[0] if len(s.mode()) else None)
m=m.merge(c2n.rename("niche"),left_on="campaignId",right_index=True,how="left")

def dl(r,k): return feats[r.variant][k]-feats[r.control][k]
changes={"added a form-question":lambda r:dl(r,"qf")>0,"removed a form-question":lambda r:dl(r,"qf")<0,
 "added input fields":lambda r:dl(r,"inp")>0,"removed input fields":lambda r:dl(r,"inp")<0,
 "added any question":lambda r:(dl(r,"qm")+dl(r,"qt")+dl(r,"qc")+dl(r,"qf"))>0,
 "removed any question":lambda r:(dl(r,"qm")+dl(r,"qt")+dl(r,"qc")+dl(r,"qf"))<0,
 "added media":lambda r:dl(r,"med")>0,"removed media":lambda r:dl(r,"med")<0,
 "added social proof":lambda r:dl(r,"soc")>0,"added a CTA/button":lambda r:dl(r,"btn")>0,
 "more components":lambda r:dl(r,"n")>0,"fewer components":lambda r:dl(r,"n")<0}
base=m.won.mean()
print(f"\n=== challenger-win-rate by change (baseline {100*base:.1f}%, n={len(m):,}) ===")
out=[]
for name,fn in changes.items():
    msk=m.apply(fn,axis=1)
    if msk.sum()<60: continue
    out.append((name,int(msk.sum()),100*m[msk].won.mean(),100*(m[msk].won.mean()-base)))
for name,n,wr,lift in sorted(out,key=lambda x:-x[2]):
    f="  helps" if lift>4 else ("  hurts" if lift<-4 else "")
    print(f"  {wr:5.1f}%  (n={n:>5}, {lift:+.1f}pp){f}  {name}")
m.to_csv(D/"data/causal_linked.csv",index=False)
print(f"\nsaved {len(m):,} linked tests -> data/causal_linked.csv")
