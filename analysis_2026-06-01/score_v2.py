"""Push the Funnel Score past 0.40: structure + composition/sequence + page-archetype + full content embedding."""
import numpy as np, pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import cross_val_predict
from scipy.stats import spearmanr
from pathlib import Path
D=Path(__file__).parent

content=pd.read_csv(D/"data/funnel_content.csv").reset_index(drop=True)
emb=np.load(D/"data/embeddings.npy")
emap={v:i for i,v in enumerate(content.campaignVersionId.values)}

comp=pd.read_csv(D/"data/deep_composition_features.csv")          # composition + niche + cvr + visitors
feat=pd.read_csv(D/"data/funnel_features_v1.csv")[["campaignVersionId","q_media","q_text","q_choice","q_form",
        "n_form_fields","n_buttons","n_social","n_media","n_result_pages","has_branching","n_components"]]
arch=pd.read_csv(D/"data/page_archetype_seq.csv")[["campaignVersionId","opening"]]
df=comp.merge(feat,on="campaignVersionId",how="left").merge(arch,on="campaignVersionId",how="left")
df=df[df.campaignVersionId.isin(emap)].copy()
df["y"]=df.groupby("niche").cvr.rank(pct=True)
print(f"{len(df):,} funnels")

E=emb[[emap[v] for v in df.campaignVersionId.values]]
niche_oh=pd.get_dummies(df.niche,prefix="n")
arch_oh=pd.get_dummies(df.opening.fillna("none"),prefix="open")
STRUCT=["n_pages","lp_has_question","lp_is_form","lp_content_only","lp_media_led","lp_media","lp_components",
        "lp_social","lp_buttons","lp_q_choice","first_form_relpos","q_first_half","media_per_page",
        "q_media","q_text","q_choice","q_form","n_form_fields","n_buttons","n_social","n_media",
        "n_result_pages","has_branching","n_components"]
Xstruct=np.hstack([df[STRUCT].fillna(0).values, arch_oh.values, niche_oh.values])
Ep=PCA(n_components=120,random_state=0).fit_transform(E)
Xcontent=np.hstack([Ep, niche_oh.values])
Xall=np.hstack([df[STRUCT].fillna(0).values, arch_oh.values, Ep, niche_oh.values])
y=df.y.values

def ev(X,label):
    m=HistGradientBoostingRegressor(max_iter=400,learning_rate=0.05,max_depth=5,l2_regularization=1.0,random_state=0)
    rho=spearmanr(cross_val_predict(m,X,y,cv=5,n_jobs=-1),y).correlation
    print(f"  {label:<42} rho = {rho:.3f}"); return rho
print("Predicting within-niche CVR percentile (5-fold CV):")
ev(niche_oh.values,"niche only")
ev(Xstruct,"structure + composition + archetype")
ev(Xcontent,"content (embedding 120d)")
ev(Xall,"ALL: structure + composition + content")
