# Team Learning: Wie wir den Niche-Classifier gebaut haben

> Quelle: direkt aus dem Code (`analysis_2026-06-01/cluster_embeddings.py`, `niche_classifier.py`) und den
> Eval-Zahlen (`data/niche_classifier_eval.json`). Nichts aus der Erinnerung. Stellen, die Interpretation
> statt 1:1-Code sind, sind als solche markiert.

---

## Das Problem

Wir teilen Funnels in **Niches** ein (Job + Zielgruppe, *nicht* Industrie). Diese Einteilung entstand
über ein einmaliges Clustering. Aber: ein **neuer** Funnel braucht seine Niche, *ohne* dass wir die ganze
Cluster-Pipeline neu laufen lassen. Der Classifier ist genau dieser „On-the-fly"-Schritt — plus eine
**Confidence**, damit das UI bei Unsicherheit nachfragen kann („Ist das deine Niche?").

---

## Der Aufbau in 4 Schritten

### 1. Woher die Labels kommen (der wichtige Trick)

Die Niches sind **kein** externer Ground-Truth. Sie sind ein 1:1-Relabel von **35 Content-Embedding-Clustern**:

- Funnel-Text (Name 2× gewichtet + erste 400 Zeichen Content) → multilinguales Sentence-Embedding
  (`paraphrase-multilingual-MiniLM-L12-v2`). Clustert nach **Bedeutung**, sprachübergreifend.
- KMeans (k=35) → Cluster. Pro Cluster: nächste Beispiele am Centroid + Top-TF-IDF-Begriffe → ein
  **Mensch** hat die Cluster zu Niches gelabelt.

### 2. Der Classifier selbst — bewusst simpel

- Input: dasselbe Embedding → **PCA auf 120 Dimensionen** (unsupervised, daher quasi kein CV-Leakage)
  → **Logistic Regression**.
- Kein Deep Learning, kein Tuning-Zirkus. Das Embedding macht die schwere Arbeit; ein linearer
  Klassifikator reicht, um die Cluster-Grenzen zu rekonstruieren.

### 3. Die richtige Validierung (das eigentliche Learning)

- **`GroupKFold` nach `campaignId`** = Account-Holdout. Ein Account ist entweder komplett im Training
  oder komplett im Test, nie beides.
- Warum kritisch: Ein Account hat oft viele ähnliche Funnels. Bei normalem Random-Split „lernt" das Modell
  den Account auswendig und die Accuracy ist geschönt. Account-Holdout misst, ob ein **echt neuer** Kunde
  sauber zugeordnet wird.

### 4. Ergebnis + die Produkt-Entscheidung

- **Top-1: 91,7 % | Top-3: 99,8 %** (196.365 Funnels / 87.110 Accounts / 32 Niches).
- **Confidence Gating** ist der Produkt-Hebel, nicht nur eine Metrik:
  - `conf ≥ 0,7` → **71 %** der Funnels automatisch zugeordnet @ **98,4 %** Genauigkeit.
  - darunter → Top-3 anzeigen und User fragen.
  - Im `.pkl` als `recommend_confirm_below=0.7` gespeichert.
- Schwächste Niches (Grenzfälle): Coaching/Webinar 84 %, Food/E-Com, IT/PM, Generic/Untitled, Real Estate.
- Stärkste: Dental 97,5 %, Solar, LKW-Fahrer.

---

## Die ehrliche Einschränkung (bitte immer mitkommunizieren)

„Accuracy" = **Übereinstimmung mit dem selbst definierten Cluster-Label**, also Schärfe der Grenzen +
Generalisierung — **nicht** externe Wahrheit. Was es ehrlich misst: wie sicher ein neuer Funnel auf *eine*
Niche „einrastet" und wie oft er auf einer Grenze sitzt (→ dann fragen wir).

---

## Übertragbare Learnings fürs Team

1. **Embedding + linearer Klassifikator schlägt komplex.** Ist das Embedding gut, braucht der Classifier
   kein Deep Learning.
2. **Split nach der Entität, die in Produktion neu ist** (hier Account), nicht random. Sonst lügt die Metrik.
3. **Confidence ist ein Feature, kein Nebenprodukt.** „Weiß nicht → frag den User" schlägt oft den
   selbstsicheren Fehler.
4. **Self-defined Labels ehrlich framen.** Cluster-Agreement ≠ Ground-Truth.
5. **Alles lokal, €0, reproduzierbar.** PCA unsupervised halten → kein Leakage.

---

## FAQ / Design-Entscheidungen

### Warum den Namen 2× gewichten und nur die ersten 400 Zeichen nehmen?

Code: `df["doc"] = (df["funnel_name"] + ". ") * 2 + df["content_text"].str.slice(0, 400)`

- **Name 2×:** Der Funnel-Name trägt das stärkste Niche-Signal („Zahnarzt-Termine", „Solar-Anfrage").
  Da im Embedding über den ganzen Text gemittelt wird, zieht doppelter Name den Vektor stärker zum klaren
  Signal. Code-Kommentar: *"name carries strong vertical signal"*.
- **Nur 400 Zeichen, nicht alles:**
  - **Signal-zu-Rausch:** Die ersten ~400 Zeichen sind Headline + Einstieg = „worum geht's". Danach kommt
    Boilerplate (Cookie-Text, „Weiter"-Buttons, rechtliche Hinweise) → hätte das Thema verwässert.
  - **Modell-Limit:** `MiniLM-L12-v2` hat ein Token-Fenster von ~128 Tokens. Alles darüber wird *sowieso
    abgeschnitten* — „alles reingeben" hätte das Modell intern gar nicht verarbeitet.
  - **Speed:** Kommentar im Code: *"cap content so seqs stay short & fast"*. Bei ~196k Funnels relevant.

> Kurz: „alles" hätte nichts gebracht (Modell schneidet ab) und sogar geschadet (Boilerplate-Rauschen).

### Was heißt „multilinguales (Sentence-)Embedding"?

Modell: `paraphrase-multilingual-MiniLM-L12-v2` (ein *Sentence-Transformer*).

- **Embedding** = Text → Zahlen-Vektor (hier 384 Dimensionen). Texte mit *ähnlicher Bedeutung* landen nah
  beieinander — nicht wegen gleicher Wörter, sondern gleichem Sinn.
- **Multilingual** = dieselbe Bedeutung landet *über Sprachen hinweg* am selben Ort. Deutsch „Zahnarzt" und
  Englisch „dentist" liegen dicht beieinander.
- Code: `normalize_embeddings=True` → Vektoren auf Länge 1, dann ist Ähnlichkeit = Skalarprodukt (Cosinus).

> Effekt: Ein deutscher und ein englischer Dental-Funnel clustern zusammen, weil das Embedding *Bedeutung*
> erfasst, nicht Wörter.

### Was ist „das TF-IDF-Problem"?

TF-IDF = „Bag of Words": zählt Wort-Häufigkeit, gewichtet mit Seltenheit. Kennt nur **exakte Wörter**,
keine Bedeutung. Zwei Probleme (Code-Kommentar: *"fixes TF-IDF's language/boilerplate fragmentation"*):

1. **Sprach-Fragmentierung:** DE- und EN-Dental-Funnel teilen fast keine Tokens → TF-IDF steckt sie in
   getrennte Cluster, obwohl gleiche Niche. Bei DE/EN/NL-Funnels ein echtes Problem.
2. **Boilerplate-Fragmentierung:** „Weiter", „Datenschutz", Cookie-Banner bekommen hohes Gewicht → Cluster
   nach Template statt Thema.

Embeddings lösen beides (Gruppierung nach Sinn).

> Nuance: Wir haben TF-IDF nicht rausgeworfen. Wir nutzen es nur noch, um die fertigen Cluster zu
> **beschreiben** (Top-Begriffe fürs menschliche Labeln) — *nicht* um sie zu bilden.

### K-Means: warum 35?

Ehrliche Antwort: Im Code ist 35 schlicht der **Default** (`K = int(sys.argv[1]) if len(sys.argv) > 1 else 35`).
Es gibt **kein** Elbow-/Silhouette-Verfahren, das 35 „bewiesen" hätte. Einordnung (Interpretation):

- **35 ist eine pragmatische, menschlich labelbare Granularität.** Bei 35 Clustern kann ein Mensch Top-Begriffe
  + Beispiele durchgehen und zuordnen. Die 35 Cluster wurden danach auf **32 Niches** gemappt (einige
  zusammengelegt).
- **Wir wissen: 35 ist fürs Scoring zu grob.** In `progress.md`: niche→CVR out-of-sample ρ *verdoppelt* sich
  von 34→1000 Niches, **ohne Plateau**. Feinere Buckets wären für die Vorhersage besser. 35 war ein Kompromiss
  zwischen „labelbar" und „vorhersagestark", nicht das Optimum.
- Deshalb die Empfehlung, langfristig auf **kontinuierliches k-NN** statt feste Buckets zu gehen (siehe unten).

> Zusammengefasst: 35 = bewusst gewählte, handhabbare Auflösung — kein optimierter Wert.

---

## Nächster Schritt: k-NN („Funnels wie deiner") statt fester Buckets

Statt einen Funnel in **eine von 32 festen Schubladen** zu stecken, baut k-NN für jeden Funnel eine
**dynamische Peer-Gruppe** aus den ähnlichsten echten Funnels.

### So läuft es ab

1. **Embedden** — neuer Funnel → derselbe MiniLM-Vektor wie bisher.
2. **Nachbarn finden** — die k ähnlichsten Funnels im Embedding-Raum (Cosinus = Skalarprodukt, weil
   normalisiert). Der Index ist unser vorhandenes `embeddings.npy` (196k Funnels).
3. **Daraus ableiten:**
   - **Benchmark/Score** = CVR-Verteilung *dieser* Nachbarn → Perzentil des Funnels „unter seinesgleichen".
   - **Recommendations** = was die *gut konvertierenden* Nachbarn anders machen → „Funnels wie deiner, die
     gut konvertieren, machen X" (das Framing nutzt `recommend.py` schon).
   - **Confidence** = wie dicht/einig die Nachbarschaft ist (enge, konsistente Nachbarn = sicher; weit
     gestreut über viele Niches = unsicher → User fragen).

### Warum besser als feste Buckets

- **Keine harten Grenzen** — ein Funnel zwischen Dental und Medical bekommt eine *gemischte* Peer-Gruppe
  statt einer erzwungenen Schublade.
- **Auflösung skaliert mit Daten** — genau das, was `progress.md` zeigt (ρ verdoppelt sich 34→1000, kein
  Plateau). k-NN ist quasi „unendlich viele Niches".
- **Selbst-aktualisierend** — neuer Funnel wird in den Index gelegt, kein Re-Clustering, kein Re-Labeling.
- Liefert das „Funnels wie deiner"-UX geschenkt.

### Stolperfallen

- **Account-Leakage:** eigenen Account (`campaignId`) aus den Nachbarn ausschließen — sonst benchmarkt sich
  der Funnel gegen seine eigenen Geschwister. Dieselbe Logik wie GroupKFold.
- **Skalierung:** Brute-Force (ein Query gegen 196k) ist <10 ms. Bei Millionen → FAISS / pgvector /
  Approximate-NN.
- **k & Gewichtung:** z. B. k≈200–500, gewichtet nach Ähnlichkeit × log(Traffic); Low-Traffic-Nachbarn
  rausfiltern (verrauschte CVR).
- **Cold Start:** ganz neue Nische ohne echte Nachbarn → niedrige Confidence, Fallback auf den groben
  32-Niche-Classifier.

### Empfehlung: Hybrid

Grobe 32-Niche-Klassifikation als **erklärbares Label + Causal-Layer** behalten, k-NN als **feine
Peer-Gruppe** fürs Scoring + die Empfehlungen. (Steht so auch in `progress.md`: „coarse pooling only for the
causal layer", „fine/continuous k-NN for the score".)

### Skizze

```python
EMB  = np.load("data/embeddings.npy")        # (196k, 384), normalisiert
META = pd.read_csv("data/funnel_meta.csv")   # campaignId, niche, cvr, visitors

def peers(q_emb, q_account, k=300, min_visitors=300):
    sims = EMB @ q_emb                         # Cosinus (normalisiert)
    ok = (META.campaignId.values != q_account) & (META.visitors.values >= min_visitors)
    idx = np.argsort(-np.where(ok, sims, -1))[:k]   # eigener Account raus
    return idx, sims[idx]

# → Score = Perzentil der Peer-CVRs
# → Recs  = Kontrast Top-Quartil-Peers vs Rest auf den Funnel-Features
# → Conf  = mean(sim der Top-Nachbarn) + Einigkeit der Niche-Labels in der Nachbarschaft
```

---

## Nutzung (Handoff)

```python
# .pkl laden:
niche = classes[clf.predict_proba(pca.transform(embedding))[0].argmax()]
# wenn max(proba) < 0.7  ->  Top-3 zeigen + User fragen ("Ist das deine Niche?")
```

Modell-Artefakte: `data/niche_classifier.pkl` (clf + pca + classes + `recommend_confirm_below=0.7`),
Eval: `data/niche_classifier_eval.json`.

---

## Bonus-Learning: Wie man einen Recommender ehrlich prüft (Content-Proposal-Validity)

Gleiche Disziplin wie beim Classifier, anderes Problem. Frage: **Bewegt eine Copy-Änderung in die
empfohlene Richtung die Conversion wirklich — oder korreliert „guter Funnel" nur mit „guter Copy"?**
(`content_proposal_backtest.py`, `content_ablation.py`, `content_ranker.py`.)

### Aufbau
- **Gold-Standard = echte A/B-Tests**, nicht Korrelation. 9.737 historisch verlinkte Control-vs-Variant-Paare
  (`causal_linked.csv`), Baseline „Challenger gewinnt" = 26,1 %.
- **page→text-Join:** A/B-Arme sind `pageId`s, Content war nach `campaignVersionId` gekeyt. Gelöst über
  `content.plainText` pro Seite aus BQ (das Feld `text` ist nur Template-Platzhalter — genau das Rauschen).
- Arme embedden (gleiches MiniLM, content-only). „Gewinner-Content-Richtung" = **leave-account-out**
  Gewinner-Centroid pro Niche (dieselbe Anti-Leakage-Logik wie GroupKFold beim Classifier).

### Ergebnis (drei genestete Tests)
1. **„Sei wie der Niche-Durchschnitt" → funktioniert NICHT.** toward 24,1 % (−2,0pp), Dose-Response flach
   (Monotonie −0,06). Eindimensionale „mach's wie die Gewinner"-Empfehlung ist ein Goodhart-Trap — nie blind ausliefern.
2. **Aber der mehrdimensionale Content-Change ist lernbar:** Change-Model OOS-AUC **0,571**, Top-10 %
   +8,3pp — **besser als Struktur (0,52 ≈ nichts)**. Es gibt einen pre-trainbaren Content-Prior.
3. **Ablation: das Signal ist die RICHTUNG, nicht die Menge.** Nur-Änderungsmenge 0,527 ≈ Zufall;
   magnitude-entfernte Richtung hält 0,564 (Top-10 % 44,4 %). Also: *wie* du die Copy änderst zählt, nicht *wie viel*.

### Übertragbare Learnings
1. **Korrelation ≠ kausale Empfehlung.** Ein descriptiver Score („gute Funnels sehen so aus") ist kein
   Rezept. Erst der A/B-Backtest sagt, ob die Empfehlung wirkt.
2. **Dose-Response ist der Lackmustest.** Flach = korrelativ. Monoton = kausal-artig. Ein einzelner
   win-rate-Vergleich täuscht leicht.
3. **Richtung vs. Menge trennen (Ablation).** Sonst hält man „wer viel ändert, gewinnt" für echtes Signal.
4. **Recommender = Prioritisierer, nicht Orakel.** AUC 0,571 reicht, um Copy-Experimente zu **ranken**
   (`content_ranker.py` → Win-Prob pro Vorschlag, in `recommend.py` per `CONTENT_RANKER=1`), aber jeder
   Vorschlag bleibt „A/B-test it". Der **Live-Flywheel** macht aus Quoten belastbare Kausalität.
