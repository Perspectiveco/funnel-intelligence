"""Engine for arbitrary funnel input (the 'paste a funnel' path).
 - TEXT mode (works on any pasted funnel copy): embed (MiniLM, local) -> classify niche -> niche
   benchmark + the niche's winner-pattern PLAYBOOK + real winner-opener exemplars. No /100 score
   (that needs the funnel's component tree, which text alone doesn't carry).
 - FULL mode (a known campaignVersionId, or later a URL resolved to one): the complete personalised
   recommend.recommend() with the within-niche score.
Single source of truth = recommend.py (classifier, per-niche driver matrix, winner norms, phrasing)."""
import re, numpy as np, pandas as pd
import recommend as R
from pathlib import Path
D=Path(__file__).parent
clean=lambda s: re.sub(r"\s+"," ",str(s)).replace(" | "," ").strip()
THRC=0.04
# campaignId -> best (highest-traffic) scored campaignVersionId, + names, for id lookup
_st=pd.read_csv(D/"data/funnel_struct.csv",low_memory=False,dtype={"campaignId":str,"campaignVersionId":str})
_nmsrc="data/funnel_meta.csv" if (D/"data/funnel_meta.csv").exists() else "data/funnel_content.csv"
_nm=pd.read_csv(D/_nmsrc,usecols=["campaignVersionId","funnel_name"]).set_index("campaignVersionId").funnel_name.to_dict()
_scored=set(R.F.campaignVersionId)
_s=_st[_st.campaignVersionId.isin(_scored)].sort_values("visitors",ascending=False)
CID2VER=_s.groupby("campaignId").campaignVersionId.first().to_dict()
VERSET=set(_s.campaignVersionId)

_MODEL=None
def _embed(name,text):
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL=SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    doc=(str(name or "")+". ")*2 + str(text or "")[:400]
    return _MODEL.encode([doc],normalize_embeddings=True,convert_to_numpy=True)[0]

# real winner-opener exemplars per niche (top-CVR funnels that open with a question)
import json as _json
_EXJSON=_json.loads((D/"data/niche_exemplars.json").read_text()) if (D/"data/niche_exemplars.json").exists() else None
_ct=None; _ex={}
def _exemplars(niche,k=2):
    global _ct
    if _EXJSON is not None: return _EXJSON.get(niche,[])[:k]   # precomputed (slim bundle, no raw copy)
    if niche in _ex: return _ex[niche]
    if _ct is None: _ct=pd.read_csv(D/"data/funnel_content.csv",usecols=["campaignVersionId","content_text"]).set_index("campaignVersionId")
    g=R.F[(R.F.niche==niche)&(R.F.lp_has_question==1)].sort_values("cvr",ascending=False).head(40)
    out=[]
    for cid in g.campaignVersionId:
        if cid in _ct.index:
            t=clean(_ct.loc[cid,"content_text"])[:110]
            if len(t)>30 and "[Template" not in t and "Text Block" not in t: out.append(t)
        if len(out)>=k: break
    _ex[niche]=out; return out

def _playbook(niche,topn=5):
    """Unconditional niche playbook (no funnel-value gating) — for TEXT mode where we lack structure."""
    recs=[]
    for f,(inc,dec) in R.PH.items():
        if f not in R.M.index or pd.isna(R.M.loc[f,niche]) or abs(R.M.loc[f,niche])<THRC: continue
        corr=R.M.loc[f,niche]; text=inc if corr>0 else dec
        if not text: continue
        recs.append(dict(feat=f,text=text,priority=abs(corr),corr=round(float(corr),3),
                         form=f in R.FORM,universal=R.UNIV.get(f,False)))
    recs.sort(key=lambda r:-r["priority"])
    # consolidate opener family into one
    op=[r for r in recs if r["feat"] in R.OPENER]
    if op:
        best=max(op,key=lambda r:r["priority"])
        recs=[r for r in recs if r["feat"] not in R.OPENER]+[dict(feat="opener",
            text="Open page 1 with one interactive question instead of a static hero/intro",
            priority=best["priority"]+1,corr=best["corr"],form=False,universal=True)]
        recs.sort(key=lambda r:-r["priority"])
    exp=[r for r in recs if not r["form"]][:topn]
    test=[r for r in recs if r["form"]][:2]
    return exp,test

def analyze_text(text,name=""):
    niche,conf,top3=R.classify(_embed(name,text))
    exp,test=_playbook(niche)
    return {"mode":"text","input_name":name or "(pasted funnel)","niche":niche,
        "conf":int(round(conf*100)),"ask_user":conf<R.THR,
        "alt":[{"niche":n,"conf":int(round(p*100))} for n,p in top3[1:]],
        "niche_median_cvr":round(float(R.NMED.get(niche,0))*100,2),
        "exp":[{"text":r["text"],"universal":r["universal"],"corr":r["corr"]} for r in exp],
        "test":[{"text":r["text"],"corr":r["corr"]} for r in test],
        "exemplars":_exemplars(niche),
        "note":"Niche + your-niche playbook from the funnel text. The /100 score and form/length recs need the funnel's page structure (URL ingestion, coming next)."}

def analyze_id(fid):
    """Accept a campaignId OR a campaignVersionId; resolve to a scored version, then full analysis."""
    fid=str(fid).strip()
    cvid = fid if fid in VERSET else CID2VER.get(fid)
    if not cvid:
        return {"error":f"'{fid}' isn't in this offline dataset (~56.5k campaigns / 196k funnels from our snapshot). "
            f"Paste a campaignId or campaignVersionId from the snapshot, or use an example below. "
            f"Live lookup of any funnel needs the BigQuery hookup (next step)."}
    return analyze_cvid(cvid)

def analyze_cvid(cvid):
    r=R.recommend(cvid)
    if r is None: return {"error":f"unknown funnel id {cvid}"}
    row=R.F[R.F.campaignVersionId==cvid].iloc[0]
    nm=_nm.get(cvid); label=f"{nm}  ·  {cvid}" if isinstance(nm,str) and nm else cvid
    return {"mode":"full","input_name":label,"niche":r["niche"],"conf":int(round(r["conf"]*100)),
        "ask_user":r["conf"]<R.THR,"alt":[{"niche":n,"conf":int(round(p*100))} for n,p in r["top3"][1:]],
        "score":int(round(r["pct"]*100)),"cvr":round(float(row.cvr)*100,2),
        "niche_median_cvr":round(float(r["niche_median"])*100,2),
        "exp":[{"text":x["text"],"universal":x["universal"],"corr":x["corr"],"suggestion":x.get("suggestion")} for x in r["exp"]],
        "test":[{"text":x["text"],"corr":x["corr"]} for x in r["test"]],"exemplars":_exemplars(r["niche"])}

if __name__=="__main__":
    import json,sys
    demo_text=("Pflegefachkraft (m/w/d) gesucht! Werde Teil unseres Teams in der Altenpflege. "
        "Vollzeit oder Teilzeit, faire Bezahlung, unbefristet. Bewirb dich jetzt in 2 Minuten.")
    print(json.dumps(analyze_text(demo_text,"Pflege Recruiting"),ensure_ascii=False,indent=1))
