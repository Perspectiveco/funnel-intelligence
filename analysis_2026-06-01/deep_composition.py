"""Deeper than counts: landing-page COMPOSITION + form placement + question front-loading,
contrasted winners vs losers WITHIN niche (CVR outcome, full 196K funnels)."""
import pandas as pd, numpy as np
from scipy.stats import mannwhitneyu
from pathlib import Path
D=Path(__file__).parent

pf=pd.read_csv(D/"data/page_features.csv",low_memory=False).sort_values(["campaignVersionId","position"])
qcols=["q_media","q_text","q_choice","q_form"]
pf["q_any"]=pf[qcols].sum(axis=1)
pf["is_form_page"]=((pf.q_form>0)|(pf.inputs>0)).astype(int)

rows=[]
for vid,g in pf.groupby("campaignVersionId"):
    g=g.reset_index(drop=True); n=len(g); lp=g.iloc[0]
    qtot=g.q_any.sum()
    formpos=g.index[g.is_form_page==1]
    rows.append(dict(
        campaignVersionId=vid, n_pages=n,
        # --- landing page (position 0) composition ---
        lp_has_question=int(lp.q_any>0),
        lp_is_form=int((lp.q_form>0) or (lp.inputs>0)),
        lp_content_only=int(lp.q_any==0 and lp.q_form==0 and lp.inputs==0),
        lp_media=lp.media, lp_components=lp.n_components, lp_social=int(lp.social>0),
        lp_buttons=lp.buttons, lp_q_media=lp.q_media, lp_q_choice=lp.q_choice,
        lp_media_led=int(lp.media>0 and lp.q_any==0),     # visual landing, no question
        # --- composition / sequence across the funnel ---
        first_form_relpos=(formpos.min()/(n-1) if len(formpos) and n>1 else 1.0),  # 0=early,1=late
        q_first_half=(g[g.index< n/2].q_any.sum()/qtot if qtot>0 else 0),          # question front-loading
        media_per_page=g.media.sum()/n,
    ))
fdf=pd.DataFrame(rows)
ver=pd.read_csv(D/"data/funnel_vertical_v2.csv")[["campaignVersionId","vertical","subtype"]]
st=pd.read_csv(D/"data/funnel_struct.csv",low_memory=False)[["campaignVersionId","visitors","cvr"]]
fdf=fdf.merge(ver,on="campaignVersionId").merge(st,on="campaignVersionId")
fdf=fdf[(fdf.visitors>=500)&fdf.cvr.notna()&fdf.subtype.notna()].copy()
fdf["niche"]=np.where(fdf.vertical=="Recruiting","R: "+fdf.subtype,fdf.vertical)
fdf.to_csv(D/"data/deep_composition_features.csv",index=False)

FEATS=["lp_has_question","lp_is_form","lp_content_only","lp_media_led","lp_media","lp_components",
       "lp_social","lp_buttons","lp_q_choice","first_form_relpos","q_first_half","media_per_page"]
big=fdf.niche.value_counts(); niches=big[big>=400].index.tolist()
print(f"{len(fdf):,} funnels >=500 visitors, {len(niches)} niches\n")

res=[]
for nm in niches:
    sub=fdf[fdf.niche==nm]; q1,q3=sub.cvr.quantile(.25),sub.cvr.quantile(.75)
    hi,lo=sub[sub.cvr>=q3],sub[sub.cvr<=q1]
    for f in FEATS:
        a,b=hi[f].values,lo[f].values
        if np.nanstd(a)==0 and np.nanstd(b)==0: continue
        U,p=mannwhitneyu(a,b,alternative="two-sided")
        res.append(dict(niche=nm,feature=f,effect=-(1-2*U/(len(a)*len(b))),
                        med_win=np.median(a),med_lose=np.median(b),p=p))
R=pd.DataFrame(res); R.to_csv(D/"data/deep_composition_results.csv",index=False)

# headline cross-niche: how often is each compositional feature a significant winner trait, and which direction
print("=== compositional features: how consistently they separate winners (p<0.01) ===")
sig=R[R.p<0.01]
for f in FEATS:
    s=sig[sig.feature==f]
    pos=(s.effect>0).sum(); neg=(s.effect<0).sum()
    if pos+neg>0:
        med=s.effect.median()
        print(f"  {f:<18} sig in {pos+neg:>2}/{len(niches)} niches | winners↑:{pos} ↓:{neg} | median effect {med:+.2f}")

print("\n=== the landing-page 'opens with a question' effect, per niche ===")
for nm in niches:
    s=sig[(sig.niche==nm)&(sig.feature=='lp_has_question')]
    if len(s):
        r=s.iloc[0]; print(f"  {nm:<34} winners open-with-question {r.med_lose:.0%}->{r.med_win:.0%}  (e={r.effect:+.2f})")
PY