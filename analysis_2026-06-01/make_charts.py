"""Generate charts for the Funnel Intelligence V0 landscape findings doc."""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

D = Path(__file__).parent
OUT = D / "charts"; OUT.mkdir(exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "font.size": 11, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False})
ACCENT = "#5b5bd6"; ACCENT2 = "#e8833a"; MUT = "#9aa0b4"

# 1. CVR distribution histogram (funnels >=500 visitors)
h = pd.read_csv(D/"data/cvr_hist.csv")
fig, ax = plt.subplots(figsize=(8,4.2))
ax.bar(h.cvr_pct_bin, h.n_funnels, width=0.9, color=ACCENT)
ax.axvline(2.11, color=ACCENT2, ls="--", lw=2, label="median 2.11%")
ax.set_xlim(-0.5, 30); ax.set_xlabel("Funnel conversion rate (%)"); ax.set_ylabel("# funnels")
ax.set_title("CVR distribution across funnels (>=500 visitors, n=108,107)\nHeavily right-skewed: most funnels 0-3%, a long high-performing tail")
ax.legend(); fig.tight_layout(); fig.savefig(OUT/"01_cvr_distribution.png"); plt.close()

# 2. Variance decomposition
fig, ax = plt.subplots(figsize=(8,2.6))
ax.barh([0], [87.2], color=MUT)
ax.barh([0], [12.8], left=[87.2], color=ACCENT)
ax.text(43.6, 0, "87%", ha="center", va="center", color="white", fontsize=14, fontweight="bold")
ax.text(93.6, 0, "13%", ha="center", va="center", color="white", fontsize=12, fontweight="bold")
ax.set_xlim(0,100); ax.set_ylim(-0.6,0.6); ax.set_xlabel("% of CVR variance (campaigns with >=2 well-trafficked versions)")
ax.set_yticks([]); ax.grid(False)
ax.set_title("Where does conversion variance come from?")
ax.text(43.6, -0.45, "Between accounts/campaigns\n(vertical, offer, audience, traffic — not designable)",
        ha="center", va="top", fontsize=9)
ax.text(93.6, 0.45, "Within account,\nbetween versions\n(the design effect)", ha="center", va="bottom", fontsize=8.5, color=ACCENT)
fig.tight_layout(); fig.savefig(OUT/"02_variance_decomposition.png"); plt.close()

# 3. CVR by funnel length
l = pd.read_csv(D/"data/cvr_by_length.csv")
fig, ax = plt.subplots(figsize=(8,4.2))
ax.bar(l.pages_bucket, l.median_cvr_pct, color=ACCENT, width=0.65)
for x,y in zip(l.pages_bucket, l.median_cvr_pct): ax.text(x, y+0.04, f"{y:.2f}%", ha="center", fontsize=9)
ax.set_xlabel("Funnel length (# pages)"); ax.set_ylabel("Median funnel CVR (%)")
ax.set_title("Longer funnels convert better (median CVR by page count)\n1-3 pages: 1.02%  ->  21+ pages: 2.73%  (monotonic)")
fig.tight_layout(); fig.savefig(OUT/"03_cvr_by_length.png"); plt.close()

# 4. CVR by traffic source (hardcoded from query D)
src = pd.DataFrame({
    "source": ["meta_paid","untagged/direct","google_paid","mixed/other_utm"],
    "visitors_m": [171.9, 25.5, 17.2, 12.6],
    "pooled_cvr": [4.13, 4.76, 2.20, 3.96]})
fig, (a1,a2) = plt.subplots(1,2, figsize=(10,4))
a1.bar(src.source, src.visitors_m, color=ACCENT); a1.set_ylabel("visitors (M)")
a1.set_title("Traffic volume by source\nPlatform is overwhelmingly Meta-paid"); a1.tick_params(axis="x", rotation=20)
a2.bar(src.source, src.pooled_cvr, color=ACCENT2); a2.set_ylabel("pooled CVR (%)")
a2.set_title("CVR by source\nGoogle-paid converts ~half of Meta"); a2.tick_params(axis="x", rotation=20)
fig.tight_layout(); fig.savefig(OUT/"04_traffic_source.png"); plt.close()

# 5. Result/disqualification pages vs CVR + completion (hardcoded)
rp = pd.DataFrame({"result_pages":[1,2,3,4,"5+"],
                   "median_cvr":[1.77,2.19,2.66,2.47,3.34],
                   "completion":[3.23,7.18,8.23,7.99,11.13]})
fig, ax = plt.subplots(figsize=(8,4.2)); x=range(len(rp))
ax.bar([i-0.2 for i in x], rp.median_cvr, width=0.4, color=ACCENT, label="median CVR %")
ax.bar([i+0.2 for i in x], rp.completion, width=0.4, color=ACCENT2, label="avg completion %")
ax.set_xticks(list(x)); ax.set_xticklabels(rp.result_pages); ax.set_xlabel("# result/disqualification pages")
ax.set_title("Branching pays off: more result/disqualification paths ->\nhigher CVR and much higher completion"); ax.legend()
fig.tight_layout(); fig.savefig(OUT/"05_result_pages.png"); plt.close()

# 6. Drop-off curve (DATA QUALITY exhibit - artifact)
dc = pd.read_csv(D/"data/dropoff_curve.csv")
fig, ax = plt.subplots(figsize=(8,4.2))
ax.plot(dc.step, dc.pct_of_all_sessions, marker="o", color="#c0392b")
ax.set_xlabel("step (counter.highest >= k)"); ax.set_ylabel("% of sessions")
ax.set_title("counter.highest is NOT a usable drop-off signal (artifact)\n100% 'reach' step 1, 0.99% reach step 2 - yet funnels avg 10.6 pages")
fig.tight_layout(); fig.savefig(OUT/"06_dropoff_artifact.png"); plt.close()

# 7. Funnel volume distribution
v = pd.read_csv(D/"data/visitor_dist.csv")
labels = {0:"1-9",1:"10-99",2:"100-999",3:"1k-9k",4:"10k-99k",5:"100k-1M",6:"1M+"}
v["lbl"]=v.log10_visitors.map(labels)
fig, ax = plt.subplots(figsize=(8,4.2))
ax.bar(v.lbl, v.n_funnels, color=ACCENT)
ax.set_yscale("log"); ax.set_xlabel("visitors per funnel"); ax.set_ylabel("# funnels (log)")
ax.set_title("Funnel traffic distribution: long tail\n~55k funnels have >=1,000 visitors (reliable CVR labels)")
fig.tight_layout(); fig.savefig(OUT/"07_volume_distribution.png"); plt.close()

print("charts written to", OUT)
for p in sorted(OUT.glob("*.png")): print(" -", p.name)
