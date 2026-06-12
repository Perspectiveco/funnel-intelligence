"""score() wrapper over the saved M2 model — predicts a NEW funnel's WITHIN-NICHE conversion
percentile (0..1) from its structural features + content embedding + niche. This is the production
new-funnel path (existing funnels have an actual percentile; new ones get this prediction).
Validated OOS at rho=0.40 acct-holdout / 0.48 temporal (see M2_validation.json)."""
import numpy as np, pandas as pd, joblib
from pathlib import Path
D=Path(__file__).parent
_B=joblib.load(D/"data/funnel_score_model.pkl")
MODEL,STRUCT,PCA_,NICHE_COLS=_B["model"],_B["struct_cols"],_B["pca"],_B["niche_cols"]

def score(struct:dict, embedding:np.ndarray, niche:str)->float:
    """struct: {feature_name: value} (missing -> 0); embedding: raw 384-d content vector; niche: label."""
    xs=np.array([[float(struct.get(c,0) or 0) for c in STRUCT]])
    ep=PCA_.transform(np.asarray(embedding,dtype=float).reshape(1,-1))
    col=f"n_{niche}"
    oh=np.array([[1.0 if c==col else 0.0 for c in NICHE_COLS]])
    if oh.sum()==0: oh[:] = 0  # unseen niche -> all-zero (model falls back to struct+content)
    return float(np.clip(MODEL.predict(np.hstack([xs,ep,oh]))[0],0,1))

if __name__=="__main__":   # smoke test on a few real funnels (their features + embedding from disk)
    emb=np.load(D/"data/embeddings.npy")
    ids=pd.read_csv(D/"data/funnel_content.csv",usecols=["campaignVersionId"]).reset_index(drop=True)
    emap={v:i for i,v in enumerate(ids.campaignVersionId.values)}
    dc=pd.read_csv(D/"data/deep_composition_features.csv")
    v1=pd.read_csv(D/"data/funnel_features_v1.csv")[["campaignVersionId","n_result_pages","q_media","q_text",
       "q_choice","q_form","n_form_fields","n_buttons","n_social","n_media","n_components","has_branching"]]
    F=dc.merge(v1,on="campaignVersionId"); F["niche"]=np.where(F.vertical=="Recruiting","R:"+F.subtype.astype(str),F.vertical)
    F=F[(F.visitors>=500)&F.cvr.notna()&F.campaignVersionId.isin(emap)]
    F["actual_pct"]=F.groupby("niche").cvr.rank(pct=True)
    s=F.sample(6,random_state=1)
    print(f"{'predicted':>10} {'actual':>8}  niche")
    for r in s.itertuples():
        p=score({c:getattr(r,c,0) for c in STRUCT}, emb[emap[r.campaignVersionId]], r.niche)
        print(f"{p*100:9.0f}% {r.actual_pct*100:7.0f}%  {r.niche}")
    print("\n(predicted=model on all-data fit, so optimistic for these in-sample rows; OOS rho=0.40 is the honest number)")
