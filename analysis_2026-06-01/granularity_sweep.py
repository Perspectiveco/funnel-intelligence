"""How many niches? Sweep cluster count k; measure the OUT-OF-SAMPLE predictive value of
niche membership for CVR (target-encoding, 5-fold, shrinkage-smoothed), plus cell sizes.
Held-out rho rises with k, then plateaus/drops when cells get too small to be reliable.
The elbow = the data-supported granularity."""
import numpy as np, pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.model_selection import KFold
from scipy.stats import spearmanr
from pathlib import Path
D=Path(__file__).parent

content=pd.read_csv(D/"data/funnel_content.csv").reset_index(drop=True)
emb=np.load(D/"data/embeddings.npy")
assert len(content)==len(emb)
mask=(content.visitors>=200)&content.cvr.notna()
X=emb[mask.values]
y=np.log(content.cvr[mask].clip(lower=1e-4).values)
print(f"{len(y):,} funnels (>=200 visitors)\n")
glob=y.mean()
print(f"{'k':>5} {'heldout_rho':>12} {'median_cell':>12} {'cells<50':>9}")
for k in [11,34,80,150,300,600,1000]:
    lab=MiniBatchKMeans(n_clusters=k,random_state=0,n_init=3,batch_size=4096).fit_predict(X)
    pred=np.empty_like(y)
    for tr,va in KFold(5,shuffle=True,random_state=0).split(X):
        s=pd.Series(y[tr]); g=pd.Series(lab[tr])
        mean=s.groupby(g).mean(); cnt=s.groupby(g).count()
        enc=((mean*cnt+glob*20)/(cnt+20))          # shrink small cells toward global
        pred[va]=pd.Series(lab[va]).map(enc).fillna(glob).values
    rho=spearmanr(pred,y).correlation
    sizes=pd.Series(lab).value_counts()
    print(f"{k:>5} {rho:>12.3f} {int(sizes.median()):>12} {int((sizes<50).sum()):>9}")
print("\nRead: rho = how well niche-membership predicts CVR out-of-sample.")
print("Pick the k where rho stops climbing meaningfully AND cells are still large enough for the A/B layer.")
