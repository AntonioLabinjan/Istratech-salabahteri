Dobrodošao na **Optuna Express Crash Course**! Ako ti je dosta ručnog isprobavanja parametara ili onog blesavog, sporog Grid Searcha koji troši struju i vrijeme, na pravom si mjestu.

Optuna je trenutno zlatni standard za optimizaciju hiperparametara (HPO) u Pythonu. Brza je, nevjerojatno fleksibilna i donosi napredne matematičke algoritme upakirane u izuzetno jednostavan API.

Proći ćemo kroz sve što ti treba da postaneš Optuna majstor: od tipova parametara, preko pametnih "samplera", pa sve do rezanja loših pokušaja u korijenu (pruning).

---

## 1. Što se sve može optimizirati? (Tipovi hiperparametara)

Optuna koristi takozvani **"Define-by-Run"** pristup. To znači da prostor pretraživanja ne definiraš unaprijed kao statični rječnik, već ga definiraš dinamički unutar same funkcije dok se kod izvršava. To ti omogućuje korištenje običnih Python `if-else` uvjeta i petlji!

Unutar svoje `objective(trial)` funkcije, od objekta `trial` tražiš (sugeriraš) parametre koristeći tri glavne metode:

### A. Kontinuirane i decimalne vrijednosti (`suggest_float`)

Odlično za stope učenja, koeficijente regularizacije i slično.

* **Standardni raspon:** `trial.suggest_float("lr", 1e-5, 1e-2)`
* **Logaritamska skala** (kada pretražuješ po redovima veličine): `trial.suggest_float("lr", 1e-5, 1e-2, log=True)`
* **Korak (diskretizacija):** `trial.suggest_float("dropout", 0.1, 0.5, step=0.1)`

### B. Cijeli brojevi (`suggest_int`)

Za broj stabala u šumi, broj slojeva u mreži, veličinu batcha itd.

* **Standardni raspon:** `trial.suggest_int("max_depth", 2, 32)`
* **Logaritamska skala:** `trial.suggest_int("batch_size", 16, 512, log=True)`
* **Korak:** `trial.suggest_int("num_filters", 32, 256, step=32)`

### C. Kategoričke vrijednosti (`suggest_categorical`)

Za odabir stringova, objekata ili čak cijelih arhitektura.

* **Primjer:** `trial.suggest_categorical("optimizer", ["Adam", "SGD", "RMSprop"])`

> 💡 **Uvjetni (Conditional) parametri:** Zahvaljujući "Define-by-Run" pristupu, možeš napisati:
> ```python
> classifier = trial.suggest_categorical("classifier", ["SVM", "RF"])
> if classifier == "SVM":
>     c = trial.suggest_float("svm_c", 1e-5, 1e2, log=True)
> else:
>     depth = trial.suggest_int("rf_depth", 2, 32)
> 
> ```
> 
> 
> Ako Optuna odabere "RF", uopće neće trošiti resurse na predlaganje parametra `svm_c` za taj krug (trial).

---

## 2. Kako Optuna bira parametre? (Sampleri)

Sampler je mozak Optune. On odlučuje koje će vrijednosti predložiti u idućem krugu na temelju onoga što je naučio iz prethodnih pokušaja. Prilikom kreiranja studije (`optuna.create_study(sampler=...)`), možeš birati između nekoliko moćnih algoritama:

| Sampler | Naziv u kodu | Kada ga koristiti? | Kako radi? |
| --- | --- | --- | --- |
| **TPE (Default)** | `TPESampler` | Zlatna sredina za većinu ML problema. Odličan s miješanim tipovima (float, int, kategorije). | **Tree-structured Parzen Estimator**: Bayesov algoritam koji modelira "dobre" i "loše" parametre te bira one koji imaju najveću vjerojatnost da budu u "dobroj" skupini. |
| **CMA-ES** | `CmaEsSampler` | Za teške, kontinuirane i numeričke prostore pretraživanja (bez puno kategorija). | Evolucijski algoritam prilagodbe kovarijacijske matrice. Izvrsno pronalazi lokalne i globalne minimume u teškim matematičkim prostorima. |
| **Gaussian Process** | `GPSampler` | Kada je evaluacija modela izuzetno skupa (npr. treniranje traje danima), pa želiš maksimalno pametne odluke u malo koraka. | Klasična Bayesova optimizacija bazirana na Gaussovim procesima. |
| **Grid Search** | `GridSampler` | Kada želiš apsolutno deterministički isprobati *svaku* kombinaciju (npr. na malom, fiksnom prostoru). | Klasični "brute-force" prolazak kroz unaprijed definiranu mrežu parametara. |
| **Random Search** | `RandomSampler` | Kao baseline (početna točka za usporedbu) ili kada imaš ogroman paralelni sustav pa želiš čistu nasumičnost. | Potpuno nasumičan odabir bez učenja iz prošlosti. |
| **Multi-Objective** | `NSGAIISampler` | Kada optimiziraš više stvari odjednom (npr. želiš visoku točnost modela, ali i što manju latenciju/brzinu predikcije). | Genetski algoritam (Non-dominated Sorting Genetic Algorithm II) za pronalaženje tzv. Pareto fronta. |

