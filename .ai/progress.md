# Funnel Intelligence — Progress

## Session 2026-06-09 — CONTENT proposal-validity ANSWERED + content-change ranker shipped

### State: the open SHIP_PLAN/NEXT item "content-level proposal validity" is now answered. Content changes ARE pre-trainably predictive of A/B wins (unlike structure), but NOT via a "write like the niche average" rule — the signal is the DIRECTION of the copy change. Built the validated ranker into recommend.py. All local, BQ scan <1¢, reproducible (`content_proposal_backtest.py`, `content_ablation.py`, `content_ranker.py`).

### page→text join SOLVED (the blocker from the last session)
- A/B arms are pageIds; content was keyed by campaignVersionId. Fixed by pulling **per-page `content.plainText`** from BQ `mongodb_lemon_tool_api.components` for the arms in `causal_linked.csv` (latest non-deleted component per `_id`, concat by createdAt). **Use `plainText`, NOT `text`** — `text` is the template placeholder ("Sommer"/"[Template-Name]"), which was the noise flagged for the suggestion exemplars. Cached → `data/page_text.csv` (5,224 pages). Dry-run = 1.47 GB ≈ <1¢ (not the ~$1 feared).

### CONTENT-PROPOSAL BACKTEST (`content_proposal_backtest.py`, 9,737 linked tests, baseline 26.1%)
- Arm-level content embeddings (same MiniLM, content-only, 400-char cap). "Winning-content direction" = leave-account-out per-niche winner-arm centroid; `align = cos(variant,cent) − cos(control,cent)`.
- **A) DIRECTION fails:** toward 24.1% (−2.0pp), against 25.7%, strongest-toward 26.9% (+0.8pp). "Be more like the niche-winner average" does NOT win → must NEVER ship as blind advice (same Goodhart trap as structure).
- **B) DOSE-RESPONSE flat:** decile monotonicity −0.06. No "more toward = more win".
- **C) CAUSAL CHANGE-MODEL has real signal:** `won ~ content-delta (arm-PCA-100) + alignment`, GroupKFold by account → **OOS AUC 0.571**; top-10% predicted winners **34.4% (+8.3pp)**. Notably **better than structure's 0.522** → consistent with M2 (content is the lever, +0.444). A pre-trainable content prior EXISTS (structure had none).
- Saved: `data/content_proposal_backtest.json`.

### ABLATION — the signal is DIRECTION, not churn (`content_ablation.py`)
- MAG (change amount only) AUC **0.527** ≈ noise → it is NOT just "rewrote a lot wins".
- ALIGN (cosine-to-winner only) 0.533 (matches the flat TEST A).
- DIR (PCA delta, **magnitude removed**) **0.564**, top-10% **44.4%** (highest) → the WHICH-way of the copy change carries the signal.
- FULL 0.571. Saved: `data/content_ablation.json`.

### CONTENT-CHANGE RANKER shipped + wired (`content_ranker.py` + hook in `recommend.py`)
- `content_ranker.py`: fits the change-model on all 9,737 pairs (full per-niche winner centroids), saves `data/content_ranker.pkl`. `score_suggestion(current_text, proposed_text, niche) → P(win)`; `rank_change(c_emb,v_emb,niche)`. In-sample sanity: P(win) 0.696 won vs 0.108 lost (honest OOS = 0.571).
- `recommend.py`: opt-in hook (`CONTENT_RANKER=1`, off by default so the demo stays light) orders the generated copy rewrites by learned win-prob, every one still tagged "A/B-test". Verified live (Real-Estate funnel: two openers ranked 13% vs 8%).
- **Framing locked:** the ranker is a PRIORITISER for live A/B tests, not a guarantee. AUC 0.571 is real but modest → still gated by the flywheel.

