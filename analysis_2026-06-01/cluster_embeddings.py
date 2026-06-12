"""Semantic vertical discovery: multilingual sentence-embeddings + KMeans.
Clusters by MEANING across languages (fixes TF-IDF's language/boilerplate fragmentation)."""
import sys, numpy as np, pandas as pd
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

D = Path(__file__).parent
K = int(sys.argv[1]) if len(sys.argv) > 1 else 35

df = pd.read_csv(D/"data/funnel_content.csv")
df["funnel_name"] = df["funnel_name"].fillna("")
df["content_text"] = df["content_text"].fillna("")
# name carries strong vertical signal; cap content so seqs stay short & fast
df["doc"] = (df["funnel_name"] + ". ") * 2 + df["content_text"].str.slice(0, 400)
print(f"{len(df)} funnels", flush=True)

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device="mps")
emb = model.encode(df["doc"].tolist(), batch_size=256, show_progress_bar=True,
                   normalize_embeddings=True, convert_to_numpy=True)
np.save(D/"data/embeddings.npy", emb)
print("embeddings", emb.shape, flush=True)

km = KMeans(n_clusters=K, random_state=42, n_init=10)
df["ecluster"] = km.fit_predict(emb)

# describe each cluster: examples nearest centroid + top tf-idf terms (for human labeling)
tfidf = TfidfVectorizer(strip_accents="unicode", lowercase=True, ngram_range=(1,2),
                        min_df=10, max_df=0.5, max_features=20000,
                        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b")
Xt = tfidf.fit_transform(df["doc"]); terms = tfidf.get_feature_names_out()
rows = []
for c in range(K):
    idx = np.where(df.ecluster.values == c)[0]
    sub = df.iloc[idx]
    centroid = km.cluster_centers_[c]
    d = (emb[idx] @ centroid)
    near = sub.iloc[np.argsort(-d)[:10]]
    top = np.asarray(Xt[idx].mean(axis=0)).ravel()
    top_terms = [terms[i] for i in top.argsort()[::-1][:12]]
    rows.append({"ecluster": c, "n_funnels": len(sub),
                 "total_visitors": int(sub.visitors.sum()),
                 "median_cvr_pct": round(100*sub.cvr.median(), 2),
                 "top_terms": ", ".join(top_terms),
                 "example_names": " || ".join(str(n)[:48] for n in near.funnel_name.tolist())})
summary = pd.DataFrame(rows).sort_values("total_visitors", ascending=False)
summary.to_csv(D/"data/ecluster_summary.csv", index=False)
df[["campaignVersionId","ecluster"]].to_csv(D/"data/funnel_eclusters.csv", index=False)
pd.set_option("display.max_colwidth", 95); pd.set_option("display.width", 260)
print(summary[["ecluster","n_funnels","total_visitors","median_cvr_pct","top_terms"]].to_string(index=False))
print("\nwrote ecluster_summary.csv + funnel_eclusters.csv")
