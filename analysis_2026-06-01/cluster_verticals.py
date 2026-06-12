"""Discover funnel verticals from copy via TF-IDF + MiniBatchKMeans.
Content-driven (no imposed taxonomy). Outputs a cluster summary for labeling."""
import re, json, sys
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import MiniBatchKMeans
from pathlib import Path

D = Path(__file__).parent
K = int(sys.argv[1]) if len(sys.argv) > 1 else 40

df = pd.read_csv(D/"data/funnel_content.csv")
df["funnel_name"] = df["funnel_name"].fillna("")
df["content_text"] = df["content_text"].fillna("")
# weight the name by repeating it (concise vertical signal)
df["doc"] = (df["funnel_name"] + " ") * 3 + df["content_text"]
print(f"{len(df)} funnels loaded")

# bilingual (DE+EN) stopwords + template/structural noise that survived extraction
DE_STOP = """und oder der die das ein eine einen dem den des mit für von zu im in
auf ist sind war dich dir du wir uns euch sie ihr ihre dein deine mein meine als auch
nicht noch nur schon sehr mehr hier dann wenn weil dass aber bei aus nach vor über
unter durch um am beim zum zur kann kannst können wird werden hat haben sein wie was
wer wo so es er ist diese dieser dieses alle alles mehr block text nachricht klick mich
neues theme deine dein einfach ja nein""".split()
NOISE = "block text nachricht klick mich theme grid row column listitem button media".split()
vec = TfidfVectorizer(strip_accents="unicode", lowercase=True, ngram_range=(1,2),
                      min_df=20, max_df=0.4, max_features=30000,
                      stop_words=list(set(list(TfidfVectorizer(stop_words='english').get_stop_words()) + DE_STOP + NOISE)),
                      token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b")
X = vec.fit_transform(df["doc"])
print("tfidf matrix", X.shape)

km = MiniBatchKMeans(n_clusters=K, random_state=42, n_init=5, batch_size=2048)
df["cluster"] = km.fit_predict(X)
terms = vec.get_feature_names_out()
centroids = km.cluster_centers_

rows = []
for c in range(K):
    sub = df[df.cluster == c]
    top_idx = centroids[c].argsort()[::-1][:12]
    top_terms = [terms[i] for i in top_idx]
    # most-trafficked example names in the cluster
    examples = (sub.sort_values("visitors", ascending=False)["funnel_name"]
                .head(8).tolist())
    rows.append({
        "cluster": c,
        "n_funnels": len(sub),
        "total_visitors": int(sub.visitors.sum()),
        "median_cvr_pct": round(100*sub.cvr.median(), 2),
        "top_terms": ", ".join(top_terms),
        "example_names": " || ".join(str(e)[:50] for e in examples),
    })

summary = pd.DataFrame(rows).sort_values("total_visitors", ascending=False)
summary.to_csv(D/"data/cluster_summary.csv", index=False)
df[["campaignVersionId","cluster"]].to_csv(D/"data/funnel_clusters.csv", index=False)
pd.set_option("display.max_colwidth", 90); pd.set_option("display.width", 240)
print(summary[["cluster","n_funnels","total_visitors","median_cvr_pct","top_terms"]].to_string(index=False))
print("\nwrote data/cluster_summary.csv and data/funnel_clusters.csv")