### Implication (sharpens the previous session's note)
Content-validity is no longer "open": there IS a learnable content prior (unlike structure), strong enough to RANK copy experiments, too weak for blind single-recs. So: recommend content changes as ranked, A/B-test-framed hypotheses (never "copy the niche average"), and the LIVE flywheel remains CORE to upgrade odds → causal claims.

### NEXT (remaining content thread)
- Run `generate_suggestions.py` with a real ANTHROPIC_API_KEY to populate suggestions for ALL funnels (not just the 9 demo), then the ranker scores them at scale.
- Extend the ranker beyond openers to headline/CTA rewrites; quality-filter the winner exemplars before prod.
- Optional: interpret WHICH content directions win (probe the PCA dirs / content features the model keys on) per niche.

---

## Session 2026-06-05 (eve) — M2 score hardening + linchpin backtest DONE

### State: M2 score hardened + proposal-validity backtest run. Both the SHIP_PLAN's open score-validity gates and the linchpin recommender test are now answered. All local, €0, reproducible (`score_m2.py`, `proposal_backtest.py`).

### M2 — score validation PASSED both hard tests (`score_m2.py`, 107.7k funnels / 57.3k accounts / 32 niches)
- **account-holdout (GroupKFold by campaignId) ρ=0.403** — generalises to UNSEEN accounts, so ρ=0.48 was NOT memorising the account. Past the 0.40 V1 gate even on the hardest split.
- **temporal (train old → predict new, time from ObjectId prefix) ρ=0.483** — predicts the FUTURE, not just fits the past.
- plain 5-fold ρ=0.481 (the number we quote). **Drivers (perm-imp):** content embedding block **+0.444** ≫ all structure (~0.18); top structural q_form +0.052, n_form_fields +0.047, n_buttons +0.023. → content is the lever.
- Saved: `data/funnel_score_model.pkl` (model + struct_cols + PCA), `data/niche_benchmarks.csv` (median CVR per niche), `data/M2_validation.json`, `data/M2_run.log`.

### LINCHPIN — proposal-validity backtest (`proposal_backtest.py`, 9,935 linked A/B tests, baseline 27.0%)
- **Causal change-model** (won ~ variant−control page-feature deltas, GroupKFold by account): **AUC 0.522 ≈ no signal**; top-decile predicted winners ≈ baseline. → **No pre-trainable structural recommender prior.** Flywheel must run LIVE; cannot be cold-started from structural change features.
- **Score-direction causally NON-NEGATIVE (good):** toward-score variants win 30.1% (+3.1pp) vs against-score 22.7% (−4.3pp). Safe soft prior, but too weak for confident advice and does NOT strengthen with magnitude.
- **Goodhart located:** the score's biggest structural lever (forms) is causally BACKWARDS — add a form-question 10.9%, add inputs 11.3%, REMOVE a form-question 5.4% (all ≪27%). Recommender must NEVER advise touching the form despite the score liking it. Only "add components/media/CTA" mildly beat baseline (+2 to +3.5pp).
- Saved: `data/proposal_backtest.json`.
- **NOTE:** real baseline is **27.0%** (causal_linked.csv), not 41% — earlier "41%" in this doc was stale; SHIP_PLAN §1's 27% is correct.

### LIVE NICHE CLASSIFIER — DONE (`niche_classifier.py`, §7 gate 2 closed)
- Niche labels are a 1:1 relabel of the 35 content-embedding clusters → a classifier recovers them from the raw embedding, so a NEW funnel snaps to a benchmark niche on the fly (no re-clustering).
- **top-1 agreement 91.7% / top-3 99.8%** on account-holdout (GroupKFold by campaignId, 196k funnels / 87k accounts).
- **Confidence gating** (the "is this your niche?" UX): conf≥0.7 auto-assigns 71% of funnels @ 98.4%, conf≥0.9 → 48% @ 99.7%; below threshold show top-3 + ask user. Saved with `recommend_confirm_below=0.7`.
- Weakest (most boundary confusion): Coaching/Webinar 84%, Food/E-com, IT/PM, Generic/Untitled, Real Estate, Sales/Lead-gen. Strongest: Dental 97.5%, Solar, LKW drivers.
- **HONEST CAVEAT:** accuracy = agreement with the self-defined cluster label (boundary sharpness + generalisation), NOT external ground truth.
- Saved: `data/niche_classifier.pkl` (clf+pca+classes+threshold), `data/niche_classifier_eval.json`. Handoff snippet printed at end of script.

