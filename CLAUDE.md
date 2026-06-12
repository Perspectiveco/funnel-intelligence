# CLAUDE.md — Start hier (für KI-Agents & neue Mitwirkende)

Du arbeitest am **Funnel Intelligence** Projekt von Perspective. Dieses File ist dein Einstieg: was das ist,
wie man es startet, die Regeln, die man nicht verletzen darf, und was als Nächstes zu tun ist.

## Lies in dieser Reihenfolge
1. **dieses File** (Setup + Regeln + Stolperfallen)
2. [`docs/README.md`](docs/README.md) — Übersicht, Repo-Karte, Schnellstart, Status
3. [`docs/PIPELINE.md`](docs/PIPELINE.md) — wie das Modell end-to-end läuft (Engine für Engine)
4. [`docs/FINDINGS.md`](docs/FINDINGS.md) — alle validierten Erkenntnisse
5. [`docs/SCRIPTS.md`](docs/SCRIPTS.md) — Referenz aller 36 Skripte
6. [`.ai/progress.md`](.ai/progress.md) — chronologisches Sessions-Log = der jeweils aktuelle Stand. **Nach jeder
   Session hier oben einen neuen Eintrag ergänzen.**

## Was das Projekt ist
Ein Funnel-Builder, vorgeladen mit dem, was in der jeweiligen **Nische** konvertiert. Aus einer Funnel-ID →
Niche + ein an echter Conversion geeichter Score + nach Gewinnwahrscheinlichkeit gerankte Verbesserungs-Experimente.
Details: `docs/`.

## Arbeitsprinzipien (nicht verhandelbar)
- **Lokal, €0, reproduzierbar.** Alle Analysen laufen lokal auf Perspectives eigenen Daten. BQ-Scans im Cent-Bereich.
- **Ehrlich by design.** Correlation ≠ Causation. Empfehlungen sind **A/B-Test-Hypothesen**, keine Garantien.
  Der **Score ist ein ML-Modell, KEIN LLM** — niemals einen LLM scoren lassen (das wäre halluziniert und
  verschenkt den Moat). Das LLM textet nur die Copy-Vorschläge am Ende.
- **Caveats immer mitschreiben.** `kept_original` ist verrauscht, Niche-Labels sind self-defined, n pro Zelle
  teils klein → directional, nicht definitiv.

## Setup
```bash
cd analysis_2026-06-01
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # Python 3.10–3.12
.venv/bin/python <script>.py
```
Die großen Daten/Modelle sind **nicht im Repo** (`.gitignore`: `data/`, `*.csv`, `*.npy`, `*.pkl`, `*.jsonl`).
Sie werden aus BigQuery regeneriert (siehe „Daten" unten) oder intern per Drive/GCS geteilt.

## Stolperfallen (hart gelernt — lies das, bevor du Zeit verlierst)
- **BQ ist im Claude-Sandbox geblockt** (TimeoutError) → `bq`/`gcloud` mit `dangerouslyDisableSandbox: true` aufrufen.
- **`bq` braucht `gcloud` im PATH** für die Auth. Auf dieser Maschine liegt das SDK unter
  `~/Downloads/google-cloud-sdk/bin` (nicht im Default-PATH) → `export PATH="$HOME/Downloads/google-cloud-sdk/bin:$PATH"`.
  Billing-Projekt: `--project_id=perspective-bi`.
- **`git push` schlägt mit HTTP 400 fehl** (HTTP/2-Problem) → `git config http.version HTTP/1.1`, dann geht's.
  Repo-Regel: **nie direkt auf `main`**, immer Feature-Branch + PR.
- **NIE schweres mongosh auf prod** — hat am 2026-06-03/04 zu Last/Failover beigetragen. Alles Schwerere als ein
  Point-Lookup → BigQuery.
- **Content-Extraktion: `content.plainText` benutzen, NICHT `text`.** `text` ist nur der Template-Platzhalter
  („Sommer"/„[Template-Name]") = Rauschen.
- **Niche-Strings inkonsistent:** `R: x` vs `R:x` über Skripte hinweg → mit `.replace("R: ","R:")` normalisieren.
- **Daten sind intern/PII-nah** → niemals öffentlich posten. Nur intern (Drive/GCS mit Team-Zugriff).

## Daten (Quelle der Wahrheit = BigQuery)
- Aggregierte Funnel-Daten: `perspective-bi.funnel_intelligence` (275M Sessions Basis).
- Roh-Funnel-Struktur + Copy: `perspective-bi.mongodb_lemon_tool_api.components` (98,9M Zeilen; Text in
  `content.plainText`), `pages`, `versions`. A/B-Tests: `campaign_ab_tests` + Split-Events in `product.product_events_raw`.
- Lokale Artefakte in `analysis_2026-06-01/data/` (regenerierbar): Modelle (`funnel_score_model.pkl`,
  `niche_classifier.pkl`, `content_ranker.pkl`), Embeddings (`embeddings.npy`), Benchmarks, Backtest-JSONs.

## Pipeline reproduzieren (grobe Reihenfolge)
1. Discovery: `cluster_embeddings.py` (→ `embeddings.npy`) → `label_verticals.py`
2. Score: `score_m2.py` (→ `funnel_score_model.pkl`); Wrapper `funnel_score.py`
3. Classifier: `niche_classifier.py` (→ `niche_classifier.pkl`)
4. Hebel: `per_niche_drivers.py` (→ `per_niche_drivers.csv`)
5. Absichern: `causal_diff_v2.py` (→ `causal_linked.csv`) → `proposal_backtest.py`,
   `content_proposal_backtest.py` (zieht page→text aus BQ), `content_ablation.py`
6. Produkt: `recommend.py`, `content_ranker.py` (→ `content_ranker.pkl`), `generate_suggestions.py`
   (braucht `ANTHROPIC_API_KEY`), `make_demo_html.py` (→ `demo.html`), `server.py` (Live-Analyzer :8754)

## Offene NEXT-Items (woran weiterarbeiten)
1. **Live-Daten-Hookup** — BQ `funnel_lookup`-Tabelle (clustered by campaignId), damit *jeder* Funnel jenseits
   der 56,5k im Cache in Echtzeit aufgelöst wird (~$1 Build).
2. **`generate_suggestions.py` mit echtem `ANTHROPIC_API_KEY`** → Copy-Vorschläge für *alle* Funnels (nicht nur die
   9 Demo), dann vom Ranker bewerten; danach über Opener hinaus auf Headline/CTA erweitern.
3. **Niche-Recalibration v1** — `niche_health.py` umsetzen (split Coaching/RE, merge Trades), Classifier neu trainieren.
4. **Live-Flywheel** — Vorschläge als A/B-Test ausspielen → Ergebnis zurückfüttern → Modell schärfen. Der eigentliche
   Moat und größte Bau-Schritt (~½ Engineer).

> Wenn du etwas Substanzielles geändert hast: Eintrag oben in `.ai/progress.md` ergänzen und die betroffene Doc in
> `docs/` aktualisieren. So bleibt die nächste Person (oder KI) sofort anschlussfähig.
