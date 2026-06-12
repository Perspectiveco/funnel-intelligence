"""Winning MESSAGE ANGLES per niche: cluster copy (embeddings) within a niche, rank angles by CVR."""
import numpy as np, pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from pathlib import Path
D=Path(__file__).parent

content=pd.read_csv(D/"data/funnel_content.csv").reset_index(drop=True)
emb=np.load(D/"data/embeddings.npy")
emap={v:i for i,v in enumerate(content.campaignVersionId.values)}
ver=pd.read_csv(D/"data/funnel_vertical_v2.csv")[["campaignVersionId","vertical","subtype"]]
df=content.merge(ver,on="campaignVersionId")
df=df[(df.visitors>=500)&df.cvr.notna()].copy()
df["niche"]=np.where(df.vertical=="Recruiting","R: "+df.subtype,df.vertical)

DE_EN_STOP="und der die das ein eine du dich wir uns ich sie ihr mit für von zu im in auf ist sind als auch nicht nur the and you your for with our are this that".split()
focus=["R: Nursing & care","R: Trades & technical","Real Estate","Coaching / Webinar","Solar / Energy","R: Drivers (LKW)"]
for niche in focus:
    sub=df[df.niche==niche]
    if len(sub)<300: continue
    idx=[emap[v] for v in sub.campaignVersionId.values]
    X=emb[idx]
    k=6
    km=KMeans(n_clusters=k,random_state=0,n_init=5).fit(X)
    sub=sub.assign(angle=km.labels_)
    tf=TfidfVectorizer(strip_accents="unicode",ngram_range=(1,2),min_df=5,max_df=0.5,
                       max_features=8000,stop_words=DE_EN_STOP,token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b")
    Xt=tf.fit_transform(sub.content_text.fillna("")); terms=tf.get_feature_names_out()
    print(f"\n############ {niche}  (n={len(sub)}, median CVR {100*sub.cvr.median():.2f}%) ############")
    rows=[]
    for a in range(k):
        m=sub.angle==a
        if m.sum()<20: continue
        top=np.asarray(Xt[m.values].mean(axis=0)).ravel()
        words=", ".join(terms[i] for i in top.argsort()[::-1][:8])
        rows.append((a,m.sum(),100*sub[m].cvr.median(),words))
    rows.sort(key=lambda r:-r[2])
    for a,n,cvr,words in rows:
        print(f"  CVR {cvr:5.2f}% (n={n:>4})  {words}")
