"""PER-NICHE RECOMMENDATION GENERATOR — the product loop, end to end, from the 196k funnels only.
 funnel -> classify niche (+confidence) -> within-niche percentile -> ranked 'funnels like yours that
 convert well tend to X' recommendations, split into:
   - Recommended experiments (correlational, niche-aware, framed 'tend to')
   - Test-don't-apply (the FORM: strongest +correlation but A/B-harmful -> never a blind instruction)
 Each rec carries the per-niche direction + how far this funnel sits from its niche's winners.
 Universal factors (sign stable across niches) vs niche-specific (sign flips) are labelled.
Correlational by design (agreed start); flywheel later upgrades strong corrs -> confident causal claims."""
import os, numpy as np, pandas as pd, joblib, json
from pathlib import Path
D=Path(__file__).parent
norm=lambda s: str(s).replace("R: ","R:")   # reconcile 'R: x' vs 'R:x' across scripts
# generated, funnel-specific opener suggestions (round-1: authored in-session; prod swaps a live LLM call)
SUG=json.loads((D/"data/suggestions.json").read_text()) if (D/"data/suggestions.json").exists() else {}
OPENER={"lp_has_question","lp_content_only","lp_media_led"}  # page-1 opener family -> one consolidated rec

# ── CONTENT-RANKER HOOK (opt-in via CONTENT_RANKER=1) ──────────────────────────────
# Orders the generated copy rewrites by the learned win-probability from content_ranker.py
# (validated in content_proposal_backtest.py: OOS AUC 0.571; the signal is the DIRECTION of the
# copy change). This is a PRIORITISER for live A/B tests, NOT blind advice — every suggestion
# still says "A/B-test it", and the live flywheel is what turns these odds into causal claims.
# Off by default so the demo path stays light (no live text-embedder load).
_RANK = os.environ.get("CONTENT_RANKER") == "1"
_ranker = None
def _rank_sug(niche, current, tries):
    global _ranker
    if not _RANK or not current or not tries:
        return [(t, None) for t in tries]
    try:
        if _ranker is None:
            import content_ranker as _ranker
        return sorted([(t, _ranker.score_suggestion(current, t, niche)) for t in tries],
                      key=lambda x: -(x[1] or 0))
    except Exception:
        return [(t, None) for t in tries]

C=joblib.load(D/"data/niche_classifier.pkl"); clf,pca,CLASSES,THR=C["clf"],C["pca"],list(C["classes"]),C["recommend_confirm_below"]
emb=np.load(D/"data/embeddings.npy")
_idsrc="data/funnel_meta.csv" if (D/"data/funnel_meta.csv").exists() else "data/funnel_content.csv"
ids=pd.read_csv(D/_idsrc,usecols=["campaignVersionId"]).reset_index(drop=True)
emap={v:i for i,v in enumerate(ids.campaignVersionId.values)}
M=pd.read_csv(D/"data/per_niche_drivers.csv",index_col=0); M.columns=[norm(c) for c in M.columns]

dc=pd.read_csv(D/"data/deep_composition_features.csv")
v1=pd.read_csv(D/"data/funnel_features_v1.csv")[["campaignVersionId","n_result_pages","q_media","q_text",
   "q_choice","q_form","n_form_fields","n_buttons","n_social","n_media","n_components","has_branching"]]
F=dc.merge(v1,on="campaignVersionId").copy(); F["niche"]=F.niche.map(norm)
F=F[(F.visitors>=500)&F.cvr.notna()&F.niche.notna()]
# per-niche stats: winner-norm (top-quartile CVR median), niche std, niche median CVR + percentile lookup
NWIN,NSTD,NMED={},{},{}
for nm,g in F.groupby("niche"):
    w=g[g.cvr>=g.cvr.quantile(0.75)]
    NWIN[nm]=w.median(numeric_only=True); NSTD[nm]=g.std(numeric_only=True)+1e-9; NMED[nm]=g.cvr.median()
SORTED_CVR={nm:np.sort(g.cvr.values) for nm,g in F.groupby("niche")}

THRC=0.04   # min |within-niche corr| to treat as a real direction
PH={ "first_form_relpos":("push the form later","move the form earlier so visitors reach it sooner"),
 "lp_has_question":("open page 1 with a question instead of a static intro",""),
 "lp_content_only":("","replace the text-only page-1 intro with an interactive question"),
 "lp_media_led":("","stop leading page 1 with a large media/hero block"),
 "q_first_half":("front-load more of your questions into the first half of the funnel",""),
 "n_result_pages":("add a personalised result / outcome step",""),
 "has_branching":("add branching so the path adapts to answers",""),
 "lp_media":("add a video or image to page 1","remove media from page 1"),
 "media_per_page":("add more visuals across pages","cut media density across pages"),
 "lp_social":("add social proof to page 1","reduce social-proof clutter on page 1"),
 "lp_buttons":("add a clear CTA button to page 1","reduce the number of buttons on page 1"),
 "q_choice":("add a choice / multiple-choice question","use fewer choice questions"),
 "q_text":("add a short open-text question","use fewer open-text questions"),
 "q_form":("winners ask MORE in the form","winners ask LESS in the form"),
 "n_form_fields":("winners use MORE form fields","winners use FEWER form fields")}
