# Script-Referenz

Alle 36 Skripte in `analysis_2026-06-01/`, gruppiert nach Pipeline-Stufe. Zweck = erste Docstring-Zeile.
Ausführung immer aus dem Ordner heraus mit der venv: `.venv/bin/python <script>.py`. BQ-Skripte brauchen
authentifizierte `bq`/`gcloud`-CLI (nicht im Sandbox — `dangerouslyDisableSandbox`).

## Setup

```bash
cd analysis_2026-06-01
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

---

## 1. Daten-Extraktion & Ingestion (BigQuery / Mongo)

| Skript | Zweck |
|---|---|
| `pull_struct.sh` | Resilienter einmaliger Pull von `funnel_struct_v1` → lokales CSV (übersteht flaky BQ-Verbindung). |
| `extract_abreach.py` | Lean per-arm A/B-Reach, streaming (kein `$group`-Barrier → Output fließt kontinuierlich). |
| `extract_abtests.js` / `extract_abtest_pagefeats.js` | A/B-Test-Paare bzw. Page-Features der Test-Arme extrahieren. |
| `extract_dropoff*.js` | Drop-off / Page-Reach extrahieren (mehrere Varianten: fast, wide, batched, activities). |
| `overnight_extract.py` | Prod-schonende Activities-Extraktion über Nacht, läuft auf GCP-VM (laptop-unabhängig). |
| `redact_activities.py` | Lokaler PII-Redactor für mongoexport-Output (extended-JSON .jsonl). |
| `sample_activities.js` / `sample_collections.js` | Schema-Samples aus Mongo-Collections ziehen. |
| `inspect2.js`, `inspect_analytics_abtests.js`, `diag_coverage.js`, `diag_year.js` | Diagnose/Inspektion von Collections, Abdeckung, Jahresverteilung. |

> **Prod-Sicherheits-Regel** (aus `progress.md`): Schwerer als ein Point-Lookup auf großen Collections → BigQuery,
> NICHT mongosh auf prod (hat am 2026-06-03/04 zu Last/Failover beigetragen). Wenn mongosh: Secondary + maxTimeMS.

---

## 2. Niche / Vertical-Discovery

| Skript | Zweck |
|---|---|
| `cluster_verticals.py` | Funnel-Verticals aus Copy via TF-IDF + MiniBatchKMeans (frühe Version). |
| `cluster_embeddings.py` | **Semantische Vertical-Discovery**: multilinguale Sentence-Embeddings + KMeans (löst TF-IDF-Sprach-/Boilerplate-Fragmentierung). Erzeugt `embeddings.npy`. |
| `label_verticals.py` | Mappt entdeckte Cluster → menschliche Vertical-Taxonomie, schreibt Per-Funnel-Labels. |
| `niche_experiment.py` | Niche-Definitions-Test: ist der Funnel-JOB / das Value-Promise der bessere Schlüssel (Marcos Hypothese). |
| `granularity_sweep.py` | Wie viele Niches? Sweep über Cluster-Anzahl k, misst out-of-sample-Vorhersagewert. |
| `niche_classifier.py` | **Live-Niche-Classifier**: neuer Funnel → eine von 32 Niches + Confidence. Embedding→PCA(120)→LogReg, 91,7 % Top-1. Erzeugt `niche_classifier.pkl`. |
| `niche_health.py` | **Recalibration-Diagnostik**: soll die Taxonomie splitten/mergen? (split: Coaching/RE; merge: Trades-Cluster). |

---

## 3. Scoring (der Funnel-Score)

| Skript | Zweck |
|---|---|
| `content_vs_structure.py` | Wie viel Within-Niche-CVR ist aus Design vorhersagbar — Struktur vs. Content vs. beides? |
| `score_v2.py` | Score über 0,40 drücken: Struktur + Composition/Sequence + Page-Archetype + volles Content-Embedding. |
| `score_m2.py` | **M2 — Score härten.** Account-Holdout ρ=0,40, temporal ρ=0,48, 5-fold 0,48; Content +0,444. Erzeugt `funnel_score_model.pkl`. |
| `funnel_score.py` | `score(struct, embedding, niche) → Within-Niche-Perzentil`. Production-Wrapper über das M2-Modell für neue Funnels. |

---

## 4. Driver- & Kontrast-Analyse (die „Hebel")

| Skript | Zweck |
|---|---|
| `per_niche_drivers.py` | **Per-Niche-Feature-Importances** via Spearman: welche Merkmale helfen in einer Niche und schaden in anderer (16/23 kippen). Erzeugt `per_niche_drivers.csv`. |
| `contrast_mining.py` | Per-Niche Winner-vs-Loser strukturelle Kontraste. |
| `deep_composition.py` | Tiefer als Counts: Landing-Page-Composition + Formular-Platzierung + Frage-Front-Loading. |
| `page_archetypes.py` | Block-Composition + Sequence: jede Seite in einen Archetyp klassifizieren. |
| `message_angles.py` | Gewinnende Message-Angles pro Niche (Copy-Cluster innerhalb Niche, nach CVR gerankt). |
| `h1_lowfriction.py` | Hypothese 1: Low-Friction-Framing in Recruiting-Funnels. |
| `h2_length.py` | Hypothese 2: optimale Funnel-Länge ist sub-typ-spezifisch (Recruiting). |
| `dropoff_curves.py` | Per-Funnel-Retention-Kurven (Events-per-Page × Page-Order) → Page-1-Cliff. |

---

## 5. Kausale / A/B-Validierung (das „Absichern")

| Skript | Zweck |
|---|---|
| `causal_diff.py` | Control vs. Variant Page-Struktur pro A/B-Test diffen, `kept_original`-Verdict joinen. |
| `causal_diff_v2.py` | Verbesserte Kausal-Verlinkung: testKey → split_test_created → ended → kept_original. Erzeugt `causal_linked.csv`. |
| `per_niche_causal.py` | Gilt „Formular anfassen schadet" über Niches? Per-Niche Challenger-Win-Rate, Formular vs. nicht. |
| `proposal_backtest.py` | **Struktur-Proposal-Validity**: gewinnen die empfohlenen Struktur-Änderungen real? AUC 0,52, Formular rückwärts. |
| `content_proposal_backtest.py` | **Content-Proposal-Validity** (das Gegenstück): AUC 0,571, Richtung > Menge. Erzeugt `page_text.csv`, `arm_emb.npz`, `content_proposal_backtest.json`. |
| `content_ablation.py` | Ablation: ist die 0,571 nur Änderungsmenge? Nein — das Signal ist die Richtung (DIR 0,564). |

---

## 6. Recommendation & Produkt (der Output)

| Skript | Zweck |
|---|---|
| `recommend.py` | **Per-Niche-Recommendation-Generator** — der Produkt-Loop end-to-end: Niche → Perzentil → gerankte Experimente + „test-don't-apply". Opt-in Content-Ranker-Hook (`CONTENT_RANKER=1`). |
| `generate_suggestions.py` | **Live-Generierung** der funnel-spezifischen „try something like"-Copy-Vorschläge (Claude, an echtes Angebot gebunden). Braucht `ANTHROPIC_API_KEY`. |
| `content_ranker.py` | **Content-Change-Ranker**: `score_suggestion(current, proposed, niche) → P(win)`. Erzeugt `content_ranker.pkl`. |
| `build_demo.py` | Baut die Demo-Daten über die Live-Engine (`recommend.py`). Erzeugt `demo_data.json`. |
| `make_demo_html.py` | Baut die self-contained `demo.html` (27 Funnels eingebettet, offline öffnbar). |
| `make_charts.py` | Generiert die 14 PNG-Charts der V0-Findings (`charts/`). |
| `gen_share_assets.py` | Erzeugt die schlanken Files, damit der Analyzer ohne die 727MB `funnel_content.csv` läuft. |
| `analyze.py` | Engine für arbiträren Funnel-Input (der „paste a funnel"-Pfad: Campaign-ID oder Text). |
| `server.py` | Tiny stdlib-Backend für den „paste a funnel"-Analyzer (`:8754`, keine extra Deps). |

---

## Wichtigste Artefakte (`data/`)

| Datei | Inhalt |
|---|---|
| `funnel_score_model.pkl` | Trainiertes M2-Score-Modell (+ struct_cols, PCA, niche_cols). |
| `niche_classifier.pkl` | Niche-Classifier (clf + pca + classes + confirm_below=0.7). |
| `content_ranker.pkl` | Content-Change-Ranker (clf + pca + Per-Niche-Centroids). |
| `per_niche_drivers.csv` | Korrelations-Matrix Merkmal × Niche. |
| `niche_benchmarks.csv` | Median-CVR pro Niche (Benchmark fürs Perzentil). |
| `embeddings.npy` | 384-d Content-Embeddings aller ~196k Funnels (~290 MB). |
| `causal_linked.csv` | 9.951 verlinkte A/B-Tests (control/variant pageId, won, niche). |
| `page_text.csv` / `arm_emb.npz` | Per-Page Copy + Arm-Embeddings (Content-Backtest). |
| `*_validation.json`, `proposal_backtest.json`, `content_proposal_backtest.json`, `content_ablation.json` | Validierungs-Ergebnisse. |

> Große Quell-CSVs (`funnel_content.csv` 727MB, `page_features.csv` 136MB, `embeddings.npy` 290MB) sind
> Zwischendaten — werden von den Skripten erzeugt/gelesen, nicht versioniert (siehe `.gitignore`).
