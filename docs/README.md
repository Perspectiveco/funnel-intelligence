# Funnel Intelligence — Dokumentation

Vollständige Dokumentation des Funnel-Intelligence-Projekts: von der Idee über die validierten
Findings und die End-to-End-Pipeline bis zu jedem einzelnen Skript. Stand: 2026-06-10.

> Alle Analysen laufen lokal, auf Perspectives eigenen Daten, €0 (BigQuery-Scans im Cent-Bereich),
> reproduzierbar. Kein externes Benchmark, kein Raten.

## Was ist das?

Die Produktidee in einem Satz: **ein Funnel-Builder, der vorgeladen ist mit dem, was in deiner Branche
konvertiert.** Nicht generische KI — Muster aus 196.000 echten Funnels in genau deiner Nische, plus eine
über echte A/B-Tests geeichte Bewertung. Kein Wettbewerber kann das ohne unseren Datensatz.

Die Frage, mit der wir gestartet sind: *Kann ein Produkt wissen, was konvertiert — bevor du baust?*

## Dokumente

| Doc | Inhalt |
|-----|--------|
| [FINDINGS.md](FINDINGS.md) | Alle validierten Erkenntnisse, datiert (V0 → M2 → Content-Proposal-Validity). Die Beweislage. |
| [PIPELINE.md](PIPELINE.md) | Wie das Modell end-to-end läuft — Engine für Engine (ML vs. Statistik vs. LLM), mit der ehrlichen Korrelation-vs-Kausalität-Einordnung. |
| [SCRIPTS.md](SCRIPTS.md) | Vollständige Referenz aller 36 Skripte, gruppiert nach Pipeline-Stufe, mit Zweck + Inputs/Outputs + Run-Befehlen. |

Tiefer liegende Quelldokumente (nicht dupliziert, hier verlinkt):
- [`../analysis_2026-06-01/FINDINGS_V0_landscape.md`](../analysis_2026-06-01/FINDINGS_V0_landscape.md) — V0-Detailbefunde (§9–19).
- [`../analysis_2026-06-01/SHIP_PLAN.md`](../analysis_2026-06-01/SHIP_PLAN.md) — Produkt-/Ship-Plan + Gates.
- [`../analysis_2026-06-01/RUN.md`](../analysis_2026-06-01/RUN.md) — wie man den Analyzer startet.
- [`../.ai/progress.md`](../.ai/progress.md) — chronologisches Sessions-Log (Stand der Arbeit).
- [`../TEAM_LEARNING_niche_classifier.md`](../TEAM_LEARNING_niche_classifier.md) — Team-Learning: wie der Classifier gebaut wurde + Content-Validity.

## Repo-Karte

```
funnel-intelligence/
├── docs/                      ← diese Dokumentation
├── analysis_2026-06-01/       ← alle Skripte (.venv) + Quell-Docs
│   ├── data/                  ← Modelle (.pkl), Embeddings (.npy), Zwischen-CSVs, JSON-Ergebnisse
│   ├── charts/                ← 14 PNG-Charts der V0-Findings
│   ├── demo.html              ← self-contained Demo (27 Funnels, offline öffnbar)
│   ├── analyze.html + server.py ← Live-Analyzer (Campaign-ID → Score + Recs)
│   └── *.py / *.js            ← die Pipeline (siehe SCRIPTS.md)
├── .ai/progress.md            ← Sessions-Log
└── README.md                  ← Repo-Root
```

## Schnellstart (Analyzer lokal)

```bash
cd analysis_2026-06-01
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python server.py          # startet http://127.0.0.1:8754 (Modell lädt ~15-30s)
```
Dann Campaign-ID einfügen oder ein Beispiel klicken. Ohne Setup: `demo.html` doppelklicken
(self-contained, keine arbiträren IDs). Details: [RUN.md](../analysis_2026-06-01/RUN.md).

## Status & nächste Schritte

**Fertig & validiert:** Funnel-Score (M2), Niche-Classifier, Per-Niche-Driver, A/B-Backtests (Struktur +
Content), Recommendation-Generator, Content-Change-Ranker, zwei Demos.

**Offen (NEXT):**
1. **Live-Daten-Hookup** — BQ `funnel_lookup`-Tabelle, damit *jeder* Funnel (nicht nur die 56,5k im Cache)
   in Echtzeit aufgelöst wird.
2. **`generate_suggestions.py` mit echtem API-Key** laufen lassen → Copy-Vorschläge für *alle* Funnels.
3. **Niche-Recalibration v1** (siehe `niche_health.py`).
4. **Der Live-Flywheel** — Vorschläge als A/B-Test ausspielen, Ergebnis zurückfüttern. Der eigentliche Moat,
   größter Bau-Schritt, ~½ Engineer.
