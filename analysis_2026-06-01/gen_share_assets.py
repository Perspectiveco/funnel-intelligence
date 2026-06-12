"""Generate the slim files that let the analyzer run WITHOUT the 727MB funnel_content.csv
(which holds raw customer copy). Produces:
  data/funnel_meta.csv      campaignVersionId,funnel_name  (SAME row order as embeddings.npy -> emap still valid)
  data/niche_exemplars.json {niche: [2 real winner-opener snippets]}
Run once before bundling for a colleague."""
import re, json, pandas as pd
import recommend as R
from pathlib import Path
D=Path(__file__).parent
clean=lambda s: re.sub(r"\s+"," ",str(s)).replace(" | "," ").strip()

# 1) slim meta (order-preserving — read in the SAME order the embeddings were built)
meta=pd.read_csv(D/"data/funnel_content.csv",usecols=["campaignVersionId","funnel_name"])
meta.to_csv(D/"data/funnel_meta.csv",index=False)
print(f"funnel_meta.csv: {len(meta):,} rows")

# 2) precompute winner-opener exemplars per niche
ct=pd.read_csv(D/"data/funnel_content.csv",usecols=["campaignVersionId","content_text"]).set_index("campaignVersionId")
ex={}
for niche in sorted(R.F.niche.unique()):
    g=R.F[(R.F.niche==niche)&(R.F.lp_has_question==1)].sort_values("cvr",ascending=False).head(40)
    out=[]
    for cid in g.campaignVersionId:
        if cid in ct.index:
            t=clean(ct.loc[cid,"content_text"])[:110]
            if len(t)>30 and "[Template" not in t and "Text Block" not in t: out.append(t)
        if len(out)>=2: break
    ex[niche]=out
(D/"data/niche_exemplars.json").write_text(json.dumps(ex,ensure_ascii=False,indent=1))
print(f"niche_exemplars.json: {len(ex)} niches")
