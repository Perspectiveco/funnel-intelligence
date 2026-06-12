# Funnel Intelligence — What It Takes to Ship (VP ML / Product / Data-Eng review)
*Devil's-advocate, grounded only in what we've measured. 2026-06-05.*

## UPDATE 2026-06-05 (eve) — score hardened + linchpin backtest run (`score_m2.py`, `proposal_backtest.py`)
- **Score validation PASSED both hard tests** (107.7k funnels / 57.3k accounts): account-holdout ρ=**0.403** (generalises to UNSEEN accounts — not memorising the account), temporal ρ=**0.483** (train-old→predict-new — predicts the future). Plain 5-fold 0.481. → §7 gates 1 & ³(score half) clear. Drivers: content embeddings dominate (perm-imp **+0.444** vs ~0.18 all structure combined); top structural levers q_form +0.052, n_form_fields +0.047.
- **Proposal-validity backtest run (9,935 linked A/B tests, baseline 27.0%):**
  - *Causal change-model* (won ~ variant−control deltas, GroupKFold by account): **AUC 0.522 — essentially no signal.** Top-decile predicted winners ≈ baseline. **No pre-trainable structural recommender prior exists.** The flywheel must run LIVE; it cannot be cold-started from structural change-features.
  - *Score-direction* is causally **non-negative**: moving toward the score's preference wins 30.1% (+3.1pp) vs 22.7% (−4.3pp) against — a soft, safe prior, but too weak to ship as confident advice and it does NOT strengthen with magnitude.
  - **Goodhart, precisely located:** the score's single biggest structural lever (form questions/fields) is causally **backwards** — adding a form-question wins 10.9%, adding inputs 11.3%, *removing* a form-question 5.4% (all far below 27%). The recommender must NEVER advise touching the form, despite the score rewarding it.
- **Net:** ship the SCORE (validated, relative); recommendations stay hypotheses; the real lever is CONTENT (the +0.444 block), which the A/B page features don't even capture → next causal test needs arm-level copy, not structure.

## 0. The honest one-paragraph state
We proved a **Funnel Score** is feasible (design predicts within-niche conversion at ρ=0.48, content>structure). That part is real and shippable. But the **recommendations** — the thing customers act on — are the opposite of solved: a naive "do what winners do" recommender produces changes that *lose or do nothing* in real A/B tests (see §1). The whole product hinges on making recommendations trustworthy, and we have only thin causal evidence so far. **Ship the score; do not ship blind recommendations.**

## 1. THE central risk: descriptive ≠ causal (measured)
Cross-sectional winners have more form questions / fields / media. But in ~10k real A/B tests, *adding* those wins **11–28% of the time, at or below the 27% baseline.** Only "more components overall" barely beats baseline (+2pp). 

Implication: the headline playbook describes what good funnels *are*, not what *makes* a funnel better. A recommender that ships these as advice would, on the evidence, make customers' funnels **worse or no better** ~70–90% of the time, then lose trust. This is the make-or-break problem.

**The only resolution is the AI-led A/B flywheel:** propose from priors → test → confirm → only then recommend with confidence. Until the flywheel has run, recommendations should be framed as *experiments to try*, never as *known fixes*. **Caveat on the caveat:** kept_original is a noisy outcome proxy, n per change is small, and diffs are multi-variable — so this is directional, but it points the same way as every other causal cut we've done.

## 2. What we MUST test before trusting recommendations
1. **Proposal validity (done, failed for naive):** §1. Re-run with *clean per-arm CVR* (not kept_original) once we have it, to confirm magnitude.
2. **Temporal score validity:** does the score predict *future* conversion (train on month t, predict t+1), not just contemporaneous? A score that only fits the past is useless for new funnels.
3. **Held-out + leakage check:** ρ=0.48 was 5-fold by funnel; verify on funnels from accounts never seen in training (account-level holdout) — otherwise we may be learning the account, not the design.
4. **Niche-classifier accuracy:** build the live classifier; measure misassignment rate (a wrong niche = a wrong benchmark = wrong advice).
5. **The real recommendation test:** human-in-the-loop AI-led A/B — propose a change, run it, measure lift vs the 27% baseline, per niche. This is the only test that proves the product works. Everything before it is a proxy.
6. **Behavioral lift:** does adding drop-off/dwell/click features materially raise ρ above 0.48? (Needs the activities pipeline.)

