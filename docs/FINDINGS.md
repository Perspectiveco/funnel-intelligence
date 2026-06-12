# Findings — die Beweislage

Alle Erkenntnisse, chronologisch, mit dem Skript, das sie erzeugt hat, und den ehrlichen Caveats.
Zahlen sind auf Perspectives echten Daten gemessen (≈196k Funnels, 275M Sessions in BQ
`perspective-bi.funnel_intelligence`; ~9.900 verlinkte A/B-Tests).

---

## 1. Funnel-Score ist machbar (V0 → M2)

**Ein Funnel-Design sagt die Within-Niche-Conversion voraus.** (`score_v2.py`, `score_m2.py`)
- 5-fold CV: **ρ = 0,48**. Struktur allein 0,38, Content/Copy allein 0,40, kombiniert 0,48 → **Content > Struktur**.
- Härtetests (`score_m2.py`): **Account-Holdout (GroupKFold) ρ = 0,403** (generalisiert auf *unbekannte*
  Accounts, also kein Auswendiglernen), **temporal (alt → neu) ρ = 0,483** (sagt die Zukunft vorher).
- **Der Hebel ist Content:** Permutations-Importance des Content-Embeddings **+0,444 ≫ alle Strukturmerkmale
  (~0,18)**. Top-Struktur: q_form +0,052, n_form_fields +0,047.

**87/13:** ~87 % der CVR-Varianz steckt in Account/Niche/Audience/Traffic, nur ~13 % im Funnel-Design.
→ Der Score muss ein **Perzentil innerhalb der Nische** sein, kein absoluter Wert.
*Implikation:* Selbst perfekte Funnel-Tipps bewegen nur einen kleinen, aber echten Teil — Erwartung managen.

Artefakte: `data/funnel_score_model.pkl`, `data/niche_benchmarks.csv`, `data/M2_validation.json`.

---

## 2. Niche = Job + Zielgruppe, nicht Industrie

(`niche_experiment.py`, `granularity_sweep.py`, `cluster_embeddings.py`)
- Primärschlüssel einer Niche ist die **Aufgabe / das Value-Promise** des Funnels (transferiert über Branchen),
  Industrie ist sekundärer Modifikator.
- **34 Niches sind zu grob:** Out-of-sample ρ (Niche → CVR) verdoppelt sich von 34 → 1000 Niches, **kein Plateau**.
  Für den Score wäre feiner besser → langfristig kontinuierliches k-NN („Funnels wie deiner").

### Live-Niche-Classifier (`niche_classifier.py`)
- Embedding → PCA(120) → Logistic Regression. **Top-1 91,7 % / Top-3 99,8 %** (Account-Holdout, 196k/87k).
- **Confidence-Gating:** conf ≥ 0,7 ordnet 71 % der Funnels automatisch zu @ 98,4 %; darunter → Top-3 + User fragen.
- Ehrlicher Caveat: „Accuracy" = Übereinstimmung mit dem selbst definierten Cluster-Label, **nicht** externer
  Ground-Truth. (Details: [TEAM_LEARNING](../TEAM_LEARNING_niche_classifier.md).)

---

## 3. Es gibt keine globalen Design-Regeln (`per_niche_drivers.py`)

- Methode: **univariate Spearman-Korrelation** (Merkmal × CVR), pro Nische vs. global.
- **16 von 23 Strukturmerkmalen kippen das Vorzeichen je Nische** → eine globale Empfehlung ist für ≥1 Nische falsch.
- Drei Gruppen:
  - **Universal** (Vorzeichen stabil): Formular früher erreichbar, nicht mit statischem Hero starten, Fragen
    front-loaden, mehr interaktive Steps.
  - **Niche-spezifisch** (kippt): Medien, Components, Choice-Fragen, Social Proof, Buttons.
  - **Causal Blocklist** (stark +korreliert, aber A/B-schädlich): das Formular → „test, don't apply".

Per-Niche-Seeds unterscheiden sich konkret (Real Estate = längeres Branching-Quiz; Sales/Lead-gen =
Frage auf Seite 1, wenig Medien; Coaching = Formular früh). Matrix: `data/per_niche_drivers.csv`.

---

## 4. Korrelation ≠ Kausalität — die A/B-Backtests

### Struktur (`proposal_backtest.py`, `causal_diff_v2.py`, `per_niche_causal.py`)
- 9.935 verlinkte A/B-Tests, **Baseline „Challenger gewinnt" = 26–27 %**.
- **Causal Change-Model AUC 0,522 ≈ kein Signal** → aus der Struktur-Änderung allein lässt sich nicht
  vorhersagen, wer gewinnt. **Kein pre-trainbarer struktureller Recommender-Prior** → Flywheel muss live laufen.
- **Goodhart lokalisiert:** der stärkste *strukturelle* Score-Hebel (Formular) ist kausal **rückwärts** —
  Formularfrage hinzufügen gewinnt nur ~11 %, entfernen ~5 % (beide ≪ 27 %). → Formular nie blind empfehlen.

### Content (`content_proposal_backtest.py`) — 2026-06-09
- page→text-Join gelöst: per-Page `content.plainText` aus BQ `components` (das Feld `text` ist nur
  Template-Platzhalter → Rauschen). 9.737 nutzbare Tests, Baseline 26,1 %.
- **A) „Sei wie der Niche-Durchschnitt" → funktioniert NICHT:** toward 24,1 % (−2,0pp), against 25,7 %.
  Dose-Response flach (Monotonie −0,06). → eindimensionale Centroid-Empfehlung ist ein Goodhart-Trap.
