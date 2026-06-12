"""Engine A first deliverable: per-niche winner-vs-loser structural contrast.
Top CVR quartile vs bottom quartile within each niche; rank-biserial effect + Mann-Whitney p.
Output: data/contrast_results.csv + charts/11_contrast_heatmap.png + console top-3 per niche."""
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu
from pathlib import Path

D = Path(__file__).parent
F = ["n_pages","n_result_pages","n_questions","q_media","q_text","q_choice","q_form",
     "n_form_fields","n_buttons","n_social","n_media","has_social","has_branching"]

df = pd.read_csv(D/"data/funnel_features_v1.csv")
df = df[(df.visitors >= 500) & df.cvr.notna() & df.subtype.notna()].copy()

# niche = recruiting subtypes (granular) + coarse vertical for the rest
df["niche"] = np.where(df.vertical == "Recruiting", "R: " + df.subtype, df.vertical)
sizes = df.niche.value_counts()
niches = sizes[sizes >= 400].index.tolist()
print(f"{len(df):,} funnels >=500 visitors | {len(niches)} niches with n>=400\n")

rows = []
for n in niches:
    sub = df[df.niche == n]
    q1, q3 = sub.cvr.quantile(0.25), sub.cvr.quantile(0.75)
    lo, hi = sub[sub.cvr <= q1], sub[sub.cvr >= q3]
    for f in F:
        a, b = hi[f].values, lo[f].values            # winners vs losers
        if a.std() == 0 and b.std() == 0: continue
        U, p = mannwhitneyu(a, b, alternative="two-sided")
        rbc = 1 - 2 * U / (len(a) * len(b))           # rank-biserial; <0 => winners HIGHER
        rows.append(dict(niche=n, n_win=len(hi), n_lose=len(lo), feature=f,
                         effect=-rbc,                  # flip: >0 => winners have MORE of f
                         med_win=float(np.median(a)), med_lose=float(np.median(b)), p=p))
res = pd.DataFrame(rows)
res.to_csv(D/"data/contrast_results.csv", index=False)

# console: top-3 differentiators per niche (significant only)
sig = res[res.p < 0.01].copy()
sig["absC"] = sig.effect.abs()
print("=== top differentiators per niche (winners vs losers, p<0.01) ===")
for n in niches:
    s = sig[sig.niche == n].nlargest(3, "absC")
    if s.empty: continue
    bits = [f"{r.feature} {'↑' if r.effect>0 else '↓'} ({r.med_lose:.0f}→{r.med_win:.0f}, e={r.effect:+.2f})"
            for r in s.itertuples()]
    print(f"{n:<38} {' | '.join(bits)}")

# heatmap: niches x features, signed effect, only p<0.01 shown
piv = res.pivot(index="niche", columns="feature", values="effect")
pv  = res.pivot(index="niche", columns="feature", values="p")
piv = piv[F].loc[niches]
masked = piv.where(pv[F].loc[niches] < 0.01)
fig, ax = plt.subplots(figsize=(11, 0.42*len(niches)+2))
im = ax.imshow(masked.values.astype(float), cmap="RdBu_r", vmin=-0.45, vmax=0.45, aspect="auto")
ax.set_xticks(range(len(F))); ax.set_xticklabels(F, rotation=45, ha="right", fontsize=8)
ax.set_yticks(range(len(niches))); ax.set_yticklabels(niches, fontsize=8)
ax.set_title("What separates winning funnels (top CVR quartile) from losing ones — per niche\n"
             "red = winners have MORE of it, blue = winners have LESS. Only p<0.01 shown.", fontsize=10)
fig.colorbar(im, ax=ax, label="rank-biserial effect", shrink=0.7)
fig.tight_layout(); fig.savefig(D/"charts/11_contrast_heatmap.png", dpi=130)
print("\nwrote data/contrast_results.csv + charts/11_contrast_heatmap.png")
