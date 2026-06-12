"""Hypothesis 1: low-friction framing in recruiting funnels.
Within-subtype comparison (chart) + within-account paired test. Fully local."""
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu, wilcoxon
from pathlib import Path
D=Path(".")

c=pd.read_csv("data/funnel_content.csv")
v=pd.read_csv("data/funnel_vertical_v2.csv")[["campaignVersionId","vertical","subtype"]]
df=c.merge(v,on="campaignVersionId")
df=df[df.vertical=="Recruiting"].copy()
df["content_text"]=df.content_text.fillna("")
pat=(r"ohne lebenslauf|ohne anschreiben|ohne bewerbungsunterlagen|kein lebenslauf|kein anschreiben|"
     r"in nur \d+ (sekunden|minuten)|wenigen sekunden|\d+ sekunden|express.?bewerb|blitz.?bewerb|"
     r"schnell bewerben|unkompliziert bewerben|without (a )?(cv|resume)|no (cv|resume)|"
     r"apply in \d+ seconds|quick apply|60 seconds")
df["lf"]=df.content_text.str.contains(pat,case=False,regex=True,na=False)

# ---- within-subtype (>=500 visitors) ----
big=df[df.visitors>=500]
rows=[]
for st,sub in big.groupby("subtype"):
    a=sub[sub.lf].cvr.values; b=sub[~sub.lf].cvr.values
    if len(a)<30 or len(b)<30: continue
    p=mannwhitneyu(a,b,alternative="two-sided").pvalue
    rows.append(dict(subtype=st,n_lf=len(a),n_no=len(b),
                     delta=100*(np.median(a)-np.median(b)),p=p))
res=pd.DataFrame(rows).sort_values("delta")
res.to_csv("data/h1_subtype.csv",index=False)

# diverging bar chart
fig,ax=plt.subplots(figsize=(9,7))
colors=["#2e8b57" if d>0 else "#c0392b" for d in res.delta]
alphas=[1.0 if p<0.05 else 0.35 for p in res.p]
bars=ax.barh(res.subtype,res.delta,color=colors)
for bar,al in zip(bars,alphas): bar.set_alpha(al)
ax.axvline(0,color="#333",lw=1)
for y,(d,p) in enumerate(zip(res.delta,res.p)):
    star="*" if p<0.05 else ""
    ax.text(d+(0.02 if d>=0 else -0.02),y,f"{d:+.2f}{star}",va="center",
            ha="left" if d>=0 else "right",fontsize=8)
ax.set_xlabel("CVR difference: low-friction framing minus none (percentage points)")
ax.set_title("Hypothesis 1: 'Apply fast, no CV' framing — helps trades, hurts care/credentialed roles\n"
             "Green=helps, Red=hurts. Solid=significant (p<0.05), faded=not. Recruiting funnels >=500 visitors.")
ax.margins(x=0.18)
fig.tight_layout();fig.savefig("charts/09_h1_lowfriction_by_subtype.png",dpi=130);plt.close()
print("chart saved. subtype table:")
print(res.assign(delta=res.delta.round(2),p=res.p.round(4)).to_string(index=False))

# ---- within-account paired test ----
cm=Path("data/cvid_campaign.csv")
if cm.exists() and cm.stat().st_size>1000:
    camp=pd.read_csv("data/cvid_campaign.csv")
    dd=df[df.visitors>=200].merge(camp,on="campaignVersionId")
    g=dd.groupby("campaignId").agg(cvr_lf=("cvr",lambda s:s[dd.loc[s.index,"lf"]].mean()),
                                   cvr_no=("cvr",lambda s:s[~dd.loc[s.index,"lf"]].mean()),
                                   n_lf=("lf","sum"),n_tot=("lf","count"))
    paired=g[(g.n_lf>=1)&(g.n_lf<g.n_tot)].dropna(subset=["cvr_lf","cvr_no"])
    diff=(paired.cvr_lf-paired.cvr_no).values
    w=wilcoxon(diff).pvalue if len(diff)>10 else float("nan")
    print(f"\n=== WITHIN-ACCOUNT PAIRED (same company ran both framed & unframed, >=200 visitors) ===")
    print(f"campaigns: {len(paired):,}")
    print(f"avg framed CVR:   {100*paired.cvr_lf.mean():.2f}%")
    print(f"avg unframed CVR: {100*paired.cvr_no.mean():.2f}%")
    print(f"avg within-account delta: {100*np.mean(diff):+.3f}pp")
    print(f"framed wins: {(diff>0).mean()*100:.1f}%   Wilcoxon p={w:.4f}")
else:
    print("\n(cvid_campaign.csv not ready yet — paired test skipped)")
