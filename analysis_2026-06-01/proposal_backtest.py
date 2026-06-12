"""PROPOSAL-VALIDITY BACKTEST — the linchpin pre-flight test (SHIP_PLAN §2.1, §7 gate 3).

Question: would the recommender's proposed changes actually WIN in real A/B tests, or do they
underperform the 27.1% challenger-win baseline (Goodhart: descriptive score != causal advice)?

Three nested tests on the 9,935 historically-linked A/B tests (control vs variant PAGE, kept_original verdict):
 1. NAIVE single-rule recs (re-stated from causal_diff): do individual "winner" edits beat baseline?
 2. SCORE-DIRECTION: when the variant moves toward what the FUNNEL SCORE prefers (its M2 structural
    drivers), does it win > baseline? If not -> optimising our score LOSES A/B tests (Goodhart, measured).
 3. CAUSAL CHANGE-MODEL: can a model trained on REAL outcomes (X = variant-control feature deltas,
    GroupKFold by account) identify winning changes with confidence > baseline? This is the only path
    to a pre-trained recommender prior; if it can't, recommendations require LIVE AI-led testing.

All local, no prod, no new data. kept_original is a noisy proxy, diffs are multi-variable, n per cell small
-> directional, not definitive. Honest by construction."""
import numpy as np, pandas as pd, json
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import cross_val_predict, GroupKFold
from sklearn.metrics import roc_auc_score
from pathlib import Path
D=Path(__file__).parent

FEATS=["n_components","q_media","q_text","q_choice","q_form","inputs","buttons","social","media"]
pf=pd.read_csv(D/"data/abtest_pagefeats.csv",dtype={"pageId":str}).drop_duplicates("pageId").set_index("pageId")
m=pd.read_csv(D/"data/causal_linked.csv",dtype={"campaignId":str,"control":str,"variant":str})
m["won"]=m.won.astype(str).str.lower().eq("true")
m=m[m.control.isin(pf.index)&m.variant.isin(pf.index)].reset_index(drop=True)
C=pf.loc[m.control,FEATS].reset_index(drop=True); V=pf.loc[m.variant,FEATS].reset_index(drop=True)
delta=(V-C); delta.columns=[f"d_{c}" for c in FEATS]
base=m.won.mean(); n=len(m)
print(f"{n:,} linked A/B tests | baseline challenger-win = {100*base:.1f}%\n")

def wr(mask,label):
    k=int(mask.sum())
    if k<40: return
    w=100*m.won[mask].mean(); print(f"  {w:5.1f}%  (n={k:>5}, {w-100*base:+.1f}pp)  {label}")

# ---- TEST 1: naive single-rule recs (does the descriptive playbook win?) ----
print("=== 1) NAIVE single-rule recs: win-rate when variant makes the 'recommended' edit ===")
rules={"variant adds a form-question":delta.d_q_form>0,"variant adds input fields":delta.d_inputs>0,
 "variant adds any question":delta[["d_q_media","d_q_text","d_q_choice","d_q_form"]].sum(1)>0,
 "variant adds social proof":delta.d_social>0,"variant adds a CTA/button":delta.d_buttons>0,
 "variant adds media":delta.d_media>0,"variant adds components (richer)":delta.d_n_components>0,
 "variant removes a form-question":delta.d_q_form<0,"variant leaner (fewer components)":delta.d_n_components<0}
for lbl,msk in rules.items(): wr(msk,lbl)

# ---- TEST 2: SCORE-DIRECTION (Goodhart check) ----
# weight page features by the funnel score's M2 structural permutation-importances
W={"q_form":0.052,"inputs":0.047,"buttons":0.023,"n_components":0.011,"q_text":0.008,"social":0.007,
   "q_media":0.0,"q_choice":0.0,"media":0.0}
align=sum(W[c]*delta[f"d_{c}"] for c in FEATS)   # >0 => variant moves TOWARD what the score rewards
print(f"\n=== 2) SCORE-DIRECTION: does moving toward the funnel score's preference win? ===")
wr(align>0,"variant MORE score-preferred than control")
wr(align<0,"variant LESS score-preferred (against the score)")
# top-quartile strongest score-aligned moves
q=align[align>0].quantile(0.75) if (align>0).any() else 0
wr(align>=q,"strongest score-aligned moves (top quartile of +align)")

# ---- TEST 3: CAUSAL CHANGE-MODEL (can we learn winners from real outcomes?) ----
print(f"\n=== 3) CAUSAL CHANGE-MODEL: learn won ~ (variant-control deltas + control context), GroupKFold by account ===")
X=pd.concat([delta, C.add_prefix("c_")],axis=1).values; y=m.won.values; grp=m.campaignId.values
gkf=GroupKFold(n_splits=5)
clf=HistGradientBoostingClassifier(max_iter=300,learning_rate=0.05,max_depth=4,l2_regularization=1.0,random_state=0)
p=cross_val_predict(clf,X,y,cv=gkf,groups=grp,method="predict_proba",n_jobs=-1)[:,1]
auc=roc_auc_score(y,p)
print(f"  out-of-fold AUC = {auc:.3f}   (0.5 = change-features carry NO signal about who wins)")
order=np.argsort(-p)
for frac in (0.05,0.10,0.20):
    k=int(n*frac); topwr=100*y[order[:k]].mean()
    print(f"  top {int(frac*100):>2}% most-confident predicted winners (n={k}): win-rate {topwr:.1f}%  ({topwr-100*base:+.1f}pp)")
# decile calibration
dec=pd.qcut(p,10,labels=False,duplicates="drop")
cal=pd.DataFrame({"dec":dec,"won":y}).groupby("dec").won.agg(["mean","size"])
print("  win-rate by predicted-prob decile (0=lowest .. 9=highest):")
print("   ",", ".join(f"d{int(i)}:{100*r['mean']:.0f}%" for i,r in cal.iterrows()))

out={"n":int(n),"baseline_winrate":round(100*base,1),"causal_model_auc":round(float(auc),3),
     "top10pct_winrate":round(float(100*y[order[:int(n*0.10)]].mean()),1),
     "score_direction_winrate":round(float(100*m.won[align>0].mean()),1)}
(D/"data/proposal_backtest.json").write_text(json.dumps(out,indent=2))
print("\nsaved -> data/proposal_backtest.json")