### PER-NICHE DRIVERS — global features are wrong; recommendations must be per-niche (`per_niche_drivers.py`)
- Within-niche Spearman(feature, cvr), visitors>=500, per niche vs global. **16 of 23 structural factors FLIP SIGN across niches** → a global recommendation is wrong for ≥1 niche on ~70% of factors. Confirms "no global features."
- **3 factor groups for the recommender:**
  - *Universal (sign stable, recommend globally as "tend to"):* reach the form earlier (`first_form_relpos` −31/31), don't open with a static/media-led hero (`lp_content_only`/`lp_media_led` − in ~20), front-load questions (`q_first_half`), more interactive steps (`n_result_pages`/`has_branching`/`n_pages`).
  - *Niche-specific (FLIPS, must be per-niche):* `lp_media` (+9/−12), `lp_components` (+12/−12), `media_per_page`, `q_choice`, `n_media`, `n_social`, `lp_buttons`.
  - *Causal blocklist (strongest +corr, but A/B-harmful → "test, don't apply"):* `q_form` (+31/31), `n_form_fields` (+28), `lp_is_form`.
- Per-niche seeds differ concretely (Real Estate = longer branching quiz; Sales/Lead-gen = page-1 question, avoid media-heavy page 1; Coaching = front-load form). Matrix for all 32 niches → `data/per_niche_drivers.csv`.
- **Agreed product direction:** correlational recs are fine to SHIP NOW if framed "funnels like yours that convert well tend to X", per-niche, minus the causal blocklist; flywheel upgrades strong correlations → confident causal claims. Same recipe for content.

### RECOMMENDATION GENERATOR — the product loop, end to end (`recommend.py`)
- funnel → classify niche (+conf, ask-user if <0.7) → within-niche CVR percentile → ranked recs, split:
  - **Recommended experiments** (correlational, niche-aware, framed "funnels like yours that convert well tend to…"), each tagged universal vs niche-specific + the per-niche corr + how far this funnel is from its niche's winners (top-quartile median).
  - **Test, don't apply** = the FORM (q_form/n_form_fields/lp_is_form): strongest +corr but A/B-harmful → always "A/B-test it", never a blind instruction.
- Demo confirms genuinely different advice per niche (Real Estate→branching/more steps; Sales/Lead-gen→page-1 question + less media; Coaching→form earlier + front-load questions). Universal factors: first_form_relpos, lp_media_led, q_first_half, n_result_pages (+ form, which is routed to test bucket).
- `recommend(cvid)` + `render()` ready; next = wire into demo.html and plug the score model's predicted percentile (needs score() wrapper — see below).

### NICHE RECALIBRATION DIAGNOSTIC — taxonomy is wrong BOTH ways (`niche_health.py`)
- **SPLIT (too broad):** Coaching/Webinar (sub-niches 2.1% vs 5.7%, ~50/50), Real Estate (1.5/2.8), Dental, Sales+appointment, Sales & skilled labor — balanced 2-way embedding splits with distinct CVR.
- **MERGE (too granular):** recruiting-trades cluster redundant — Skilled-trades+Welding (centroid cos 0.77, driver-corr 0.88, cvrΔ 0.3pp) + Construction/Welding/Trades variants.
- → recalibration is region-specific, not global. Re-runnable: propose split/merge → human approves → retrain classifier; long-term = continuous k-NN, no fixed buckets.

