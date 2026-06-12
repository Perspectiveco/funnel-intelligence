"""Niche-definition test (Marco's hypothesis): is the funnel JOB / value-promise a better
niche key than INDUSTRY? Two checks:
  1) variance of CVR explained by industry vs by job (eta^2) — audience-confounded, context only
  2) do the WINNING structural patterns transfer across industries WITHIN the same job?
     (the product question: do the same recommendations apply regardless of industry?)"""
import pandas as pd, numpy as np, re
from scipy.stats import mannwhitneyu
from pathlib import Path
D=Path(__file__).parent

f=pd.read_csv(D/"data/funnel_features_v1.csv")
c=pd.read_csv(D/"data/funnel_content.csv",usecols=["campaignVersionId","funnel_name","content_text"])
df=f.merge(c,on="campaignVersionId",how="left")
df=df[(df.visitors>=500)&df.cvr.notna()&df.vertical.notna()].copy()
df["txt"]=(df.funnel_name.fillna("")+" "+df.content_text.fillna("")).str.lower()

# --- derive funnel JOB (value promise) from copy ---
def job(t):
    if re.search(r"\bwebinar|masterclass|live training|videokurs|online.?kurs", t): return "webinar/course"
    if re.search(r"bewerb|lebenslauf|anschreiben|ausbildung|stelle|mitarbeiter|vollzeit|teilzeit|\bapply\b", t): return "application"
    if re.search(r"termin|beratung|gespräch|appointment|consultation|erstgespräch|kennenlern|\bcall\b|probestunde", t): return "consultation"
    if re.search(r"angebot|anfrage|unverbindlich|\bquote\b|expose|bewertung|kalkul", t): return "quote/lead-gen"
    if re.search(r"kaufen|rabatt|bestell|warenkorb|gutschein|\bshop\b|\border\b|\bcart\b", t): return "purchase"
    return "other"
df["job"]=df.txt.apply(job)

print("=== funnel JOB distribution ===")
print(df.job.value_counts().to_string())
print("\n=== JOB x INDUSTRY (does a job span industries? Marco's premise) ===")
ct=pd.crosstab(df.job, df.vertical)
pd.set_option("display.width",240); pd.set_option("display.max_columns",20)
print(ct.to_string())

# --- eta^2: how much CVR variance does each grouping explain (on log cvr) ---
def eta2(g):
    y=np.log(df.cvr.clip(lower=1e-4)); gm=y.mean()
    ss_t=((y-gm)**2).sum()
    ss_b=df.assign(y=y).groupby(g).apply(lambda s: len(s)*(s.y.mean()-gm)**2).sum()
    return ss_b/ss_t
print(f"\n=== CVR variance explained (eta^2; audience-confounded, context only) ===")
print(f"  by INDUSTRY (vertical): {eta2('vertical'):.3f}")
print(f"  by JOB (value promise): {eta2('job'):.3f}")
df["job_ind"]=df.job+" | "+df.vertical
print(f"  by JOB x INDUSTRY:      {eta2('job_ind'):.3f}")

# --- DO WINNING PATTERNS TRANSFER ACROSS INDUSTRIES WITHIN A JOB? ---
FEATS=["n_pages","q_media","q_choice","q_form","n_form_fields","n_social","n_media","has_branching"]
def top_diff(sub):
    q1,q3=sub.cvr.quantile(.25),sub.cvr.quantile(.75)
    hi,lo=sub[sub.cvr>=q3],sub[sub.cvr<=q1]
    out={}
    for ft in FEATS:
        a,b=hi[ft].values,lo[ft].values
        if len(a)<15 or len(b)<15: continue
        U,p=mannwhitneyu(a,b,alternative="two-sided")
        out[ft]=-(1-2*U/(len(a)*len(b)))   # >0 winners have MORE
    return out

JOB="consultation"   # the job that most spans industries
sub=df[df.job==JOB]
inds=sub.vertical.value_counts()
inds=inds[inds>=120].index.tolist()
print(f"\n=== winning patterns for JOB='{JOB}', per industry (>=120 funnels) ===")
print(f"(rank-biserial; + = winners have MORE. Are the signs consistent across industries?)")
rows={}
for ind in inds:
    rows[ind]=top_diff(sub[sub.vertical==ind])
tab=pd.DataFrame(rows).round(2)
print(tab.to_string())
# consistency: for each feature, do industries agree on direction?
print("\nsign agreement across industries (per feature):")
for ft in tab.index:
    vals=tab.loc[ft].dropna()
    if len(vals)>=2:
        agree = (vals>0).all() or (vals<0).all()
        print(f"  {ft:<16} {'CONSISTENT' if agree else 'mixed':<11} {list(vals.values)}")