- **C) Aber der mehrdimensionale Content-Change ist lernbar:** Change-Model **OOS-AUC 0,571**, Top-10 % +8,3pp —
  **besser als Struktur (0,52)**. Passt zu M2 (Content ist der Hebel). Ein pre-trainbarer Content-Prior existiert.

### Ablation: das Signal ist die RICHTUNG, nicht die Menge (`content_ablation.py`)
| Modell | AUC | Top-10 % |
|---|---|---|
| MAG (nur Änderungsmenge) | 0,527 | 29,6 % |
| ALIGN (nur Cosinus-zum-Gewinner) | 0,533 | 32,2 % |
| **DIR (Magnitude entfernt)** | **0,564** | **44,4 %** |
| FULL | 0,571 | 34,4 % |
→ Nicht „wer viel ändert, gewinnt". Es zählt, *wie* (in welche Richtung) die Copy geändert wird.

**Verdict:** Content trägt genug Signal, um Copy-Experimente zu **ranken**, zu schwach für blinde Einzel-Recs.
→ Empfehlungen sind A/B-Hypothesen; der Live-Flywheel macht daraus Kausalität.

---

## 5. Weitere V0-Befunde

- **Page-1-Cliff** (`dropoff_curves.py`): der mediane Funnel behält nur 10–17 % nach Seite 1; die
  First-Page-Survival schwankt 4× je Nische.
- **Design-Playbook** (`contrast_mining.py`, `deep_composition.py`): Seite 1 mit Frage öffnen (nicht Hero),
  Seite 1 schlank halten, Formular im ersten Drittel erreichbar, Interaktion front-loaden. Verlierer-Muster:
  statischer Hero → Thank-you (7. Perzentil).
- **Message-Angles je Nische** (`message_angles.py`): Trades „Arbeit in DE/NL"; Coaching Live-Webinar ≫
  recorded ≫ Agency; RE Investment/Steuer; Pflege Entwicklung > Praxis.
- **58 % der A/B-Tests scheitern** → Nutzer können ohne datengetriebene Hilfe nicht zuverlässig optimieren.

Volle Details: [`FINDINGS_V0_landscape.md`](../analysis_2026-06-01/FINDINGS_V0_landscape.md) §9–19.

---

## Globale Caveats (gelten für alles oben)

- `kept_original` ist ein verrauschter Win-Proxy; A/B-Diffs sind multivariabel; n pro Nische×Merkmal teils klein
  → **directional, nicht definitiv**.
- Traffic-Quelle nicht kontrolliert (cold Meta vs. warm Google konvertiert anders) → Muster konsistent, aber
  Ergebnisse eher directional.
- Niche-Labels = self-defined Cluster-Agreement, nicht externe Wahrheit.
- Arm-Content = *aktueller* Content (kein historischer Snapshot zum Testzeitpunkt); page-level Text-Konkatenation
  verliert visuelle Reihenfolge.