---

## 3. Rezanje loših pokušaja u korijenu (Pruneri)

Zamisli da treniraš neuronsku mrežu kroz 100 epoha. Već u 5. epohi vidiš da je točnost očajna (npr. 10%), dok su prošli uspješni modeli u 5. epohi već imali 80%. **Zašto trošiti struju i vrijeme na preostalih 95 epoha?**

Tu uskaču **Pruneri (rezači)**. Oni prate međurezultate i automatski gase (prunaju) neperspektivne pokuse.

Da bi pruner radio, unutar petlje treniranja moraš javiti Optuni trenutni rezultat pomoću `trial.report(current_value, step=epoch)` i provjeriti treba li prekinuti pokus s `trial.should_prune()`.

### Glavni pruneri u ponudi:

* **`MedianPruner` (Najpopularniji/Default):**
* *Kako radi:* Gasi trenutni pokus ako je njegov rezultat u nekom koraku (npr. epohi) lošiji od medijana (srednje vrijednosti) svih dosadašnjih pokusa u tom istom koraku.
* *Zašto je dobar:* Jednostavan, robustan i matematički vrlo učinkovit.


* **`HyperbandPruner`:**
* *Kako radi:* Koristi napredni *Hyperband* algoritam koji kombinira nasumično uzorkovanje s ranim odbacivanjem resursa (kroz runde "turnira").
* *Zašto je dobar:* Teoretski vrlo jak za duboko učenje (Deep Learning) jer agresivno i pametno raspoređuje resurse.


* **`PercentilePruner`:**
* *Kako radi:* Stroža verzija MedianPrunera. Možeš reći: "Ugasi sve pokuse koji nisu u top 25% najboljih u ovom koraku."


* **`PatientPruner`:**
* *Kako radi:* Omotnica (wrapper) oko drugih prunera. Daje pokusu "vrijeme strpljenja" (eng. *patience*), odnosno dopušta mu nekoliko koraka lošeg rezultata prije nego što ga pruner definitivno ugasi, kako bi se izbjeglo prerano gašenje modela koji sporo uče na početku.


* **`ThresholdPruner`:**
* *Kako radi:* Gasi pokus ako rezultat padne ispod (ili iznad) fiksne, granične vrijednosti koju sam definiraš.



---

## 4. Brzi Kodni Primjer: Sve na jednom mjestu

Evo kako sve ovo izgleda u praksi na jednom jednostavnom primjeru (simulirano treniranje s prunanjem):

```python
import optuna
import time

# 1. Definiramo objective funkciju
def objective(trial):
    # Sugeriramo razne tipove parametara
    classifier = trial.suggest_categorical("classifier", ["RandomForest", "LightGBM"])
    lr = trial.suggest_float("lr", 1e-5, 1e-1, log=True)
    num_layers = trial.suggest_int("num_layers", 1, 5)
    
    # Simuliramo treniranje kroz 10 epoha
    for epoch in range(10):
        # Simulirani izračun gubitka (loss) - želimo ga minimizirati
        # Što je manji lr, to sporije pada loss, a ovisi i o broju slojeva
        dummy_loss = (10 - epoch) * lr * (6 - num_layers) 
        
        # Javljamo Optuni trenutno stanje
        trial.report(dummy_loss, step=epoch)
        
        # Provjeravamo treba li pruner ugasiti ovaj trial
        if trial.should_prune():
            raise optuna.TrialPruned() # Ovo javlja Optuni da je trial uspješno prekinut
            
        time.sleep(0.01) # Kratka pauza za simulaciju rada
        
    return dummy_loss # Vraćamo konačni rezultat na kraju treninga

# 2. Kreiramo studiju s odabranim Samplerom i Prunerom
study = optuna.create_study(
    direction="minimize",                      # Želimo minimizirati loss
    sampler=optuna.samplers.TPESampler(),       # Koristimo Bayesov TPE
    pruner=optuna.pruners.MedianPruner()        # Palimo Median Pruner za rano gašenje
)

# 3. Pokrećemo optimizaciju
study.optimize(objective, n_trials=50)

# 4. Ispisujemo pobjednika!
print(f"Najbolji parametri: {study.best_params}")
print(f"Najbolji rezultat: {study.best_value}")

```

---
