# Pipeline — wie das Modell end-to-end läuft

So entsteht aus einer Funnel-ID ein Score plus gerankte Verbesserungs-Experimente. Wichtig ist die
**Arbeitsteilung**: ML scort und klassifiziert, Statistik findet die Hebel, ein A/B-Gate sichert sie ab,
das LLM textet — in genau dieser Reihenfolge. Das LLM ist der Sprachgenerator am Ende, nicht der Richter am Anfang.

```
Funnel-ID
  → Struktur + Copy aus DB
  → [ML]        Niche-Classifier      Copy-Embedding → Niche + Confidence
  → [ML]        M2-Score              Struktur + Content-Embedding + Niche → Within-Niche-Perzentil   (validiert, KEIN LLM)
  → [Statistik] Per-Niche-Driver      was Gewinner anders machen, global + niche, vorzeichenbewusst
  → [A/B-Layer] Kausal-Gate           sicher / „test, don't apply" / schädlich
  → [LLM]       Copy-Generator        funnel-spezifische Rewrites, an echtes Angebot gebunden            (EINZIGE LLM-Rolle)
  → [ML]        Ranker                Vorschläge nach Win-Probability sortieren
  → Output: Score + gerankte Design- & Copy-Experimente ("A/B-test it")
```

## Schritt für Schritt

| Schritt | Engine | Was passiert | Skript |
|---|---|---|---|
| **Input** | — | Funnel-ID rein, System zieht Struktur + Copy aus der DB. Kein Upload. | `analyze.py`, `server.py` |
| **Niche-Klassifikation** | ML | Classifier liest die Copy → Niche + Confidence; bei Unsicherheit „ist das deine Niche?". | `niche_classifier.py` |
| **Score** | ML (M2) | Auf 196k echten Funnels gegen echte Conversion trainiertes Modell → Perzentil *innerhalb der Niche*. | `funnel_score.py`, `score_m2.py` |
| **Hebel finden** | Statistik | Spearman-Korrelation pro Niche: welche Merkmale hängen mit hoher CVR zusammen (univariat). 3 Schubladen: universal / niche-spezifisch / Vorsicht. | `per_niche_drivers.py` |
| **Absichern** | A/B-Gate | Einmalige, *rückblickende* Kalibrierung gegen ~9.900 historische A/B-Tests → entscheidet, wie sehr man jeder Art Tipp traut. | `proposal_backtest.py`, `content_proposal_backtest.py` |
| **Copy texten** | LLM | Funnel-spezifische Rewrites (Opener, Fragen), streng ans echte Angebot gebunden, keine erfundenen Claims. | `generate_suggestions.py` |
| **Ranking** | ML | Sortiert die Vorschläge nach gelernter Gewinnwahrscheinlichkeit (Content-Change-Model). | `content_ranker.py` |
| **Output** | — | Score + nach Win-Prob gerankte Design- & Copy-Experimente, alle als „A/B-test it". | `recommend.py` |

## Warum der Score kein LLM ist (der Moat)

Ein LLM „bewerte diesen Funnel" halluziniert eine Zahl ohne Bezug zu echten Conversion-Daten. Unser Score kommt
aus **M2**, geeicht an der tatsächlichen Conversion von 196k Funnels (OOS ρ = 0,40 Account-Holdout / 0,48 temporal).
Das ist der Unterschied zwischen „die KI findet den Funnel gut" und „Funnels mit diesen Eigenschaften konvertieren
in dieser Nische messbar besser". Würde ein LLM scoren, verschenkt man genau diesen Vorsprung.

## Die zwei Schritte, die den Recommender ausmachen

### „Hebel finden" — Korrelation, kein ML-Modell
Pro Nische wird per **Spearman-Rangkorrelation** (univariat, jedes Merkmal einzeln) gemessen, was die gut
konvertierenden Funnels gemeinsam haben. Weil viele Merkmale je Nische in unterschiedliche Richtungen zeigen
(16/23 kippen das Vorzeichen), wird pro Nische gerechnet, nicht global. Univariat heißt: ohne Kontrolle für andere
Merkmale — bewusst simpel als Startpunkt, deshalb folgt „Absichern".

### „Absichern" — was es ist und was nicht
**Es ist NICHT** ein Live-Test des Kunden-Funnels. Wir spielen *seine* Recos nicht als A/B-Test aus und filtern
hinterher.

**Es IST** ein einmaliger, rückblickender Lern-Schritt: aus ~9.900 *vergangenen* A/B-Tests vieler Funnels haben wir
auf **Kategorie-Ebene** gelernt, wie verlässlich jede Art von Änderung kausal wirkt. Ergebnis ist fest eingebaut und
entscheidet nur die **Darstellung**:
- strukturelle Änderungen tragen kaum kausales Signal (AUC 0,52) → laufen alle als **Experimente**, nicht als Befehle;
- das Formular ist kausal rückwärts → **„test, don't apply"**;
- Content wird vom gelernten Change-Model gerankt (AUC 0,571).

**Analogie:** Ein Arzt hat 9.900 frühere Patienten studiert und weiß generell, was meist hilft und was nach hinten
losgeht. Mit dem Wissen berät er dich — aber er hat noch keine Studie *an dir* gemacht.

## Der Live-Flywheel (noch nicht gebaut — der eigentliche Moat)

Die Studie *an dir* laufen lassen = der Flywheel: das System spielt eine Empfehlung selbst als A/B-Test aus
(Variante bauen → Traffic splitten → Gewinner messen → Ergebnis zurückfüttern). Damit wird aus „Hypothese" über
Zeit bewiesenes, nischenspezifisches Wissen — und das Modell wird mit jedem Test schlauer. Deshalb steht heute auf
jeder Empfehlung „A/B-test it": es sind gut begründete Test-Vorschläge, keine Garantien.

## Produkt-Oberflächen (heute)

- **Live-Analyzer** (`server.py` + `analyze.html`): Campaign-ID aus ~56,5k → voller Score + Recs. Auch Text-Modus
  (Copy reinpasten → Niche + Playbook, kein /100-Score ohne Struktur).
- **Static Demo** (`demo.html`): self-contained, 27 Funnels, offline öffnbar, „send-anyone".
