"""Engine B first output: per-funnel retention curves (events-per-page x page order),
aggregated to per-niche drop-off benchmarks."""
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from pathlib import Path
D=Path(__file__).parent

dro=pd.read_csv(D/"dropoff_fast.csv",skiprows=1)        # skip the dbName= line; header is line 2
dro.columns=["campaignVersionId","slug","events"]
pf=pd.read_csv(D/"data/page_features.csv",low_memory=False)[["campaignVersionId","position","slug"]]
ver=pd.read_csv(D/"data/funnel_vertical_v2.csv")[["campaignVersionId","vertical","subtype"]]

# join events -> page order via (version, slug)
m=pf.merge(dro,on=["campaignVersionId","slug"],how="inner")
cov=dro.merge(pf,on=["campaignVersionId","slug"],how="left")
print(f"event rows: {len(dro):,} | joined to a page position: {cov.position.notna().sum():,} ({100*cov.position.notna().mean():.0f}%)")

# base = entry page (min position) events; keep funnels with a real base
base=m.sort_values("position").groupby("campaignVersionId").first().rename(columns={"events":"base_ev"})
m=m.merge(base[["base_ev"]],on="campaignVersionId")
m=m[m.base_ev>=100]                      # enough traffic for a stable curve
m["retention"]=m.events/m.base_ev
m=m[m.retention<=1.2]                    # drop back-nav outliers
print(f"funnels with stable curve (base>=100 views, 7d): {m.campaignVersionId.nunique():,}")

m=m.merge(ver,on="campaignVersionId",how="left")
m["niche"]=np.where(m.vertical=="Recruiting","R: "+m.subtype,m.vertical)

# headline: median retention past page 1 (position 1 vs 0), per niche
p1=m[m.position==1].groupby("niche").retention.median().sort_values()
big=m.groupby("niche").campaignVersionId.nunique()
p1=p1[big.reindex(p1.index)>=30]
print("\n=== median %% of visitors surviving PAST the first page, by niche ===")
for n,v in p1.items(): print(f"  {100*v:5.1f}%  {n}  (n={big[n]})")

# chart 1: per-niche retention curves (positions 0..7) for the 6 biggest niches
top=big.sort_values(ascending=False).head(6).index
fig,ax=plt.subplots(figsize=(9,5.5))
for n in top:
    c=m[(m.niche==n)&(m.position<=7)].groupby("position").retention.median()
    ax.plot(c.index,100*c.values,marker="o",label=f"{n} (n={big[n]})")
ax.set_xlabel("Funnel step (page position)");ax.set_ylabel("% of entry visitors still present (median)")
ax.set_title("Engine B: live per-niche drop-off curves (7-day activities, page-view based)")
ax.legend(fontsize=8);ax.grid(alpha=0.3);ax.set_ylim(0,105)
fig.tight_layout();fig.savefig(D/"charts/12_dropoff_curves.png",dpi=130);plt.close()

# chart 2: first-page survival bar
fig,ax=plt.subplots(figsize=(8,6))
ax.barh(range(len(p1)),100*p1.values,color="#5b5bd6")
ax.set_yticks(range(len(p1)));ax.set_yticklabels(p1.index,fontsize=8)
ax.set_xlabel("% surviving past page 1 (median funnel)")
ax.set_title("First-page retention varies widely by niche")
for i,v in enumerate(p1.values): ax.text(100*v+0.5,i,f"{100*v:.0f}%",va="center",fontsize=8)
fig.tight_layout();fig.savefig(D/"charts/13_firstpage_survival.png",dpi=130);plt.close()
print("\nwrote charts/12_dropoff_curves.png + 13_firstpage_survival.png")
