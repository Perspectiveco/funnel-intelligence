"""CONTENT-PROPOSAL-VALIDITY BACKTEST — the content counterpart to proposal_backtest.py.

proposal_backtest.py answered this for STRUCTURE (9 page features) and found ~no causal signal
(change-model AUC 0.52, flat dose-response). But M2 showed the real lever is CONTENT
(embedding perm-importance +0.444 >> all structure ~0.18). So the open question is:

  Does moving a page's COPY toward what *wins* in its niche actually win real A/B tests,
  or is the content->CVR link (like the structural one) merely correlational / Goodhart-prone?

We answer it on the same 9,935 linked A/B tests (control vs variant PAGE, kept_original verdict),
but on arm-level CONTENT EMBEDDINGS instead of structural deltas.

"Winning content direction" is defined leakage-free:
  winner arm = variant if the challenger won, else control (kept_original).
  per-niche winner centroid = mean winner-arm embedding, computed LEAVE-THIS-ACCOUNT-OUT
  (GroupKFold-style: a test never sees its own account's arms in the reference it's judged against).
  align(test) = cos(variant, centroid) - cos(control, centroid)   (>0 => variant moved toward winning copy)

Three nested tests (mirror proposal_backtest.py):
  A) DIRECTION : win-rate when align>0 vs align<0, and for the strongest toward-moves, vs baseline.
  B) DOSE-RESPONSE : win-rate by align-decile. A real causal lever is MONOTONE; the structural
     version was flat (the tell-tale of "correlational, not causal").
  C) CAUSAL CHANGE-MODEL : learn won ~ (content delta in arm-PCA space + alignment features),
     GroupKFold by account. OOS AUC > ~0.55 => content change carries real signal about who wins;
     ~0.50 => it does not (then content recs also need the LIVE flywheel, same verdict as structure).

HONEST CAVEATS (by construction):
  - kept_original is a noisy win proxy; diffs are multi-variable; arm content = CURRENT content
    (no historical snapshot at test time); page-level plainText concatenation loses visual order.
    -> directional, not definitive.
  - Arms are embedded content-only (no funnel-name doubling like cluster_embeddings.py) — fine, they
    are compared to each other and to a centroid built the SAME way, so the space is internally consistent.

PREREQ: a one-time BigQuery pull (pageId -> content_text) for the A/B arms. Runs the bq CLI, so
execute on a machine where `bq` is authenticated (Alex's laptop / CI), NOT in the Claude sandbox
(sandbox blocks BQ; if you must, run the bq step under dangerouslyDisableSandbox). The pull is cached
to data/page_text.csv — delete it to force a refresh. Est. ~$1 (one full scan of components.content).
"""
import os, sys, json, subprocess, numpy as np, pandas as pd
from pathlib import Path

D = Path(__file__).parent
DATA = D / "data"
PROJECT = "perspective-bi"
BQ = os.environ.get("BQ_BIN", "bq")              # path to the bq CLI (override if not on PATH)
DS = "funnel_intelligence"                       # existing dataset we already use
TMP_IDS = f"{PROJECT}:{DS}._arm_pageids_tmp"
PAGE_TEXT = DATA / "page_text.csv"               # cache: pageId, content_text
ARM_EMB = DATA / "arm_emb.npz"                   # cache: pageId order + normalized embeddings
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"   # same model as cluster_embeddings.py


def norm_niche(s):
    return str(s).strip().replace("R: ", "R:")


# ───────────────────────── 1. arms we need ─────────────────────────
m = pd.read_csv(DATA / "causal_linked.csv",
                dtype={"campaignId": str, "control": str, "variant": str})
m["won"] = m.won.astype(str).str.lower().eq("true")
m["niche"] = m.niche.map(norm_niche)
arm_ids = pd.unique(pd.concat([m.control, m.variant], ignore_index=True).dropna())
print(f"{len(m):,} linked A/B tests | {len(arm_ids):,} unique arm pages\n")


# ───────────────────────── 2. BQ pull: pageId -> content_text ─────────────────────────
def bq(*args, **kw):
    print("  $ bq", " ".join(a for a in args[:4] if not a.startswith("--")), "…")
    return subprocess.run([BQ, f"--project_id={PROJECT}", *args], check=True, **kw)


