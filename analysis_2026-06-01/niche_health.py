"""NICHE RECALIBRATION DIAGNOSTIC — should the taxonomy adapt? (the 'recalibrate niches' requirement)
We already know the 32 niches are likely too coarse (niche->CVR predictiveness keeps rising 34->1000).
This flags WHERE to act:
 - TOO BROAD -> SPLIT: split the niche's embeddings in two; if the halves have clearly different CVR
   (and both are sizeable), the niche conflates two behaviours and a sub-niche would predict better.
 - TOO GRANULAR -> MERGE: niche pairs whose embedding centroids are very close AND whose winner-patterns
   (per-niche driver columns) agree AND whose median CVR is similar -> redundant, merge.
 - THIN -> unstable benchmark (n small).
Run this periodically; human approves split/merge; taxonomy evolves. All local, no new data."""
import numpy as np, pandas as pd, joblib
from sklearn.cluster import KMeans
from pathlib import Path
D=Path(__file__).parent
norm=lambda s: str(s).replace("R: ","R:")

C=joblib.load(D/"data/niche_classifier.pkl"); pca=C["pca"]
emb=np.load(D/"data/embeddings.npy")
ids=pd.read_csv(D/"data/funnel_content.csv",usecols=["campaignVersionId"]).reset_index(drop=True)
emap={v:i for i,v in enumerate(ids.campaignVersionId.values)}
dc=pd.read_csv(D/"data/deep_composition_features.csv")[["campaignVersionId","visitors","cvr","niche"]]
dc["niche"]=dc.niche.map(norm); dc=dc[(dc.visitors>=500)&dc.cvr.notna()&dc.niche.notna()&dc.campaignVersionId.isin(emap)]
M=pd.read_csv(D/"data/per_niche_drivers.csv",index_col=0); M.columns=[norm(c) for c in M.columns]

niches=dc.niche.value_counts(); niches=niches[niches>=500]
cent={}; split=[]
for nm,n in niches.items():
    g=dc[dc.niche==nm]; E=pca.transform(emb[[emap[v] for v in g.campaignVersionId.values]])
    cent[nm]=E.mean(0)
    lab=KMeans(n_clusters=2,n_init=4,random_state=0).fit_predict(E)
    a,b=g.cvr.values[lab==0],g.cvr.values[lab==1]
    if len(a)<50 or len(b)<50: continue
    bal=min(len(a),len(b))/len(g); gap=abs(np.median(a)-np.median(b))
    split.append((nm,int(n),100*np.median(a),100*np.median(b),100*gap,bal))

print("=== TOO BROAD -> SPLIT candidates (2-way split yields sub-niches with distinct CVR) ===")
print("    niche                              n     subA%   subB%   |gap|pp  balance")
for nm,n,ma,mb,gap,bal in sorted(split,key=lambda x:-x[4])[:8]:
    flag=" <-- SPLIT" if (gap>=0.6 and bal>=0.30) else ""
    print(f"    {nm:<33}{n:>6}  {ma:5.2f}  {mb:5.2f}   {gap:5.2f}   {bal:.2f}{flag}")

print("\n=== TOO GRANULAR -> MERGE candidates (close centroid + same winner-pattern + similar CVR) ===")
nm_list=list(cent); med={nm:dc[dc.niche==nm].cvr.median() for nm in nm_list}
def cos(a,b): return float(a@b/(np.linalg.norm(a)*np.linalg.norm(b)))
pairs=[]
for i in range(len(nm_list)):
    for j in range(i+1,len(nm_list)):
        x,y=nm_list[i],nm_list[j]
        cs=cos(cent[x],cent[y])
        dcorr=M[x].corr(M[y])                         # do their driver profiles agree?
        cvrgap=abs(med[x]-med[y])*100
        pairs.append((x,y,cs,dcorr,cvrgap))
print("    nicheA  +  nicheB                                       centroid_cos  driver_corr  cvrΔpp")
for x,y,cs,dc_,cg in sorted(pairs,key=lambda p:-p[2])[:8]:
    flag=" <-- MERGE" if (cs>=0.80 and dc_>=0.5 and cg<=0.6) else ""
    print(f"    {x[:24]:<25}+ {y[:24]:<25} {cs:5.2f}        {dc_:+.2f}       {cg:4.2f}{flag}")

thin=niches[niches<1500]
print(f"\n=== THIN niches (n<1500, benchmark less stable): {len(thin)} ===")
print("    "+", ".join(f"{nm}({n})" for nm,n in thin.items()))
print("\nRecalibration loop: re-run periodically -> propose split/merge -> human approves -> retrain classifier"
      "\n(long-term: continuous k-NN 'funnels like yours' removes fixed buckets entirely).")
