"""Build the demo data via the LIVE engine (recommend.py): classify niche (+confidence) ->
within-niche percentile -> per-niche recs split into experiments (universal/niche-specific) and
test-don't-apply (the form). No duplicated logic — single source of truth is recommend.py."""
import json, numpy as np, pandas as pd
from pathlib import Path
import recommend as R   # loads classifier + per-niche drivers + features on import
D=Path(__file__).parent

names=pd.read_csv(D/"data/funnel_content.csv",usecols=["campaignVersionId","funnel_name"])
F=R.F.merge(names,on="campaignVersionId",how="left")
F["pct"]=F.groupby("niche").cvr.rank(pct=True)
counts=F.niche.value_counts().to_dict()
good=F[F.funnel_name.notna() & (F.funnel_name.str.len()>6) &
       (~F.funnel_name.str.contains("Funnel 2026|Neues|Kopie|copy|Test",case=False,na=False))]

def sample(cvid):
    r=R.recommend(cvid)
    if r is None: return None
    row=F[F.campaignVersionId==cvid].iloc[0]
    exp=[{"text":x["text"],"universal":x["universal"],"corr":x["corr"],"suggestion":x.get("suggestion")} for x in r["exp"]]
    test=[{"text":x["text"],"corr":x["corr"]} for x in r["test"]]
    note=("" if len(exp)>=2 else
        "Few structural gaps vs your niche's winners. At a score this low the lever is most likely your "
        "audience, offer or traffic (design explains only ~13% of conversion) or your COPY — which carries far "
        "more signal than layout. The highest-value test here is messaging, not structure.")
    return {"id":cvid,"name":str(row.funnel_name)[:60],"niche":r["niche"],
            "conf":int(round(r["conf"]*100)),"ask_user":r["conf"]<R.THR,
            "alt":[{"niche":n,"conf":int(round(p*100))} for n,p in r["top3"][1:]] if r["conf"]<R.THR else [],
            "score":int(round(r["pct"]*100)),"visitors":int(row.visitors),"cvr":round(float(row.cvr)*100,2),
            "niche_median_cvr":round(float(r["niche_median"])*100,2),"niche_n":int(counts.get(r["niche"],0)),
            "stats":{"pages":int(row.n_pages),"form_qs":int(row.q_form),"media_qs":int(row.q_media),
                     "form_fields":int(row.n_form_fields),"social":int(row.n_social),
                     "opens_with_question":bool(row.lp_has_question)},
            "exp":exp,"test":test,"note":note}

samples=[]
for niche in sorted(counts,key=lambda n:-counts[n])[:9]:
    sub=good[(good.niche==niche)&(good.visitors>=2000)].sort_values("pct")
    if len(sub)<3: continue
    for r in [sub.iloc[1],sub.iloc[len(sub)//2],sub.iloc[-2]]:   # low / mid / high scorer
        s=sample(r.campaignVersionId)
        if s: samples.append(s)
print(f"{len(samples)} sample funnels across {len(set(s['niche'] for s in samples))} niches")
(D/"data/demo_data.json").write_text(json.dumps(samples,ensure_ascii=False))
print("wrote data/demo_data.json")
