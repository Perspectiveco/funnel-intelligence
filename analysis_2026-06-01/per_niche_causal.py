"""Does 'touching the form hurts' hold across niches? Per-niche challenger-win-rate, form vs non-form changes."""
import re, pandas as pd, numpy as np
from pathlib import Path
D=Path(__file__).parent
feats={}; hexre=re.compile(r"^[0-9a-f]{24},")
for l in open(D/"abtest_pagefeats.csv"):
    if not hexre.match(l): continue
    p=l.strip().split(","); feats[p[0]]=dict(qf=int(p[5]),inp=int(p[6]),qm=int(p[2]),qt=int(p[3]),qc=int(p[4]),
                                              med=int(p[9]),btn=int(p[7]),n=int(p[1]),soc=int(p[8]))
m=pd.read_csv(D/"data/causal_linked.csv",dtype={"control":str,"variant":str})
def dl(r,k): return feats[r.variant][k]-feats[r.control][k]
m["touched_form"]=m.apply(lambda r: dl(r,"qf")!=0 or dl(r,"inp")!=0, axis=1)
m["changed_q"]=m.apply(lambda r: (dl(r,"qm")+dl(r,"qt")+dl(r,"qc"))!=0, axis=1)
m["added_visual"]=m.apply(lambda r: (dl(r,"med")>0 or dl(r,"btn")>0 or dl(r,"n")>0) and not (dl(r,"qf")!=0 or dl(r,"inp")!=0), axis=1)

print(f"overall: {len(m):,} tests, baseline challenger-win {100*m.won.mean():.1f}%")
print(f"  touched form: {100*m[m.touched_form].won.mean():.1f}% (n={m.touched_form.sum()})  | didn't: {100*m[~m.touched_form].won.mean():.1f}%")
print(f"\n=== per niche: form-touch vs not (niches with >=20 form-touch tests) ===")
print(f"{'niche':<34}{'n':>5}{'base':>7}{'formTouch':>11}{'noForm':>9}")
for nm,g in m.dropna(subset=['niche']).groupby('niche'):
    ft=g[g.touched_form]; nf=g[~g.touched_form]
    if len(ft)<20: continue
    print(f"{nm:<34}{len(g):>5}{100*g.won.mean():>6.0f}%{100*ft.won.mean():>10.0f}%{100*nf.won.mean():>8.0f}%")
# is form-touch universally below baseline?
bel=sum(1 for nm,g in m.dropna(subset=['niche']).groupby('niche') if len(g[g.touched_form])>=20 and g[g.touched_form].won.mean()<g.won.mean())
tot=sum(1 for nm,g in m.dropna(subset=['niche']).groupby('niche') if len(g[g.touched_form])>=20)
print(f"\nform-touch below that niche's baseline in {bel}/{tot} niches")
