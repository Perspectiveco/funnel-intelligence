"""Block COMPOSITION + SEQUENCE: classify each page into an archetype from its block mix,
then test which OPENING archetype and which first-3-page SEQUENCES win (within-niche CVR)."""
import pandas as pd, numpy as np
from pathlib import Path
from collections import Counter
D=Path(__file__).parent

pf=pd.read_csv(D/"data/page_features.csv",low_memory=False).sort_values(["campaignVersionId","position"])
def arch(r):
    if r.isResult is True or r.isResult=="true": return "result"
    if r.q_form>0 or r.inputs>0: return "FORM"
    if r.q_media>0: return "Qmedia"
    if r.q_choice>0: return "Qchoice"
    if r.q_text>0:   return "Qtext"
    if r.media>0:    return "content+media"
    return "content/text"
pf["arch"]=pf.apply(arch,axis=1)
print("=== page-archetype frequency (all pages) ===")
for a,n in pf.arch.value_counts().items(): print(f"  {n:>9,}  {a}")

seq=pf.groupby("campaignVersionId").arch.apply(list)
opening=seq.apply(lambda s:s[0] if s else None)
first3=seq.apply(lambda s:" → ".join(s[:3]))
F=pd.DataFrame({"campaignVersionId":seq.index,"opening":opening.values,"first3":first3.values})

ver=pd.read_csv(D/"data/funnel_vertical_v2.csv")[["campaignVersionId","vertical","subtype"]]
st=pd.read_csv(D/"data/funnel_struct.csv",low_memory=False)[["campaignVersionId","visitors","cvr"]]
F=F.merge(ver,on="campaignVersionId").merge(st,on="campaignVersionId")
F=F[(F.visitors>=500)&F.cvr.notna()&F.subtype.notna()].copy()
F["niche"]=np.where(F.vertical=="Recruiting","R: "+F.subtype,F.vertical)
F["y"]=F.groupby("niche").cvr.rank(pct=True)   # within-niche CVR percentile (0..1)

print(f"\n=== OPENING-PAGE archetype -> avg within-niche CVR percentile (n>=300) ===")
g=F.groupby("opening").agg(n=("y","size"),winpct=("y","mean")).query("n>=300").sort_values("winpct",ascending=False)
for a,r in g.iterrows(): print(f"  {100*r.winpct:5.1f}th pct  (n={int(r.n):>5})  open with: {a}")

print(f"\n=== first-3-page SEQUENCE motifs -> within-niche CVR percentile (n>=150) ===")
g2=F.groupby("first3").agg(n=("y","size"),winpct=("y","mean")).query("n>=150").sort_values("winpct",ascending=False)
print("  TOP (winning) sequences:")
for s,r in g2.head(6).iterrows(): print(f"    {100*r.winpct:5.1f}th pct (n={int(r.n):>4})  {s}")
print("  BOTTOM (losing) sequences:")
for s,r in g2.tail(6).iterrows(): print(f"    {100*r.winpct:5.1f}th pct (n={int(r.n):>4})  {s}")
F.to_csv(D/"data/page_archetype_seq.csv",index=False)
