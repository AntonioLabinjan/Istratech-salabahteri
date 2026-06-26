# Structured Output šalabahter

## Instalacija

```bash
pip install openai pydantic python-dotenv
```

## Osnova — definiraš shemu, model je popuni

```python
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 1. Definiraj shemu
class Osoba(BaseModel):
    ime: str
    godine: int
    grad: str

# 2. Pozovi model s parse()
response = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Ivan ima 32 godine i živi u Zagrebu."}
    ],
    response_format=Osoba,
)

# 3. Dobij objekt natrag
osoba = response.choices[0].message.parsed
print(osoba.ime)    # Ivan
print(osoba.godine) # 32
print(osoba.grad)   # Zagreb
```

## Pydantic tipovi koji rade

```python
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class Kategorija(str, Enum):
    POSAO   = "posao"
    PRIVATNO = "privatno"
    HITNO   = "hitno"

class Zadatak(BaseModel):
    naziv:      str
    opis:       str
    prioritet:  int              # 1-5
    kategorija: Kategorija       # enum
    tagovi:     List[str]        # lista
    rok:        Optional[str]    # može biti None
```

## Ugniježđeni objekti

```python
class Adresa(BaseModel):
    ulica: str
    grad:  str
    država: str

class Tvrtka(BaseModel):
    naziv:     str
    osnivanje: int
    adresa:    Adresa            # ugniježđeni objekt
    zaposlenici: List[str]
```

## Ekstrakcija podataka iz teksta

```python
class Artikl(BaseModel):
    naziv:  str
    cijena: float
    valuta: str

class Racun(BaseModel):
    artikli: List[Artikl]
    ukupno:  float

tekst = "Kava 2.50 EUR, kroasan 1.80 EUR, sok 3.00 EUR"

response = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Ekstraktaj artikle s računa."},
        {"role": "user",   "content": tekst},
    ],
    response_format=Racun,
)

racun = response.choices[0].message.parsed
for artikl in racun.artikli:
    print(f"{artikl.naziv}: {artikl.cijena} {artikl.valuta}")
```

## Provjera je li model uspio parsirati

```python
msg = response.choices[0].message

if msg.parsed:
    print(msg.parsed)       # objekt
elif msg.refusal:
    print("Model odbio:", msg.refusal)
```

## Pydantic validacija (besplatna provjera)

```python
from pydantic import BaseModel, Field, field_validator

class Proizvod(BaseModel):
    naziv:  str
    cijena: float = Field(gt=0, description="Mora biti pozitivna")
    kolicina: int = Field(ge=0, le=1000)

    @field_validator("naziv")
    def naziv_ne_smije_biti_prazan(cls, v):
        if not v.strip():
            raise ValueError("Naziv ne smije biti prazan")
        return v.strip()
```

## Tipičan pattern: system prompt + user data

```python
class Sentiment(BaseModel):
    ocjena:    int          # 1-5
    sentiment: str          # "pozitivan" / "negativan" / "neutralan"
    kljucne_rijeci: List[str]

response = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Analiziraj sentiment recenzije."},
        {"role": "user",   "content": "Odličan proizvod, brza dostava!"},
    ],
    response_format=Sentiment,
)

print(response.choices[0].message.parsed)
```

## Sažetak

| što                  | kako                                      |
|----------------------|-------------------------------------------|
| definiraj shemu      | `class X(BaseModel)`                      |
| pozovi model         | `client.beta.chat.completions.parse()`    |
| dohvati objekt       | `response.choices[0].message.parsed`      |
| opcionalno polje     | `Optional[str] = None`                    |
| lista                | `List[str]`                               |
| enum                 | `class X(str, Enum)`                      |
| validacija           | `Field(gt=0)` ili `@field_validator`      |

> ⚠ `.parse()` je beta metoda specifična za OpenAI SDK — interno koristi `response_format` s JSON shemom