FORM={"q_form","n_form_fields","lp_is_form"}
# universal (sign stable) vs niche-specific (flips), from the matrix
def flips(f):
    r=M.loc[f].dropna(); return (r>=THRC).sum()>0 and (r<=-THRC).sum()>0
UNIV={f:(not flips(f)) for f in PH if f in M.index}

def classify(emb_vec):
    p=clf.predict_proba(pca.transform(emb_vec.reshape(1,-1)))[0]
    o=np.argsort(-p); return CLASSES[o[0]], float(p[o[0]]), [(CLASSES[i],float(p[i])) for i in o[:3]]

def pct_in_niche(niche,cvr):
    a=SORTED_CVR.get(niche);  return None if a is None else float(np.searchsorted(a,cvr)/len(a))

def recommend(cvid,topn=5):
    if cvid not in emap or cvid not in set(F.campaignVersionId): return None
    niche,conf,top3=classify(emb[emap[cvid]])
    row=F[F.campaignVersionId==cvid].iloc[0]
    win,std=NWIN.get(niche),NSTD.get(niche)
    recs=[]
    if win is not None:
        for f,(inc,dec) in PH.items():
            if f not in M.index or pd.isna(M.loc[f,niche]) or abs(M.loc[f,niche])<THRC: continue
            corr=M.loc[f,niche]; val=row.get(f,np.nan); wv=win.get(f,np.nan)
            if pd.isna(val) or pd.isna(wv): continue
            gap=(wv-val) if corr>0 else (val-wv)        # how far below the winner level (in the good direction)
            if gap<=0: continue
            z=abs(gap)/float(std.get(f,1.0));
            if z<0.15: continue
            text=inc if corr>0 else dec
            if not text: continue
            recs.append(dict(feat=f,text=text,priority=abs(corr)*min(z,3),corr=round(float(corr),3),
                             form=f in FORM,universal=UNIV.get(f,False)))
    recs.sort(key=lambda r:-r["priority"])
    # consolidate the 3 page-1 opener recs into ONE actionable rec + attach the funnel-specific suggestion
    op=[r for r in recs if r["feat"] in OPENER]
    if op:
        best=max(op,key=lambda r:r["priority"])
        recs=[r for r in recs if r["feat"] not in OPENER]+[dict(feat="opener",
            text="Rework your page-1 opener — lead with one interactive question instead of a static hero/intro",
            priority=best["priority"]+1, corr=best["corr"], form=False, universal=True)]
        recs.sort(key=lambda r:-r["priority"])
    # attach the funnel-specific generated suggestion to each rec by its feature (opener/q_text/q_choice/…)
    fsug=SUG.get(cvid,{})
    for r in recs: r["suggestion"]=fsug.get(r["feat"])
    exp=[r for r in recs if not r["form"]][:topn]
    test=[r for r in recs if r["form"]][:2]
    return dict(cvid=cvid,niche=niche,conf=conf,top3=top3,cvr=float(row.cvr),
                pct=pct_in_niche(niche,row.cvr),niche_median=NMED.get(niche),exp=exp,test=test)

def render(r):
    if r is None: return "  (funnel not in dataset)"
    L=[f"\nFUNNEL {r['cvid']}",
       f"  niche: {r['niche']}  (confidence {r['conf']*100:.0f}%{' — ASK USER to confirm' if r['conf']<THR else ''})",
       f"  within-niche conversion percentile: {r['pct']*100:.0f}th  (this funnel {r['cvr']*100:.2f}% vs niche median {r['niche_median']*100:.2f}%)"]
    if r['conf']<THR: L.append("  alt niches: "+", ".join(f"{n} {p*100:.0f}%" for n,p in r['top3'][1:]))
    L.append("  Recommended experiments (funnels like yours that convert well tend to…):")
    for x in (r['exp'] or [["—"]]):
        if not isinstance(x,dict): L.append("    • (none above threshold)"); continue
        L.append(f"    • {x['text']}   [{'universal' if x['universal'] else 'niche-specific'}, niche-corr {x['corr']:+.2f}]")
        if x.get("suggestion"):
            sug=x["suggestion"]
            if sug.get("current"): L.append(f"        current: {sug['current']}")
            for t,prob in _rank_sug(r['niche'], sug.get('current'), sug['try']):
                tag=f"   [win-prob {prob*100:.0f}% — A/B-test]" if prob is not None else ""
                L.append(f"        try something like: {t}{tag}")
    if r['test']:
        L.append("  Test, don't apply (strong correlation, but our A/B data shows these often backfire):")
        for x in r['test']: L.append(f"    • {x['text']} → A/B-test it   [niche-corr {x['corr']:+.2f}]")
    return "\n".join(L)

if __name__=="__main__":
    print(f"loaded: {len(CLASSES)} niches | universal factors: {[f for f,u in UNIV.items() if u]}")
    # demo: lowest-percentile funnels (most to gain) from a few illustrative niches
    demo=[]
    for nm in ["Coaching / Webinar","Real Estate","Sales / Lead-gen","R:Nursing & care"]:
        g=F[(F.niche==nm)&(F.visitors>=2000)].sort_values("cvr")
        if len(g): demo.append(g.iloc[max(0,int(len(g)*0.15))].campaignVersionId)  # a low (15th pct) funnel
    for cvid in demo: print(render(recommend(cvid)))
