"""LIVE NICHE CLASSIFIER (SHIP_PLAN §7 gate 2): assign a NEW funnel to one of the 32 benchmark
niches on the fly, with a CONFIDENCE so the UI can ask 'is this your niche?' when unsure.

The niche labels are a 1:1 relabel of the 35 content-embedding clusters (eclusters), so this
classifier recovers the cluster boundaries from the raw embedding -> for a brand-new funnel we get
its niche without re-running the whole clustering+hand-mapping pipeline.
HONEST CAVEAT: 'accuracy' here = agreement with the (self-defined) cluster label, i.e. boundary
sharpness + generalisation to UNSEEN accounts (GroupKFold by campaignId) — NOT external ground truth.
What it genuinely measures: how confidently a new funnel snaps to a single niche, and how often it
sits on a boundary (where we should ask the user). All local, no prod, no new data."""
import numpy as np, pandas as pd, json, joblib
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_predict, GroupKFold
from sklearn.metrics import accuracy_score
from pathlib import Path
D=Path(__file__).parent

content=pd.read_csv(D/"data/funnel_content.csv",usecols=["campaignVersionId"]).reset_index(drop=True)
emb=np.load(D/"data/embeddings.npy")
v2=pd.read_csv(D/"data/funnel_vertical_v2.csv",dtype=str)
st=pd.read_csv(D/"data/funnel_struct.csv",low_memory=False,dtype={"campaignId":str,"campaignVersionId":str})[["campaignVersionId","campaignId"]]
v2["niche"]=np.where(v2.vertical=="Recruiting","R:"+v2.subtype.astype(str),v2.vertical)
emap={v:i for i,v in enumerate(content.campaignVersionId.values)}
df=v2.merge(st,on="campaignVersionId",how="left")
df=df[df.campaignVersionId.isin(emap)&df.campaignId.notna()].drop_duplicates("campaignVersionId").reset_index(drop=True)
X_full=emb[[emap[v] for v in df.campaignVersionId.values]]
pca=PCA(n_components=120,random_state=0).fit(X_full)   # unsupervised -> negligible CV leakage
X=pca.transform(X_full); y=df.niche.values; grp=df.campaignId.values
classes=np.array(sorted(set(y)))
print(f"{len(df):,} funnels | {df.campaignId.nunique():,} accounts | {len(classes)} niches\n")

def clf(): return LogisticRegression(max_iter=400,C=1.0)
gkf=GroupKFold(n_splits=5)
print("=== account-holdout (GroupKFold by campaignId) ===")
proba=cross_val_predict(clf(),X,y,cv=gkf,groups=grp,method="predict_proba",n_jobs=-1)
order_classes=clf().fit(X[:1000],y[:1000]).classes_  # class column order for proba
pred=order_classes[proba.argmax(1)]
top1=accuracy_score(y,pred)
top3=np.mean([yt in order_classes[np.argsort(-row)[:3]] for yt,row in zip(y,proba)])
conf=proba.max(1)
print(f"  top-1 agreement: {100*top1:.1f}%")
print(f"  top-3 agreement: {100*top3:.1f}%")

# confidence gating: where can we auto-assign vs ask the user?
print("\n=== confidence gating (UI: auto-assign above threshold, else ask 'is this your niche?') ===")
for thr in (0.5,0.6,0.7,0.8,0.9):
    msk=conf>=thr
    cov=msk.mean(); acc=accuracy_score(y[msk],pred[msk]) if msk.any() else float("nan")
    print(f"  conf>={thr:.1f}: auto-assigns {100*cov:4.1f}% of funnels @ {100*acc:.1f}% accuracy")

# per-niche recall (where do we misassign most?)
rec=pd.DataFrame({"niche":y,"correct":(pred==y)}).groupby("niche").agg(n=("correct","size"),recall=("correct","mean"))
rec=rec.sort_values("recall")
print("\n=== weakest niches (lowest recall = most boundary confusion) ===")
for nm,r in rec.head(6).iterrows(): print(f"  {100*r.recall:5.1f}%  (n={int(r.n):>5})  {nm}")
print("=== strongest ===")
for nm,r in rec.tail(3).iterrows(): print(f"  {100*r.recall:5.1f}%  (n={int(r.n):>5})  {nm}")

# fit final on all + save (classify_embedding handoff)
final=clf().fit(X,y)
joblib.dump({"clf":final,"pca":pca,"classes":list(final.classes_),
             "recommend_confirm_below":0.7}, D/"data/niche_classifier.pkl")
out={"n_funnels":int(len(df)),"n_accounts":int(df.campaignId.nunique()),"n_niches":int(len(classes)),
     "top1_acct_holdout":round(float(top1),3),"top3_acct_holdout":round(float(top3),3),
     "auto_assign_at_conf0.7":{"coverage":round(float((conf>=0.7).mean()),3),
        "accuracy":round(float(accuracy_score(y[conf>=0.7],pred[conf>=0.7])),3)}}
(D/"data/niche_classifier_eval.json").write_text(json.dumps(out,indent=2))
print("\nsaved -> data/niche_classifier.pkl (clf+pca+classes, confirm_below=0.7), niche_classifier_eval.json")
print("handoff: load pkl; niche = classes[clf.predict_proba(pca.transform(embedding))[0].argmax()];")
print("         if max(proba) < 0.7 -> show top-3 and ask the user to confirm.")