### DEMO WIRED + score() WRAPPER (`build_demo.py` now imports `recommend.py`; `make_demo_html.py`; `funnel_score.py`)
- `demo.html` rebuilt through the LIVE engine: 27 funnels / 10 niches. Shows niche + **confidence pill** (ask-user state for <0.7; 7/27 samples low-conf), within-niche score, then recs split into **Recommended experiments** (universal/niche-specific badges + corr) and **Test, don't apply** (form; 14/27 samples). Single source of truth = recommend.py (no duplicated logic). Verified rendering via preview DOM (no JS errors); screenshot tool had a viewport bug, DOM inspection confirmed all sections.
- **`funnel_score.py`** = production new-funnel scorer: `score(struct, embedding, niche) -> within-niche percentile`. FIXED the model-reuse bug — `score_m2.py` now persists `niche_cols` (one-hot order) in `funnel_score_model.pkl`; model re-run. Smoke-tested (predicted tracks actual; OOS honest number ρ=0.40).
- Preview infra: `.claude/launch.json` (project) + `~/.claude/launch.json` (global, `funnel-demo` on :8753 serving the analysis dir).

### SPECIFIC SUGGESTIONS — "try something like: XXX" wired into recommender (round 1)
- Problem: structural recs were generic ("stop leading with a hero") — told the direction, not the action.
- Fix in `recommend.py`: (1) the 3 redundant page-1 opener recs (lp_has_question/lp_content_only/lp_media_led) now **consolidate into ONE** rec "Rework your page-1 opener…"; (2) it carries a **funnel-specific suggestion** = concrete opener questions generated from the funnel's OWN content (e.g. BStoked campervan-roofs → "Für welches Fahrzeug suchst du ein Aufstelldach? → VW Bus · Ford · Mercedes · Anderes").
- Round-1 generation: authored by the LLM in-session into `data/suggestions.json` (9 demo funnels w/ opener recs). **Production seam:** `SUG=suggestions.json`; swap that for a live LLM call (funnel content + niche winner-pattern + real winner openers as exemplars). No env API key/SDK/network here, so in-session authoring is the round-1 transport; architecture identical.
- Framing guardrails: every suggestion labelled "A/B-test — generated from your funnel, not a guaranteed win"; constrained to the funnel's real offer (no invented claims/discounts).
- Demo: tailored "✎ Try something like" blocks now on **17/27 funnels** — 9 opener rewrites + 8 open-text questions. Suggestions keyed per rec-feature in `suggestions.json` (cvid → {feat → {current?, try[]}}); `recommend.py` attaches by feat. Honest scope: only COPY-suggestible recs get a block (openers, open-text qs); structural recs (cut media, add branching, reduce buttons) intentionally have none — no fake copy. Verified both block types render in-browser (opener shows "replaces your current opener"; open-text omits it). Generator reads the actual funnel so copy stays relevant even when niche label is coarse (BStoked 41%).

### LIVE GENERATION MODULE — production version of the suggestion seam (`generate_suggestions.py`)
- Assembles per-funnel prompt = funnel's OWN page-1 copy + niche winner-rate (% open-with-question) + real winner openers as exemplars + guardrails (A/B-test framing, real-offer-only, funnel's language, strict-JSON out). Calls Claude (`anthropic` SDK, model `claude-sonnet-4-5`) → merges into `data/suggestions.json`.
- **Verified here end-to-end EXCEPT the authenticated call**: 9 opener prompts assembled correctly → `data/suggestion_prompts.jsonl`. No usable API key in this sandbox (harness proxy doesn't expose one to subprocesses) → graceful fallback, kept the in-session suggestions. **To go live: run where `ANTHROPIC_API_KEY` is set** (Alex's machine / CI) → regenerates suggestions for all funnels → rebuild demo. SDK now installed in `.venv`.
- Refinement flagged: winner exemplars are noisy (`[Template-Name]` placeholders, spammy ones) → filter exemplars for quality before prod; the funnel's own content already drives relevance so output stays on-topic regardless.