def pull_page_text():
    if PAGE_TEXT.exists():
        print(f"[skip] {PAGE_TEXT.name} exists ({PAGE_TEXT.stat().st_size//1024} KB) — delete to refresh\n")
        return
    print("[bq] pulling page content_text (one-time, ~$1 scan)…")
    ids_csv = DATA / "_arm_pageids.csv"
    pd.DataFrame({"pageId": arm_ids}).to_csv(ids_csv, index=False)
    bq("load", "--replace", "--skip_leading_rows=1", "--source_format=CSV",
       TMP_IDS, str(ids_csv), "pageId:STRING")
    # latest non-deleted state per component _id; concatenate the rendered plainText per page.
    # plainText = what the visitor actually reads (the `text` field is a template placeholder).
    sql = f"""
    WITH latest AS (
      SELECT pageId, content, _ab_cdc_deleted_at, createdAt,
             ROW_NUMBER() OVER (PARTITION BY _id ORDER BY _airbyte_extracted_at DESC) AS rn
      FROM `{PROJECT}.mongodb_lemon_tool_api.components`
      WHERE pageId IN (SELECT pageId FROM `{PROJECT}.{DS}._arm_pageids_tmp`)
    )
    SELECT pageId,
           STRING_AGG(JSON_VALUE(content, '$.plainText'), ' ' ORDER BY createdAt) AS content_text
    FROM latest
    WHERE rn = 1 AND _ab_cdc_deleted_at IS NULL
      AND JSON_VALUE(content, '$.plainText') IS NOT NULL
      AND TRIM(JSON_VALUE(content, '$.plainText')) != ''
    GROUP BY pageId
    """
    with open(PAGE_TEXT, "w") as f:
        bq("query", "--use_legacy_sql=false", "--format=csv", "--max_rows=1000000", sql, stdout=f)
    print(f"[bq] wrote {PAGE_TEXT.name} ({sum(1 for _ in open(PAGE_TEXT))-1:,} pages)\n")


pull_page_text()
pt = pd.read_csv(PAGE_TEXT, dtype={"pageId": str}).dropna(subset=["content_text"])
pt = pt.drop_duplicates("pageId").set_index("pageId")


# ───────────────────────── 3. embed arms (cached) ─────────────────────────
def embed_arms():
    if ARM_EMB.exists():
        z = np.load(ARM_EMB, allow_pickle=True)
        print(f"[skip] {ARM_EMB.name} exists ({len(z['ids']):,} arms) — delete to re-embed\n")
        return {pid: i for i, pid in enumerate(z["ids"])}, z["emb"]
    from sentence_transformers import SentenceTransformer
    import torch
    dev = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[embed] loading {MODEL_NAME} on {dev}…")
    model = SentenceTransformer(MODEL_NAME, device=dev)
    ids = pt.index.to_numpy()
    docs = pt.content_text.str.slice(0, 400).tolist()   # same 400-char cap as the funnel pipeline
    emb = model.encode(docs, batch_size=256, show_progress_bar=True,
                       normalize_embeddings=True, convert_to_numpy=True)
    np.savez(ARM_EMB, ids=ids, emb=emb)
    print(f"[embed] {emb.shape[0]:,} arms × {emb.shape[1]} dims -> {ARM_EMB.name}\n")
    return {pid: i for i, pid in enumerate(ids)}, emb


emap, EMB = embed_arms()

# keep only tests where BOTH arms have an embedding
m = m[m.control.isin(emap) & m.variant.isin(emap)].reset_index(drop=True)
C = EMB[[emap[p] for p in m.control]]
V = EMB[[emap[p] for p in m.variant]]
won = m.won.to_numpy()
acct = m.campaignId.to_numpy()
niche = m.niche.to_numpy()
base = won.mean(); n = len(m)
print(f"usable tests with both arms embedded: {n:,} | baseline challenger-win = {100*base:.1f}%\n")


# ───────────────────────── 4. leave-account-out winning-content centroid ─────────────────────────
# winner arm of a test = variant if challenger won, else control (kept_original).
winner = np.where(won[:, None], V, C)                       # (n, dim), already L2-normalized arms
MINN = 30                                                   # below this per-niche -> fall back to global

# precompute per-niche and per-(niche,account) sums for O(1) leave-account-out
from collections import defaultdict
nsum = defaultdict(lambda: np.zeros(EMB.shape[1])); ncnt = defaultdict(int)
asum = defaultdict(lambda: np.zeros(EMB.shape[1])); acnt = defaultdict(int)
gsum = np.zeros(EMB.shape[1]); gcnt = 0
gasum = defaultdict(lambda: np.zeros(EMB.shape[1])); gacnt = defaultdict(int)
for i in range(n):
    w, nz, a = winner[i], niche[i], acct[i]
    nsum[nz] += w; ncnt[nz] += 1; asum[(nz, a)] += w; acnt[(nz, a)] += 1
    gsum += w; gcnt += 1; gasum[a] += w; gacnt[a] += 1


