# SemVer 2.0.0 — Šalabahter

> **Format:** `MAJOR.MINOR.PATCH[-pre-release][+build]`  
> Izvor: [semver.org](https://semver.org) · autor: Tom Preston-Werner · CC BY 3.0

---

## Što bumpaš i kada?

| Segment | Kada | Reset |
|---------|------|-------|
| **MAJOR** `X.0.0` | Nekompatibilna promjena API-ja | MINOR i PATCH → 0 |
| **MINOR** `x.Y.0` | Nova kompatibilna funkcionalnost ili deprecation | PATCH → 0 |
| **PATCH** `x.y.Z` | Ispravak greške, ne mijenja API | — |

---

## Posebne oznake

### Pre-release (crtica)
```
1.0.0-alpha
1.0.0-alpha.1
1.0.0-0.3.7
1.0.0-rc.1
```
- Označava nestabilnu verziju
- Manji prioritet od normalne verzije (`1.0.0-alpha < 1.0.0`)
- Dozvoljeni znakovi: `[0-9A-Za-z-]`, bez vodećih nula u brojevima

### Build metadata (plus)
```
1.0.0+20130313144700
1.0.0-beta+exp.sha.5114f85
```
- **Ignorira se** pri usporedbi verzija
- Dvije verzije koje se razlikuju samo u build metadati imaju isti prioritet

---

## Redoslijed prioriteta (Precedence)

```
1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-alpha.beta
  < 1.0.0-beta < 1.0.0-beta.2 < 1.0.0-beta.11
  < 1.0.0-rc.1 < 1.0.0
```

```
1.0.0 < 2.0.0 < 2.1.0 < 2.1.1
```

**Pravila usporedbe pre-release:**
1. Samo brojevi → numerička usporedba (`1 < 2 < 11`)
2. Slova/crtice → leksikografski ASCII redoslijed
3. Broj < alfanumerički identifikator (`alpha.1 < alpha.beta`)
4. Više polja = veći prioritet ako su prethodna jednaka (`alpha < alpha.1`)

---

## Ključna pravila

| Pravilo | Opis |
|---------|------|
| **Javni API** | Mora biti deklariran (kod ili dokumentacija) — precizno i sveobuhvatno |
| **Format** | `X.Y.Z` — nenegativni cijeli brojevi, bez vodećih nula |
| **Nepromjenljivost** | Objavljena verzija se **ne smije mijenjati**. Svaka izmjena = nova verzija |
| **0.y.z** | Rana faza razvoja — sve se smije mijenjati, API nije stabilan |
| **1.0.0** | Definira prvi stabilan javni API |
| **Deprecation** | Objavi MINOR s oznakom deprecationa, zatim ukloni u sljedećoj MAJOR |
| **"v1.2.3"** | Nije SemVer — `v` je konvencija (git tag), semantička verzija je `1.2.3` |

---

## Česta pitanja

**Kad objaviti 1.0.0?**  
Kad je softver u produkciji, kad korisnici ovise o API-ju, ili kad brineš o kompatibilnosti unatrag.

**Što s internim bugfixom dependencije?**  
Ne mijenja javni API → **PATCH**. Donosi novu funkcionalnost → **MINOR**.

**Što ako greškom objavljujem breaking change kao MINOR?**  
Objavi novu MINOR koja ispravlja grešku i vraća kompatibilnost. Modificiranje već objavljene verzije nije dopušteno.

**Limit duljine verzijskog stringa?**  
Nema, ali koristi zdrav razum. 255 znakova je pretjerano.

---

## Regex za validaciju

**JavaScript / ECMA (numbered groups):**
```regex
^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$
```
`cg1` = major · `cg2` = minor · `cg3` = patch · `cg4` = prerelease · `cg5` = buildmetadata

**Python / Go / PCRE (named groups):**
```regex
^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$
```

---

## BNF gramatika (sažetak)

```
<semver>       ::= <core> | <core>"-"<pre> | <core>"+"<build> | <core>"-"<pre>"+"<build>
<core>         ::= <major>"."<minor>"."<patch>
<pre>          ::= <dot-id> ("." <dot-id>)*
<build>        ::= <dot-id> ("." <dot-id>)*
<dot-id>       ::= alfanumerički identifikator ili broj bez vodećih nula
```