### "ANALYZE ANY FUNNEL" — paste-a-funnel feature, backend + page (`analyze.py`, `server.py`, `analyze.html`)
- Engine runs on ARBITRARY input, all local: embed text (MiniLM `paraphrase-multilingual-MiniLM-L12-v2`, cached, no API) → classify niche → recommend.
- **TEXT mode** (paste funnel copy, any language): niche + confidence + the niche's winner-pattern PLAYBOOK (universal/niche-specific, form→test bucket) + 2 real winner-opener exemplars. No /100 score (needs structure). Verified: nursing copy→R:Nursing&care 100%, LKW→R:Drivers 99%, Elektriker→R:Service&welding 99%.
- **FULL mode** (known campaignVersionId, later a URL): complete `recommend.recommend()` with /100 score + personalised recs + generated suggestion.
- Backend = stdlib `server.py` (ThreadingHTTPServer :8754, no extra deps): `GET /`→analyze.html, `POST /analyze {text,name|cvid|url}`. Run: `.venv/bin/python server.py`. Registered in `~/.claude/launch.json` as `funnel-analyze` for preview.
- **URL ingestion NOT wired** (deliberate): published funnels are client-rendered SPAs, so a link needs either a headless render or (cleaner) Perspective's own data/API to pull content+structure. **Waiting on a sample published funnel URL from Alex** to see how content is served, then wire it.
- BUG fixed during build: `analyze.html` had `don\\'t` (double backslash) in a JS string → killed the whole inline script (no button worked); now `don\'t`. (demo.html was fine — it went through Python.) Verified full click→render flow in-browser.

### FUNNEL-ID ANALYZER — shareable demo: paste a campaign ID → score + recs + methodology TLDR
- `analyze.py` now resolves a **campaignId OR campaignVersionId** → scored version (CID2VER = highest-traffic scored version per campaign; covers **~56.5k campaigns / 196k funnels**, $0, local cache). `analyze_id()` → full `recommend.recommend()` (niche+conf, /100 score, recs, suggestions, exemplars); unknown id → friendly message.
- `server.py` routes `POST /analyze {funnel_id}`. `analyze.html` rebuilt: campaign-ID is the primary input + 3 example chips spanning scores (Physios Service 76 / OC Lead Funnel 49 / BALIMO 27, distinct niches), raw-text mode tucked in a <details>, and a **2-min methodology TLDR** (<details>: niche 92%, score ρ=0.40 acct-holdout/0.48 temporal, per-niche playbook, 13%/Goodhart/copy caveats).
- Verified: curl campaignId→correct name/niche/score/recs (Physios Service neu → R:Trades&technical 100%, score 76, 5.97% vs 2.8%); bad-id handled; page serves all elements; inline JS passes `node --check`; render() proven live earlier. (Preview screenshot tool flaky this session — verified via curl+DOM+parse instead.)
- **To run/share:** `cd analysis_2026-06-01 && .venv/bin/python server.py` → open http://127.0.0.1:8754 (model loads ~10-15s at startup). Shareable = run the backend + open page; a single static file for non-technical recipients OR any-funnel-beyond-snapshot both need the BQ hookup (below).
- **BQ live lookup (priced, next step):** `mongodb_lemon_tool_api.components` (99M rows, fresh) has campaignId+pageId+type+content JSON = source for content_text+features; `domains` table enables URL→funnel later. Cheap design = one-time `funnel_lookup` table clustered by campaignId (~$1 build, ~$0/lookup) vs naive full-scan ~$0.40/query. NOT built (cache covers 56.5k for free).

