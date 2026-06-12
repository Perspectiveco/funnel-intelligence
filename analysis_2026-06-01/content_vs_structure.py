"""How much is within-niche CVR predictable from DESIGN — and structure vs content vs both?
Target = within-niche CVR percentile. Features: structural composition | copy embedding | both.
5-fold CV, Spearman(pred, actual). Quantifies content x component."""
import numpy as np, pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import cross_val_predict
from scipy.stats import spearmanr
from pathlib import Path
D=Path(__file__).parent

content=pd.read_csv(D/"data/funnel_content.csv")          # order matches embeddings.npy
emb=np.load(D/"data/embeddings.npy")
assert len(content)==len(emb), (len(content),len(emb))
content=content.reset_index(drop=True)
emb_df=pd.DataFrame(emb, index=content.campaignVersionId.values)

comp=pd.read_csv(D/"data/deep_composition_features.csv")  # structural composition + niche + cvr + visitors
comp=comp[comp.campaignVersionId.isin(emb_df.index)].copy()
E=emb_df.loc[comp.campaignVersionId.values].values
print(f"{len(comp):,} funnels with structure+content+cvr, >=500 visitors")

# within-niche CVR percentile = the target (removes the niche baseline = the 87% confound)
comp["y"]=comp.groupby("niche").cvr.rank(pct=True)

STRUCT=["n_pages","lp_has_question","lp_is_form","lp_content_only","lp_media_led","lp_media",
        "lp_components","lp_social","lp_buttons","lp_q_choice","first_form_relpos","q_first_half","media_per_page"]
# add niche as one-hot so the model can do niche-specific structure use
niche_oh=pd.get_dummies(comp.niche,prefix="n")
Xs=pd.concat([comp[STRUCT].reset_index(drop=True),niche_oh.reset_index(drop=True)],axis=1).values
Ep=PCA(n_components=50,random_state=0).fit_transform(E)        # copy embedding -> 50 dims
Xc=np.hstack([Ep,niche_oh.values])                            # content + niche
Xb=np.hstack([comp[STRUCT].values,Ep,niche_oh.values])        # both
y=comp.y.values

def evalX(X,label):
    m=HistGradientBoostingRegressor(max_iter=300,learning_rate=0.06,max_depth=4,
                                    l2_regularization=1.0,random_state=0)
    pred=cross_val_predict(m,X,y,cv=5,n_jobs=-1)
    rho=spearmanr(pred,y).correlation
    print(f"  {label:<28} Spearman rho = {rho:.3f}")
    return rho

print("\nPredicting WITHIN-NICHE CVR percentile from design (5-fold CV):")
rn=evalX(niche_oh.values,"niche only (baseline)")
rs=evalX(Xs,"+ structure")
rc=evalX(Xc,"+ content (copy embedding)")
rb=evalX(Xb,"+ structure + content")
print(f"\nLift over niche-only baseline:  structure +{rs-rn:.3f} | content +{rc-rn:.3f} | both +{rb-rn:.3f}")
print(f"Content adds beyond structure: +{rb-rs:.3f}   Structure adds beyond content: +{rb-rc:.3f}")
print(f"\nInterpretation: rho is how well DESIGN orders funnels by conversion WITHIN their niche.")
print(f"(Funnel Score V1 gate from the plan was rho>=0.4.)")