## 3. Data we need (in priority order)
- **Reliable fresh structure pipeline** — components/pages/versions synced (currently Airbyte, fragile/was stale). The score can't run on hand-pulled data.
- **A live niche classifier** — assign a *new* funnel to a niche on the fly. We have clusters, not a classifier.
- **Clean per-arm A/B outcomes** — the flywheel's instrumentation (per-arm CVR + significance), replacing the noisy kept_original proxy.
- **Behavioral data** (`activities` → BigQuery via an **analytics node or sanctioned export**, NOT ad-hoc prod scans). The richest signal Marco wants; blocked behind infra + governance.
- **Target-audience / ad-targeting data** — the missing niche axis (Marco's point). Funnel content only proxies it.
- **Conversion-label hygiene** — bots, duplicates, partial completions.

## 4. How we showcase it (sequenced, lowest-risk first)
1. **`demo.html` (built)** — internal, for Marco + engineers. Makes the propose→test→confirm flow tangible.
2. **Internal dashboard** — CS/onboarding use the score + recs to advise customers. Validates advice quality with zero customer-trust risk.
3. **Tight beta** — a few friendly *high-traffic* customers, framed as beta, advisory only, behind a flag.
4. **Case study** — take a low-scoring funnel, run an AI-proposed change as an A/B, show the lift. One real win is worth more than the deck.
5. **In-editor widget (3.4)** — only after the flywheel has earned trust. Score first, recommendations later.

## 5. Pitfalls — where this goes wrong (devil's advocate)
- **The 13% ceiling.** Design controls ~13% of CVR; 87% is audience/offer/traffic. A customer can follow every recommendation and see little change because their audience dominates. Manage expectations or the product reads as "broken."
- **Recommendations that lose** (§1) — the trust-killer. Mitigation: causal-gate everything; framing as experiments.
- **Goodhart / gaming** — once we score funnels, people optimize the score, not conversion; the two can decouple. Mitigation: relative score + causal recs + monitor score↔CVR correlation over time.
- **Cold start & low traffic** — new niches have no benchmark; low-traffic funnels can't reach A/B significance. The product genuinely works only for *high-traffic, common-niche* funnels at first. Be explicit about who it's for.
- **Niche misclassification** — wrong niche → wrong everything. Needs the classifier + a confidence threshold + "is this your niche?" user correction.
- **Copy is the bigger lever but the hard one** — content beats structure (ρ), but recommending/validating copy changes needs generation + is harder to A/B. The easy structural recs are the weaker lever.
- **Statistical validity** — multiple testing across thousands of funnels → false positives; small samples → underpowered. Need significance, multiple-comparison control, minimum-sample/stopping rules.
- **Selection bias in historical A/B** — the 35k tests are what people *chose* to test; priors built on them are biased. AI-led testing de-biases over time, but we start biased.
- **Pipeline fragility** — components was stale 10 months and nobody noticed. A customer-facing score on stale data is a silent failure.
- **Model/best-practice drift** — funnel styles and the Meta algorithm change; a 2025 model decays. Need drift monitoring + retraining.
- **Prod safety / governance** — we already caused a prod incident with ad-hoc Mongo. Behavioral data must come via an analytics node, with per-person DB users.
- **Privacy / GDPR** — benchmarking all customer funnels; behavioral data has PII. Needs the anonymization framing + legal sign-off before customer-facing.

## 6. Caveats to state plainly to anyone consuming this
- Everything structural/content is **associational**; the only causal evidence is the A/B aggregate (and it says the naive recs underperform).
- ρ=0.48 = design explains a real-but-bounded slice; the score is a *relative design-quality* signal, not a CVR oracle.
- Per-niche causal guidance is **data-limited** and fills in only as the flywheel runs.
- No behavioral data yet; the page-1 cliff is a 7-day sample.

## 7. Pre-launch checklist (gates before customers rely on it)
- [x] Temporal + account-holdout score validation (predicts future CVR) — DONE 2026-06-05: ρ 0.403 acct-holdout, 0.483 temporal (`score_m2.py`)
- [x] Live niche classifier with measured accuracy + user-correctable — DONE 2026-06-05: top-1 91.7% / top-3 99.8% acct-holdout; conf≥0.7 auto-assigns 71% @ 98.4%, else ask user (`niche_classifier.py`)
- [ ] At least one cohort of AI-proposed changes that **beat the 27% baseline** in real A/B (proof the recommender adds value)
- [ ] Recommendations framed as confidence-gated experiments, never blind commands
- [ ] Causal evidence store + flywheel loop wired (≥ human-in-the-loop)
- [ ] Reliable, monitored data pipeline (freshness alerts)
- [ ] Drift + niche-coverage + recommendation-outcome monitoring
- [ ] GDPR / anonymization sign-off; per-person DB users; analytics node
- [ ] Defined success metrics: do users who apply recs see lift? trust score? coverage?

## 8. Sequenced plan + owners
- **Now — Alex + Claude (local/BQ, no new resources):** harden score (temporal + account-holdout validation, SHAP, `score()`); build niche classifier; clean per-arm-CVR test design; keep the recommender in "hypothesis" framing.
- **Next — + ~½ engineer:** serving API; flywheel instrumentation (per-arm CVR capture); human-in-the-loop AI-led test on a few funnels; pipeline reliability + freshness alerts.
- **Later — team + Marco decisions:** behavioral pipeline (analytics node); audience data; full AI-led flywheel; in-editor widget; RAG playbooks; drift monitoring.

## 9. Go / no-go framing for Marco
- **GREEN to ship now:** the **Funnel Score** (relative, within-niche) + niche benchmarks, internal or beta, advisory.
- **RED until proven:** standalone "do X" recommendations. They must clear §7's "beat baseline in real A/B" gate first.
- **The one bet that makes or breaks it:** the AI-led A/B flywheel. It's not Phase 4 polish — it's the mechanism that converts our (unsafe) descriptive playbook into (safe) causal advice. Resource it early, or the recommender never becomes trustworthy.

**Bottom line:** we have a real, shippable *score* and a genuinely *unsolved* recommender. The honest move is to lead with the score, frame recommendations as experiments, and invest in the flywheel as the core — not to ship confident advice we've shown would mostly lose.
</content>
