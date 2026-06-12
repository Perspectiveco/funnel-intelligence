# V0 Analysis — What the Real Data Says (June 2026)

First analysis pass on the full platform data, not a sample: **275M sessions, 196K trafficked funnel versions, 5.7M funnel snapshots, 4.4B behavioral events.** All of it linked, cleaned, and labeled. This is what we actually learned, what it means for the product, and where the claims are still soft.

## TL;DR

1. **Who you target sets 87% of conversion. Funnel design sets ~13%.** The score has to be a percentile *within a niche*, never an absolute number. An absolute score would just re-rank industries.
2. **Design still predicts within-niche conversion at ρ=0.37**, close to the 0.40 gate in the plan. A 0-traffic Funnel Score is feasible.
3. **The copy matters more than the layout** (ρ 0.30 vs 0.26), and the two add up. The advisor has to reason about what the funnel *says*, not just how it's built.
4. **There is a real winning design pattern.** Open with a question, keep the first page lean, front-load interaction, reach the form by the first third. The losing pattern is a static hero page chained to a thank-you.
5. **Builders A/B test blind and lose ~59% of the time.** That is the clearest case for the product: raise the hit rate above 41% and the value is immediate and measurable.

## The data foundation we built

- A per-funnel feature matrix: 196K versions, structure parsed from the live snapshot (question types, form fields, social proof, media, CTAs, page order).
- A content-derived vertical taxonomy: 11 verticals, 34 sub-niches, clustered from the funnel copy itself, not a self-reported signup field. The platform is **73% German recruiting funnels**: trades, nursing, drivers, warehouse, sales, dental staff.
- Behavioral drop-off from the live event stream, and the full A/B-test history with outcomes.

## Finding 1 — Niche dominates, so the score must be relative

CVR spans 12x across verticals (1.7% beauty to 23% US disability benefits), and 3x even *inside* recruiting (1.1% dental staff to 3.5% sales). A variance split puts 87% of the difference on the account (niche, offer, audience, traffic) and ~13% on funnel design.

The product consequence is concrete: a recruiting funnel at 2% might be excellent for recruiting, and a benefits funnel at 2% is poor for benefits. The score compares a funnel to its own niche, and recommendations come from what the top funnels *in that niche* do.

## Finding 2 — The winning design pattern (structure + sequence)

This is the part that goes beyond "add more steps." Comparing the top CVR quartile to the bottom, within each niche:

- **Open with a question, not a landing page.** In 18 of 32 niches the winning funnels' first page is an interactive question (loser to winner: 0% to 100%). Static content-only first pages and hero-image first pages are losing traits.
- **Keep the first page lean.** Winners use less media, fewer buttons, fewer components on page one.
- **Front-load interaction.** Questions in the first half, and the form reached by the first third of the funnel. Burying the form in the middle loses.
- **The reliable way to lose:** chaining static content/hero pages into a thank-you. A two-page "hero then thank-you" funnel sits in the 7th percentile of its niche.

The page archetype sequence confirms it. Winning openings: form or question. Worst opening: static content+media. Winning first-three-page sequences front-load questions and forms; losing ones stack passive content.

## Finding 3 — Content beats structure, and the score is feasible

Predicting a funnel's within-niche conversion percentile from its design alone (5-fold cross-validation):

| Predict from | Spearman ρ |
|---|---|
| niche only (baseline) | ~0 |
| structure | 0.26 |
| content (the copy) | 0.30 |
| structure + content | 0.37 |

Three things follow. The Funnel Score works: design ranks funnels within their niche at 0.37, and that is within niche, not the easy "dental beats cold e-commerce" rediscovery. Content carries more signal than layout. And the two are complementary, so the engine needs both.

ρ=0.37 means design explains a real but bounded slice of conversion. That is the right strength for a builder-facing tool: a meaningful nudge that shifts the odds.

## Finding 4 — Winning message angles, per niche

Since copy is the bigger lever, here is what converts within a niche:

- **Trades:** "work in Germany / Netherlands" relocation framing converts 3.5–7% vs ~1.9% for local job ads.
- **Coaching:** a live webinar (9.8%) beats a recorded course (6.4%), which beats agency/Weiterbildung framing (1.9%).
- **Real estate:** investment, tax, and retirement framing (3.8%) beats listing/exposé pages (1.4%).
- **Nursing:** development and apprenticeship framing beats "doctor's practice" context (0.7%).

## Finding 5 — The first page is the whole game

Live drop-off curves show a brutal cliff: the median funnel keeps only **10–17% of visitors past the first page**, then the curve is nearly flat. Whoever clicks past the landing usually finishes. First-page survival ranges 4x by niche (7% in technical recruiting to 30% in customer-advisor roles).

This splits the product into two levers. The first page drives volume and is where 85–90% of the loss happens. Structure and copy drive the quality of the minority who engage. A funnel can be weak on either, and the fix is different.

## Finding 6 — The causal reality (this is the pitch)

From 26,000 real A/B tests with their outcomes: the change a builder tries beats the original **only 41% of the time.** People iterate by gut and lose most of their experiments. Per niche it ranges 25% to 53%.

That is the core justification for the whole project. An intelligence layer that steers builders toward changes that tend to win in their niche raises a 41% hit rate, and every test feeds the model back. That flywheel is the moat.

## What this means for the product

The engine is a niche-conditioned benchmark plus a recommendation table: global priors ("open with a question, reach the form early, use live framing") with per-niche overrides ("but in beauty, cut the media; in nursing, lead with development not the practice"). A funnel gets diffed against its niche's winning profile, and the gaps become the recommendations, each with an effect size and a confidence.

It maps cleanly onto the existing roadmap: this is the data and model layer for the Funnel Score Widget (3.4), the recommendation surface (3.3), and the vertical benchmarks dashboard (3.6).

## Honest caveats

- Everything except the A/B aggregate is **associational, not causal.** Winners *correlate* with these traits. "Open with a question" partly reflects that the form is the conversion. "Abroad" angles partly attract a hotter audience.
- The clean test is the A/B history. We can already measure *how often* changes win, but not yet *which* changes win, because only 2% of the variant pages are in our parsed structure. Closing that gap (parsing the test pages) is the next real step and turns the playbook from "correlates with" into "causes."
- Behavioral drop-off is currently a 7-day window on the live events. The full 18-month pass runs off-peak to protect production.

## What to build next

1. Parse the A/B test pages so we can prove which changes cause lift, per niche.
2. Push the score past 0.40 with the full content embedding and the sequence features.
3. Widen the behavioral data, then add the page-1 retention diagnostic to the score.
4. Package the first per-niche playbooks (recruiting first, it is 73% of the platform).
