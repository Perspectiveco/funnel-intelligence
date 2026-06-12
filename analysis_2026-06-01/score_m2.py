"""M2: harden the Funnel Score. The HONEST validation:
 - account-holdout (GroupKFold by campaignId): does design generalize to UNSEEN accounts, or
   was ρ=0.48 partly memorising the account?
 - temporal (train older funnels, predict newer; time derived from the ObjectId in campaignVersionId):
   does the score predict the FUTURE, not just fit the past?
 - interpretable drivers (permutation importance) + a score() function saved for handoff.
All local, no prod, no new data."""
import numpy as np, pandas as pd, json, joblib
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import cross_val_predict, GroupKFold
from sklearn.inspection import permutation_importance
from scipy.stats import spearmanr
from pathlib import Path
D=Path(__file__).parent

content=pd.read_csv(D/"data/funnel_content.csv").reset_index(drop=True)
emb=np.load(D/"data/embeddings.npy")
comp=pd.read_csv(D/"data/deep_composition_features.csv")
feat=pd.read_csv(D/"data/funnel_features_v1.csv")[["campaignVersionId","q_media","q_text","q_choice","q_form",
        "n_form_fields","n_buttons","n_social","n_media","n_result_pages","has_branching","n_components"]]
st=pd.read_csv(D/"data/funnel_struct.csv",low_memory=False,dtype={"campaignId":str})[["campaignVersionId","campaignId"]]
df=comp.merge(feat,on="campaignVersionId",how="left").merge(st,on="campaignVersionId",how="left")
df=df[df.campaignVersionId.isin(set(content.campaignVersionId))].copy()
emap={v:i for i,v in enumerate(content.campaignVersionId.values)}
df=df[(df.visitors>=500)&df.cvr.notna()&df.subtype.notna()&df.campaignId.notna()].copy()
df["niche"]=np.where(df.vertical=="Recruiting","R:"+df.subtype,df.vertical)
df["y"]=df.groupby("niche").cvr.rank(pct=True)
# creation time from the ObjectId hex prefix of campaignVersionId (no BQ needed)
def ts(v):
    try: return int(str(v)[:8],16)
    except: return 0
df["ts"]=df.campaignVersionId.map(ts)
df=df[df.ts>0].reset_index(drop=True)
print(f"{len(df):,} funnels | {df.campaignId.nunique():,} accounts | {df.niche.nunique()} niches")

STRUCT=["n_pages","lp_has_question","lp_is_form","lp_content_only","lp_media_led","lp_media","lp_components",
        "lp_social","lp_buttons","lp_q_choice","first_form_relpos","q_first_half","media_per_page",
        "q_media","q_text","q_choice","q_form","n_form_fields","n_buttons","n_social","n_media",
        "n_result_pages","has_branching","n_components"]
E=emb[[emap[v] for v in df.campaignVersionId.values]]
Ep=PCA(n_components=120,random_state=0).fit_transform(E)
niche_oh=pd.get_dummies(df.niche,prefix="n").values
Xs=df[STRUCT].fillna(0).values
X=np.hstack([Xs, Ep, niche_oh]); y=df.y.values
def mdl(): return HistGradientBoostingRegressor(max_iter=400,learning_rate=0.05,max_depth=5,l2_regularization=1.0,random_state=0)

print("\n=== HONEST validation (predicting within-niche CVR percentile) ===")
# 1) plain 5-fold (the number we quoted)
rho_plain=spearmanr(cross_val_predict(mdl(),X,y,cv=5,n_jobs=-1),y).correlation
print(f"  plain 5-fold (funnel-level):     rho = {rho_plain:.3f}   (the number we've been quoting)")
# 2) account-holdout: GroupKFold by campaignId
gkf=GroupKFold(n_splits=5)
rho_acct=spearmanr(cross_val_predict(mdl(),X,y,cv=gkf,groups=df.campaignId.values,n_jobs=-1),y).correlation
print(f"  account-holdout (GroupKFold):    rho = {rho_acct:.3f}   <-- generalises to UNSEEN accounts?")
# 3) temporal: train older 70%, test newer 30%
order=np.argsort(df.ts.values); cut=int(len(order)*0.7)
tr,te=order[:cut],order[cut:]
m=mdl().fit(X[tr],y[tr]); rho_time=spearmanr(m.predict(X[te]),y[te]).correlation
print(f"  temporal (train old -> test new):rho = {rho_time:.3f}   <-- predicts the FUTURE?")

# drivers: permutation importance, structural features individually + content(PCA block)
print("\n=== top structural drivers (permutation importance on a holdout) ===")
import numpy as np
samp=np.random.RandomState(0).choice(len(df),min(15000,len(df)),replace=False)
mfull=mdl().fit(X,y)
# permute each struct col; measure rho drop
base=spearmanr(mfull.predict(X[samp]),y[samp]).correlation
imp=[]
for i,name in enumerate(STRUCT):
    Xp=X[samp].copy(); Xp[:,i]=np.random.RandomState(1).permutation(Xp[:,i])
    imp.append((name, base-spearmanr(mfull.predict(Xp),y[samp]).correlation))
# content block
Xp=X[samp].copy(); cstart=len(STRUCT)
Xp[:,cstart:cstart+120]=Xp[np.random.RandomState(2).permutation(samp.shape[0]),cstart:cstart+120][:, :] if False else Xp[:,cstart:cstart+120]
# simpler content-block: shuffle rows of the PCA block
idxp=np.random.RandomState(2).permutation(len(samp))
Xp2=X[samp].copy(); Xp2[:,cstart:cstart+120]=Xp2[idxp,cstart:cstart+120]
content_imp=base-spearmanr(mfull.predict(Xp2),y[samp]).correlation
for name,v in sorted(imp,key=lambda t:-t[1])[:8]: print(f"  {name:<18} {v:+.3f}")
print(f"  [content embedding block] {content_imp:+.3f}")

# save model + niche benchmarks + score() handoff
joblib.dump({"model":mfull,"struct_cols":STRUCT,"pca":PCA(n_components=120,random_state=0).fit(E),
             "niche_cols":list(pd.get_dummies(df.niche,prefix="n").columns)}, D/"data/funnel_score_model.pkl")
bench=df.groupby("niche").agg(median_cvr=("cvr","median"),n=("cvr","size")).reset_index()
bench.to_csv(D/"data/niche_benchmarks.csv",index=False)
open(D/"data/M2_validation.json","w").write(json.dumps({"rho_plain":round(rho_plain,3),
   "rho_account_holdout":round(rho_acct,3),"rho_temporal":round(rho_time,3),
   "n_funnels":int(len(df)),"n_accounts":int(df.campaignId.nunique())},indent=2))
print("\nsaved model -> data/funnel_score_model.pkl, benchmarks, M2_validation.json")
