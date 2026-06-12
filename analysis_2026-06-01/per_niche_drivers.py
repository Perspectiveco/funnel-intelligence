"""PER-NICHE feature importances — does a factor help in one niche and HURT in another?
If signs flip across niches, GLOBAL feature recommendations are wrong and we must go per-niche.

For each interpretable structural feature, compute its WITHIN-NICHE Spearman correlation with CVR
(visitors>=500), per niche, vs the global correlation. Report: the sign-flip map, and per-niche
top +/- drivers (the seeds for 'funnels like yours that convert well tend to do X'). Correlational
by design (the agreed starting point); the form features carry a known causal warning."""
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from pathlib import Path
D=Path(__file__).parent

dc=pd.read_csv(D/"data/deep_composition_features.csv")
v1=pd.read_csv(D/"data/funnel_features_v1.csv")[["campaignVersionId","n_result_pages","q_media","q_text",
   "q_choice","q_form","n_form_fields","n_buttons","n_social","n_media","n_components","has_branching"]]
df=dc.merge(v1,on="campaignVersionId",how="inner")
df=df[(df.visitors>=500)&df.cvr.notna()&df.niche.notna()].copy()

FEATS=["n_pages","n_result_pages","n_components","has_branching",
   "lp_has_question","lp_is_form","lp_content_only","lp_media_led","lp_media","lp_components","lp_social","lp_buttons",
   "first_form_relpos","q_first_half","media_per_page",
   "q_media","q_text","q_choice","q_form","n_form_fields","n_buttons","n_social","n_media"]
FORM={"q_form","n_form_fields","lp_is_form"}   # causal blocklist (A/B: harmful despite + correlation)

niches=df.niche.value_counts()
niches=niches[niches>=1000].index.tolist()
print(f"{len(df):,} funnels | {len(niches)} niches with n>=1000\n")

# global vs per-niche correlation
glob={f:spearmanr(df[f],df.cvr,nan_policy="omit").correlation for f in FEATS}
M=pd.DataFrame(index=FEATS,columns=niches,dtype=float)
for nm in niches:
    s=df[df.niche==nm]
    for f in FEATS: M.loc[f,nm]=spearmanr(s[f],s.cvr,nan_policy="omit").correlation
M=M.astype(float)

print("=== SIGN-FLIP MAP: does the factor point the same way in every niche? ===")
print("(threshold |rho|>=0.04 to count as a real direction)\n")
flip=[]
for f in FEATS:
    row=M.loc[f].dropna()
    pos=(row>=0.04).sum(); neg=(row<=-0.04).sum()
    flips = pos>0 and neg>0
    if flips: flip.append((f,pos,neg))
    tag=" <-- FLIPS" if flips else ""
    warn=" [FORM: A/B-harmful]" if f in FORM else ""
    print(f"  {f:<18} global rho={glob[f]:+.3f} | +dir in {pos:>2} niches, -dir in {neg:>2}{tag}{warn}")
print(f"\n  {len(flip)} of {len(FEATS)} factors FLIP SIGN across niches "
      f"-> a global recommendation would be WRONG for those in at least one niche.\n")

# per-niche top drivers (recommendation seeds)
def show(nm):
    row=M[nm].dropna().sort_values()
    print(f"--- {nm}  (n={int((df.niche==nm).sum()):,}, median CVR {100*df[df.niche==nm].cvr.median():.2f}%) ---")
    print("   winners tend to have MORE of:", ", ".join(f"{f}({row[f]:+.2f})"+("*" if f in FORM else "")
        for f in row.index[::-1][:4]))
    print("   winners tend to have LESS of:", ", ".join(f"{f}({row[f]:+.2f})"+("*" if f in FORM else "")
        for f in row.index[:4]))
print("=== per-niche recommendation seeds (top +/- correlated factors; * = form, needs A/B not blind apply) ===\n")
for nm in ["Coaching / Webinar","Real Estate","R:Nursing & care","Sales / Lead-gen",
           "R:Drivers (LKW)","Solar / Energy"]:
    if nm in niches: show(nm)

M.round(3).to_csv(D/"data/per_niche_drivers.csv")
print("\nsaved per-niche correlation matrix -> data/per_niche_drivers.csv")
