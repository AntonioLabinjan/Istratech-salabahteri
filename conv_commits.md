# Conventional Commits 1.0.0 — Šalabahter

> Izvor: [conventionalcommits.org](https://www.conventionalcommits.org/en/v1.0.0) · CC BY 3.0

---

## Format poruke

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

---

## Tipovi (type)

| Type | SemVer | Opis |
|------|--------|------|
| `fix` | PATCH | Ispravak greške |
| `feat` | MINOR | Nova funkcionalnost |
| `BREAKING CHANGE` (footer) ili `!` | MAJOR | Nekompatibilna promjena API-ja |
| `build` | — | Sustav za izgradnju, vanjske ovisnosti |
| `chore` | — | Održavanje, ne mijenja src/test |
| `ci` | — | CI konfiguracija i skripte |
| `docs` | — | Samo dokumentacija |
| `style` | — | Formatiranje, razmaci (ne logika) |
| `refactor` | — | Ni fix ni feat — prestrukturiranje |
| `perf` | — | Poboljšanje performansi |
| `test` | — | Dodavanje ili ispravljanje testova |
| `revert` | — | Vraćanje prethodnog commita |

> `feat` i `fix` su jedini mandatorni tipovi po specifikaciji. Ostali su konvencija (Angular / commitlint).

---

## Primjeri

```bash
# Minimalno
fix: ispravi parsiranje arraya s višestrukim razmacima

# Sa scope-om
feat(lang): dodaj polski jezik

# Breaking change s !
feat(api)!: ukloni podršku za Node 6

# Breaking change u footeru
feat: omogući extend konfiguracije

BREAKING CHANGE: ključ `extends` sada služi za nasljeđivanje config datoteka

# I ! i footer
feat!: ukloni podršku za Node 6

BREAKING CHANGE: koriste se JS značajke nedostupne u Node 6.

# S tijelom i footerima
fix: spriječi race condition zahtjeva

Uvodi request id i referencu na zadnji zahtjev.
Uklanjaju se timeoutovi koji su bili privremeno rješenje.

Reviewed-by: Z
Refs: #123

# Revert
revert: nikad više ne spominjemo incident s rezancima

Refs: 676104e, a215868
```

---

## Pravila specifikacije

| # | Pravilo |
|---|---------|
| 1 | Commit MORA imati prefix `type`, kojeg slijede opcionalni scope, opcionalni `!`, te `: ` |
| 2 | `feat` MORA se koristiti za novu funkcionalnost |
| 3 | `fix` MORA se koristiti za ispravak greške |
| 4 | Scope je opcionalan — imenica u zagradama, npr. `fix(parser):` |
| 5 | Opis MORA neposredno slijediti iza `type/scope: ` |
| 6 | Tijelo (body) je opcionalno — počinje jednim praznim redom iza opisa |
| 7 | Tijelo je slobodnog formata, može imati više paragrafa |
| 8 | Footer(i) su opcionalni — jedan prazan red iza tijela; format: `token: vrijednost` ili `token #vrijednost` |
| 9 | Footer token koristi `-` umjesto razmaka (npr. `Reviewed-by`); iznimka: `BREAKING CHANGE` |
| 11 | Breaking change MORA biti označen s `!` ili kao footer entry |
| 12 | Footer breaking change: `BREAKING CHANGE: <opis>` (velika slova, obavezno) |
| 13 | Ako se koristi `!`, `BREAKING CHANGE:` footer je opcionalan |
| 15 | Type/scope nisu case-sensitive; `BREAKING CHANGE` MORA biti velika slova |
| 16 | `BREAKING-CHANGE` je sinonim za `BREAKING CHANGE` u footeru |

---

## Veza sa SemVer

| Conventional Commit | SemVer bump |
|--------------------|-------------|
| `fix:` | PATCH |
| `feat:` | MINOR |
| `BREAKING CHANGE` / `!` | MAJOR |
| `docs:`, `chore:`, `ci:`, itd. | *(bez bumpa)* |

---

## Česta pitanja

**Tip u velikom ili malom slovu?**  
Oba su OK — važna je dosljednost.

**Commit odgovara više tipovima?**  
Podijeli u više commitova — to je i poanta specifikacije.

**Krivi tip u commitu?**  
Prije merge-a: `git rebase -i`. Nakon release-a — ovisno o alatima.

**Moraju li svi suradnici koristiti specifikaciju?**  
Ne. Squash workflow + maintainer koji piše ispravnu poruku pri merge-u je validan pristup.

**Kako označiti revert?**  
Preporučeno: tip `revert` + footer s `Refs:` koji sadrži SHA commita koji se vraća.