### SHAREABLE STATIC DEMO — `demo.html` = single self-contained file (no backend)
- Added the 2-min methodology TLDR (<details>) to `make_demo_html.py` → `demo.html`: 37KB, **27 funnels embedded, 0 external refs / 0 fetch** → opens by double-click, works offline, fully shareable. Dropdown → niche + /100 score + recs + tailored suggestions + methodology.
- This is the "send-anyone" artifact (uses the earlier demo's curated funnels). The `server.py`+`analyze.html` funnel-ID analyzer remains the live "paste ANY of 56.5k IDs" version (needs the backend running).

### DATA-HYGIENE NOTE
- Niche strings inconsistent across scripts: `R: x` (deep_composition / causal_diff_v2) vs `R:x` (score_m2 / classifier / benchmarks). `recommend.py`+`niche_health.py` normalize with `.replace("R: ","R:")`. Should standardize at source.

### Implication for the product (folded into SHIP_PLAN UPDATE block)
Ship the SCORE (validated, relative). Recommendations stay hypotheses/experiments. The true lever is CONTENT (+0.444), which the A/B page features don't capture → the next causal test needs arm-level COPY, not structure. Confirms "A/B flywheel is CORE, not Phase 4."

---

## Session 2026-06-04/05 — V0 analysis → product framing

### State: V0 feasibility DONE. Everything in BigQuery + local (`analysis_2026-06-01/`), €0, reproducible.

### What's proven (all on the full real dataset, 275M sessions, in BQ `perspective-bi.funnel_intelligence`)
- **Funnel Score is feasible**: design predicts WITHIN-NICHE CVR percentile at **Spearman ρ=0.48** (5-fold CV, held by funnel). Structure alone 0.38, content(copy) alone 0.40, combined 0.48. Content > structure. Past the plan's 0.40 V1 gate. (`score_v2.py`)
- **87/13**: ~87% of CVR variance is account/niche/audience/traffic, ~13% funnel design → score must be percentile WITHIN niche.
- **Design playbook** (within-niche winners vs losers, `contrast_mining.py`, `deep_composition.py`): open page 1 with a question (not hero), keep page 1 lean, reach form by first third, front-load interaction. Losing pattern: static hero→thank-you (7th pct). Message angles per niche (`message_angles.py`): trades "work in Germany/NL"; coaching live-webinar≫recorded≫agency; RE investment/tax; nursing development>practice.
- **Page-1 cliff** (`dropoff_curves.py`, 7-day activities sample): median funnel keeps only 10-17% past page 1; first-page survival varies 4× by niche.
- **CAUSAL truth** (`causal_diff_v2.py`, ~10k A/B tests linked): challenger beats control only **41%** baseline. Adding a form question wins only ~11%; touching the form is the riskiest edit. **Correlation ≠ safe recommendation (Goodhart, measured).** → A/B flywheel is CORE, not Phase 4.
- **Niche definition resolved** (`niche_experiment.py`, `granularity_sweep.py`): primary key = funnel JOB/value-promise (transfers across industries), industry = secondary modifier, audience = unseen driver A/B resolves. **34 niches WAY too coarse** — niche→CVR out-of-sample ρ doubles 34→1000, no plateau. Use fine/continuous (k-NN "funnels like yours"); coarse pooling only for the causal layer.

### Key data-model facts (Mongo prod `heroku_8mgcnmlb`)
- Drop-off / per-arm CVR ONLY in `activities` (4.4B docs, ~2TB, PII-heavy). sessions = entry+outcome only, NO path. `analytics` collection is LEGACY (page-analytics collapsed after 2023; ~14k recent versions only).
- A/B tests: `campaign_ab_tests` (control/variant pageId pairs) + `split_test_created/ended` events in BQ `product.product_events_raw` (kept_original verdict). HUMAN-led historically; product flywheel must be AI-led (net-new build; manual split-test primitive exists, programmatic+generation+stats+orchestration+feedback = net-new).
- BQ `mongodb_lemon_tool_api`: components/pages/versions now FRESH (synced 2026-06-04; components 98.9M). Use these for structure, not snapshot re-parse.

### CRITICAL incident + rules
- **We caused prod load** (2026-06-03/04): early mongosh scans (inspect/diag/dropoff on analytics+activities) ran on the PRIMARY (mongosh defaults to primary; no maxTimeMS) — likely contributed to a failover. OWNED in Slack.
- RULES NOW: heavier-than-point-lookup on big collections → BigQuery, NOT mongosh on prod. If mongosh: secondary + maxTimeMS. Per-person DB users + analytics node recommended.
- **Claude Code sandbox BLOCKS BigQuery** (TimeoutError 60) — pass `dangerouslyDisableSandbox:true` on Bash for bq/gcloud. Mongo only reachable unsandboxed + URI in a local file (laptop $PS_MONGO_URI not in non-interactive shell).
- Activities pull = zero-risk ONLY via restored backup temp-cluster or analytics node (needs Atlas project admin — Alex has only read). PARKED. Not needed for causal direction (kept_original suffices).

### Deliverables produced
- **Notion** (single source, child of mother doc): https://app.notion.com/p/374f87b6a8448104b465d5d3e318273f — V0 findings, ρ explainer, roadmap readiness check, AI-led flywheel section, niche resolution, next steps (who does what).
- **Deck**: `analysis_2026-06-01/marco_funnel_intelligence_deck.html` (10 slides, Perspective CI).
- **Demo**: `analysis_2026-06-01/demo.html` (27 real funnels → niche + within-niche score + recommendations with causal caveats). Marco ask #1.
- FINDINGS_V0_landscape.md §9-19 = full detail. Scripts all in `analysis_2026-06-01/` (.venv).

### Marco meeting takeaways (transcript: gdoc 1dnJ2jMBQgUok5hx9D1VG8b_cCQkZvomplitupmCtD8s)
- Structural = baseline/fundament; BEHAVIORAL (drop-off, clicks, dwell) is what makes the recommender great → both feed engine, staged.
- Niche ≠ industry; it's job + target audience (he said "thousands of audience profiles").
- Wants an easy demo app (built). Phase 1 = industry + funnel-goal + structural features as the fundamental layer.

### Resourcing decision (with Marco, pending)
- Alex + Claude = the ML/data-science engine (can do M1 + M2 model). Needs ~½ an engineer for production (serving API, instrumentation, codebase integration), design+FE for the widget. NOT 2 FTEs.

### NEXT (DONE this session: M2, backtest, classifier, per-niche drivers, recommendation generator, niche-health diagnostic, demo wiring, score() wrapper). Remaining, Alex+Claude, safe/local:
- **BQ live lookup + one static shareable build** — (1) build the `funnel_lookup` table (clustered by campaignId) so ANY funnel beyond the 56.5k snapshot resolves cheaply; (2) optionally bake a static self-contained HTML (curated funnels) for zero-setup sharing to non-technical folks.
- **URL ingestion** (lower priority — funnel-id sidesteps it) — `domains` table + headless render; needs a sample published URL.
- **Run `generate_suggestions.py` with a real key** (Alex's machine/CI) to populate ALL funnels (not just the 9 demo ones); then extend it beyond openers to headline/CTA rewrites + add exemplar quality-filtering.
- **Niche recalibration v1** — act on `niche_health.py`: split Coaching/Real-Estate, merge the trades cluster, retrain classifier (or move to continuous k-NN).
- **Content-level proposal validity** — redo the backtest with arm-level COPY embeddings (the +0.444 lever), not the 9 structural page feats. Blocker: A/B arms are pageIds; `funnel_content.csv` is keyed by campaignVersionId — need page→text join before this can run.
- **Recommendation guardrails** — encode "never recommend touching the form / adding form-questions"; surface only the mildly-causal structural moves (add components/media/CTA) as low-confidence experiments; everything else gated on the live flywheel.
- **Wrap `score()` for handoff** — thin predict wrapper over `funnel_score_model.pkl` returning within-niche percentile (model is saved; convenience fn not yet written).
- Standing artifact: `analysis_2026-06-01/SHIP_PLAN.md` — updated with the M2 + backtest results (see UPDATE block at top).
</content>
