"""Hypothesis 2: optimal funnel length is sub-type-specific (recruiting).
CVR vs n_pages per sub-type: trend strength, interior peak (inverted-U), optimal bucket."""
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from scipy.stats import spearmanr
from pathlib import Path
D=Path(".")

s=pd.read_csv("data/funnel_struct.csv")      # campaignVersionId, campaignId, visitors, cvr, n_pages, n_result_pages
v=pd.read_csv("data/funnel_vertical_v2.csv")[["campaignVersionId","vertical","subtype"]]
df=s.merge(v,on="campaignVersionId")
df=df[(df.vertical=="Recruiting") & (df.visitors>=500) & df.n_pages.between(1,40)].copy()
print(f"recruiting funnels >=500 visitors with pages: {len(df):,}\n")

# page buckets
bins=[0,4,7,10,13,16,20,100]; labels=["1-4","5-7","8-10","11-13","14-16","17-20","21+"]
df["pb"]=pd.cut(df.n_pages,bins=bins,labels=labels)

# per-subtype summary: trend + interior peak via quadratic on ln(cvr)
rows=[]
for st,sub in df.groupby("subtype"):
    if len(sub)<300: continue
    sub=sub[sub.cvr>0]
    rho,p=spearmanr(sub.n_pages,sub.cvr)
    # quadratic fit ln(cvr) ~ a*x^2 + b*x + c
    x=sub.n_pages.values.astype(float); y=np.log(sub.cvr.values)
    a,b,cc=np.polyfit(x,y,2)
    peak=(-b/(2*a)) if a<0 else np.nan   # interior max only if concave (a<0)
    # median CVR by bucket -> peak bucket
    mb=sub.groupby("pb",observed=True).cvr.median()
    peak_bucket=mb.idxmax() if len(mb) else None
    rows.append(dict(subtype=st,n=len(sub),spearman=round(rho,3),p=round(p,4),
                     shape=("inverted-U" if a<0 else "monotonic/U"),
                     interior_peak_pages=(round(peak,1) if a<0 and 1<peak<40 else None),
                     best_bucket=peak_bucket,
                     med_cvr_at_best=round(100*mb.max(),2) if len(mb) else None))
summ=pd.DataFrame(rows).sort_values("n",ascending=False)
summ.to_csv("data/h2_subtype.csv",index=False)
pd.set_option("display.width",200)
print(summ.to_string(index=False))

# chart: CVR-vs-length curves for the largest contrasting sub-types
focus=summ.nlargest(6,"n").subtype.tolist()
fig,ax=plt.subplots(figsize=(9,5.5))
for st in focus:
    sub=df[df.subtype==st]
    m=sub.groupby("pb",observed=True).agg(cvr=("cvr","median"),n=("cvr","size"))
    m=m[m.n>=20]
    ax.plot(m.index.astype(str),100*m.cvr,marker="o",label=f"{st} (n={len(sub)})")
ax.set_xlabel("Funnel length (pages)"); ax.set_ylabel("Median CVR (%)")
ax.set_title("Hypothesis 2: CVR-vs-length curve differs by recruiting sub-type\n(each line a sub-type; peaks at different lengths)")
ax.legend(fontsize=8); ax.grid(alpha=0.3)
fig.tight_layout();fig.savefig("charts/10_h2_length_by_subtype.png",dpi=130);plt.close()
print("\nchart saved: charts/10_h2_length_by_subtype.png")
