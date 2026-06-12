# funnel-intelligence

ML system predicting visitor conversion based on Perspective funnel sessions.

## 📖 Dokumentation

Vollständige Doku in [`docs/`](docs/README.md) — von der Idee über die validierten Findings und die
End-to-End-Pipeline bis zu jedem einzelnen Skript:

- [docs/README.md](docs/README.md) — Übersicht, Repo-Karte, Schnellstart, Status & nächste Schritte
- [docs/FINDINGS.md](docs/FINDINGS.md) — alle validierten Erkenntnisse (V0 → M2 → Content-Proposal-Validity)
- [docs/PIPELINE.md](docs/PIPELINE.md) — wie das Modell läuft, Engine für Engine (ML vs. Statistik vs. LLM)
- [docs/SCRIPTS.md](docs/SCRIPTS.md) — Referenz aller 36 Skripte
- [TEAM_LEARNING_niche_classifier.md](TEAM_LEARNING_niche_classifier.md) — wie der Classifier gebaut wurde

## Links

- **Project doc (Notion):** https://www.notion.so/perspectiveco/AIR-Discovery-Funnel-Intelligence-Customer-Specific-Outcome-Funnel-Score-317f87b6a844818ba970e102cf93ddc9
- **ETL plumbing:** [Perspective-Software/atlas-mongo-trigger](https://github.com/Perspective-Software/atlas-mongo-trigger) — MongoDB → BigQuery transfer scripts
- **BigQuery dataset:** `perspective-bi:funnel_intelligence`
