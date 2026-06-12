"""ABLATION for content_proposal_backtest.py: is the AUC=0.571 just "amount of change",
or is it the DIRECTION of the content change?

Decomposes the change-model into nested feature sets, same arms/labels, GroupKFold by account:
  - MAG    : magnitude only (||Δembedding||, text-length deltas). If this alone ~0.57 -> it's just churn.
  - ALIGN  : cosine-only features (align, cos_v, cos_c) — magnitude-free by construction.
  - DIR    : the PCA delta, UNIT-normalized (direction kept, magnitude removed).
  - FULL   : the original model (PCA delta + alignment) — reproduces the backtest number.
Uses only cached data/page_text.csv + data/arm_emb.npz (no BQ, no re-embed)."""
import numpy as np, pandas as pd, json
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import cross_val_predict, GroupKFold
from sklearn.metrics import roc_auc_score

D = Path(__file__).parent; DATA = D / "data"


def norm_niche(s): return str(s).strip().replace("R: ", "R:")


m = pd.read_csv(DATA / "causal_linked.csv", dtype={"campaignId": str, "control": str, "variant": str})
m["won"] = m.won.astype(str).str.lower().eq("true"); m["niche"] = m.niche.map(norm_niche)
z = np.load(DATA / "arm_emb.npz", allow_pickle=True)
emap = {pid: i for i, pid in enumerate(z["ids"])}; EMB = z["emb"]
pt = pd.read_csv(DATA / "page_text.csv", dtype={"pageId": str}).drop_duplicates("pageId").set_index("pageId")
tlen = pt.content_text.fillna("").str.len().to_dict()

m = m[m.control.isin(emap) & m.variant.isin(emap)].reset_index(drop=True)
C = EMB[[emap[p] for p in m.control]]; V = EMB[[emap[p] for p in m.variant]]
y = m.won.to_numpy(); acct = m.campaignId.to_numpy(); n = len(m)
lc = m.control.map(lambda p: tlen.get(p, 0)).to_numpy(float)
lv = m.variant.map(lambda p: tlen.get(p, 0)).to_numpy(float)

# leave-account-out winning-content centroid (same as the backtest) -> cosine features
from collections import defaultdict
niche = m.niche.to_numpy(); winner = np.where(y[:, None], V, C); dim = EMB.shape[1]
nsum = defaultdict(lambda: np.zeros(dim)); ncnt = defaultdict(int)
asum = defaultdict(lambda: np.zeros(dim)); acnt = defaultdict(int)
gsum = np.zeros(dim); gcnt = 0; gasum = defaultdict(lambda: np.zeros(dim)); gacnt = defaultdict(int)
for i in range(n):
    w, nz, a = winner[i], niche[i], acct[i]
    nsum[nz] += w; ncnt[nz] += 1; asum[(nz, a)] += w; acnt[(nz, a)] += 1
    gsum += w; gcnt += 1; gasum[a] += w; gacnt[a] += 1
def cent(i):
    nz, a = niche[i], acct[i]; s = nsum[nz] - asum[(nz, a)]; c = ncnt[nz] - acnt[(nz, a)]
    if c < 30: s = gsum - gasum[a]; c = gcnt - gacnt[a]
    v = s / max(c, 1); nr = np.linalg.norm(v); return v / nr if nr else v
CEN = np.vstack([cent(i) for i in range(n)])
cos_v = np.einsum("ij,ij->i", V, CEN); cos_c = np.einsum("ij,ij->i", C, CEN); align = cos_v - cos_c

# feature blocks
delta = V - C
mag = np.linalg.norm(delta, axis=1)                       # how big is the content change
dlen = lv - lc
F_MAG = np.column_stack([mag, dlen, np.abs(dlen), lv, lc])
F_ALIGN = np.column_stack([align, cos_v, cos_c])
pca = PCA(n_components=100, random_state=0).fit(EMB)
dpca = pca.transform(V) - pca.transform(C)
dpca_unit = dpca / np.clip(np.linalg.norm(dpca, axis=1, keepdims=True), 1e-9, None)  # magnitude removed
F_DIR = dpca_unit
F_FULL = np.column_stack([dpca, align, cos_v, cos_c])

gkf = GroupKFold(n_splits=5)
def auc(X, label):
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_depth=4,
                                         l2_regularization=1.0, random_state=0)
    p = cross_val_predict(clf, X, y, cv=gkf, groups=acct, method="predict_proba", n_jobs=-1)[:, 1]
    a = roc_auc_score(y, p)
    order = np.argsort(-p); top10 = 100 * y[order[:int(n * .1)]].mean()
    print(f"  {label:<34} AUC {a:.3f}   top10%-winrate {top10:.1f}%")
    return round(float(a), 3)

print(f"n={n:,} | baseline {100*y.mean():.1f}%\n=== ABLATION: where does the signal live? ===")
res = {
    "MAG  (change amount only)": auc(F_MAG, "MAG  (change amount only)"),
    "ALIGN (cosine-to-winner only)": auc(F_ALIGN, "ALIGN (cosine-to-winner only)"),
    "DIR  (PCA delta, magnitude removed)": auc(F_DIR, "DIR  (PCA delta, magnitude removed)"),
    "FULL (PCA delta + alignment)": auc(F_FULL, "FULL (PCA delta + alignment)"),
}
(DATA / "content_ablation.json").write_text(json.dumps(res, indent=2))
print("\nINTERPRET: if MAG alone ~ FULL -> the model just rewards churn (suspect).")
print("           if DIR (magnitude-removed) holds up -> the WHICH-way of the copy change carries the signal.")
print("saved -> data/content_ablation.json")
