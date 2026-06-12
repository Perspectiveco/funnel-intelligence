"""CONTENT-CHANGE RANKER — turns the validated content-change signal (content_proposal_backtest.py:
OOS AUC 0.571, and the ablation showing the signal is the DIRECTION of the copy change, not its
amount) into a usable scorer for the recommender.

It does NOT give blind advice ("write like the niche average" failed — TEST A was negative). It RANKS
a concrete proposed copy change by its learned win-probability, so the recommender can order
suggestions by "this rewrite looks most promising — A/B-test it first".

  score_suggestion(current_text, proposed_text, niche) -> P(variant wins)   # the product entry point
  rank_change(control_emb, variant_emb, niche)         -> P(variant wins)   # if embeddings already exist

Honest scope (unchanged from the backtest): AUC 0.571 is real but modest. This is a PRIORITISER for
live A/B tests, not a guarantee. Every surfaced suggestion stays "A/B-test it". The live flywheel is
what upgrades these probabilities into confident causal claims.

Trains on the same 9.7k linked A/B arms. Final model is fit on ALL data (the honest OOS number is the
backtest's 0.571); per-niche winner centroids are full (no leave-one-out needed at inference time).
Reuses cached data/arm_emb.npz (+ rebuilds page_text/embeddings only if missing)."""
import numpy as np, pandas as pd, joblib, json
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier

D = Path(__file__).parent; DATA = D / "data"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
RANKER = DATA / "content_ranker.pkl"
norm_niche = lambda s: str(s).strip().replace("R: ", "R:")


def train():
    z = np.load(DATA / "arm_emb.npz", allow_pickle=True)
    emap = {pid: i for i, pid in enumerate(z["ids"])}; EMB = z["emb"]; dim = EMB.shape[1]
    m = pd.read_csv(DATA / "causal_linked.csv", dtype={"campaignId": str, "control": str, "variant": str})
    m["won"] = m.won.astype(str).str.lower().eq("true"); m["niche"] = m.niche.map(norm_niche)
    m = m[m.control.isin(emap) & m.variant.isin(emap)].reset_index(drop=True)
    C = EMB[[emap[p] for p in m.control]]; V = EMB[[emap[p] for p in m.variant]]
    y = m.won.to_numpy()

    # full per-niche winning-content centroid (winner arm = variant if won else control)
    winner = np.where(y[:, None], V, C)
    cent = {}
    for nz, idx in pd.Series(range(len(m))).groupby(m.niche.values).groups.items():
        v = winner[list(idx)].mean(0); nr = np.linalg.norm(v); cent[nz] = v / nr if nr else v
    g = winner.mean(0); gcen = g / max(np.linalg.norm(g), 1e-9)

    pca = PCA(n_components=100, random_state=0).fit(EMB)

    def feats(Cv, Vv, niches):
        cm = np.vstack([cent.get(n, gcen) for n in niches])
        cos_c = np.einsum("ij,ij->i", Cv, cm); cos_v = np.einsum("ij,ij->i", Vv, cm)
        return np.column_stack([pca.transform(Vv) - pca.transform(Cv), cos_v - cos_c, cos_v, cos_c])

    X = feats(C, V, m.niche.values)
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_depth=4,
                                         l2_regularization=1.0, random_state=0).fit(X, y)
    joblib.dump({"clf": clf, "pca": pca, "cent": cent, "gcen": gcen, "dim": dim}, RANKER)
    print(f"trained on {len(m):,} A/B pairs | {len(cent)} niche centroids -> {RANKER.name}")
    return clf, pca, cent, gcen


_B = None; _MODEL = None


def _load():
    global _B
    if _B is None:
        if not RANKER.exists():
            train()
        _B = joblib.load(RANKER)
    return _B


def _embed(texts):
    """content-only embedding, same model + 400-char cap + L2-norm as the arm pipeline."""
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        import torch
        dev = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
        _MODEL = SentenceTransformer(MODEL_NAME, device=dev)
    return _MODEL.encode([str(t)[:400] for t in texts], normalize_embeddings=True, convert_to_numpy=True)


def rank_change(control_emb, variant_emb, niche):
    """P(variant beats control) for a single proposed change. Embeddings = raw 384-d, L2-normalized."""
    b = _load(); cen = b["cent"].get(norm_niche(niche), b["gcen"])
    c = np.asarray(control_emb, float).ravel(); v = np.asarray(variant_emb, float).ravel()
    cos_c, cos_v = float(c @ cen), float(v @ cen)
    X = np.concatenate([b["pca"].transform(v[None]) - b["pca"].transform(c[None]),
                        [[cos_v - cos_c, cos_v, cos_c]]], axis=1)
    return float(b["clf"].predict_proba(X)[0, 1])


def score_suggestion(current_text, proposed_text, niche):
    """Product entry point: how likely is this rewritten copy to win vs the current copy?"""
    e = _embed([current_text, proposed_text])
    return rank_change(e[0], e[1], niche)


if __name__ == "__main__":
    clf, pca, cent, gcen = train()
    # sanity: actual winners should, on average, score higher than the arms that lost (in-sample)
    z = np.load(DATA / "arm_emb.npz", allow_pickle=True)
    emap = {pid: i for i, pid in enumerate(z["ids"])}; EMB = z["emb"]
    m = pd.read_csv(DATA / "causal_linked.csv", dtype={"campaignId": str, "control": str, "variant": str})
    m["won"] = m.won.astype(str).str.lower().eq("true"); m["niche"] = m.niche.map(norm_niche)
    m = m[m.control.isin(emap) & m.variant.isin(emap)].reset_index(drop=True)
    p = np.array([rank_change(EMB[emap[c]], EMB[emap[v]], n)
                  for c, v, n in zip(m.control, m.variant, m.niche)])
    print(f"mean P(win) when challenger actually WON  = {p[m.won.values].mean():.3f}")
    print(f"mean P(win) when challenger actually LOST = {p[~m.won.values].mean():.3f}")
    print("(separation here is in-sample; the honest OOS quality is the backtest's AUC 0.571)")