def loo_centroid(i):
    nz, a = niche[i], acct[i]
    s = nsum[nz] - asum[(nz, a)]; c = ncnt[nz] - acnt[(nz, a)]
    if c < MINN:                                            # sparse niche -> global LOO centroid
        s = gsum - gasum[a]; c = gcnt - gacnt[a]
    v = s / max(c, 1)
    nrm = np.linalg.norm(v)
    return v / nrm if nrm > 0 else v


cent = np.vstack([loo_centroid(i) for i in range(n)])
cos_v = np.einsum("ij,ij->i", V, cent)                      # cosine: arms & centroid are unit-norm
cos_c = np.einsum("ij,ij->i", C, cent)
align = cos_v - cos_c                                       # >0 => variant moved toward winning copy


def wr(mask, label):
    k = int(mask.sum())
    if k < 40:
        return
    w = 100 * won[mask].mean()
    print(f"  {w:5.1f}%  (n={k:>5}, {w-100*base:+.1f}pp)  {label}")


# ───────────────────────── TEST A: direction ─────────────────────────
print("=== A) DIRECTION: win-rate when the variant moves toward winning content ===")
wr(align > 0, "variant MORE like niche-winning content than control")
wr(align < 0, "variant LESS like winning content (against)")
q = np.quantile(align[align > 0], 0.75) if (align > 0).any() else 0
wr(align >= q, "strongest toward-moves (top quartile of +align)")

# ───────────────────────── TEST B: dose-response ─────────────────────────
print("\n=== B) DOSE-RESPONSE: win-rate by align decile (0=most against .. 9=most toward) ===")
dec = pd.qcut(align, 10, labels=False, duplicates="drop")
cal = pd.DataFrame({"dec": dec, "won": won}).groupby("dec").won.agg(["mean", "size"])
print("   " + ", ".join(f"d{int(i)}:{100*r['mean']:.0f}%" for i, r in cal.iterrows()))
mono = np.corrcoef(cal.index.values, cal["mean"].values)[0, 1]
print(f"   monotonicity (Spearman-ish corr of decile vs win-rate) = {mono:+.2f}   "
      f"(>~+0.6 = dose-response = causal-like; ~0 = flat = correlational, like structure)")

# ───────────────────────── TEST C: causal change-model ─────────────────────────
print("\n=== C) CAUSAL CHANGE-MODEL: won ~ content delta (arm-PCA) + alignment, GroupKFold by account ===")
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import cross_val_predict, GroupKFold
from sklearn.metrics import roc_auc_score

pca = PCA(n_components=100, random_state=0).fit(EMB)        # unsupervised on all arms -> ~no leakage
dV, dC = pca.transform(V), pca.transform(C)
X = np.column_stack([dV - dC, align, cos_v, cos_c])         # content change + how close each arm is to winning
y = won
gkf = GroupKFold(n_splits=5)
clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_depth=4,
                                     l2_regularization=1.0, random_state=0)
p = cross_val_predict(clf, X, y, cv=gkf, groups=acct, method="predict_proba", n_jobs=-1)[:, 1]
auc = roc_auc_score(y, p)
print(f"  out-of-fold AUC = {auc:.3f}   (0.5 = content change carries NO signal about who wins)")
order = np.argsort(-p)
for frac in (0.05, 0.10, 0.20):
    k = int(n * frac); topwr = 100 * y[order[:k]].mean()
    print(f"  top {int(frac*100):>2}% most-confident predicted winners (n={k}): {topwr:.1f}%  ({topwr-100*base:+.1f}pp)")

# ───────────────────────── save ─────────────────────────
out = {
    "n": int(n), "baseline_winrate": round(100 * base, 1),
    "toward_winrate": round(float(100 * won[align > 0].mean()), 1),
    "against_winrate": round(float(100 * won[align < 0].mean()), 1),
    "dose_response_monotonicity": round(float(mono), 2),
    "causal_model_auc": round(float(auc), 3),
    "top10pct_winrate": round(float(100 * y[order[:int(n * 0.10)]].mean()), 1),
}
(DATA / "content_proposal_backtest.json").write_text(json.dumps(out, indent=2))
print("\nsaved -> data/content_proposal_backtest.json")
print("VERDICT GUIDE: strong toward/against spread + monotone dose-response + AUC>0.55 => content is a")
print("               causal lever worth a pre-trained recommender. Flat + AUC~0.5 => same as structure:")
print("               correlational only, must be validated by the LIVE A/B flywheel.")
