# OpenAI Python API šalabahter

## Instalacija

```bash
pip install openai python-dotenv
```

## .env

```
OPENAI_API_KEY=sk-...
```

## Osnovna struktura poziva (chat.completions)

```python
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Ti si koristan asistent."},
        {"role": "user",   "content": "Što je Python?"},
    ]
)

print(response.choices[0].message.content)
```

## Uloge poruka (roles)

| role       | svrha                                              |
|------------|----------------------------------------------------|
| `system`   | Instrukcije modelu — ton, persona, ograničenja     |
| `user`     | Poruka korisnika                                   |
| `assistant`| Prethodni odgovor modela (za višeturni razgovor)   |

## Višeturni razgovor (chat history)

```python
messages = [
    {"role": "system", "content": "Ti si koristan asistent."},
]

# Dodaj korisnikov unos
messages.append({"role": "user", "content": "Kako se zoveš?"})

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages
)

odgovor = response.choices[0].message.content
print(odgovor)

# Spremi odgovor u povijest za sljedeći turn
messages.append({"role": "assistant", "content": odgovor})
```

## Struktura response objekta

```python
response.choices[0].message.content   # tekst odgovora
response.choices[0].message.role      # uvijek "assistant"
response.usage.prompt_tokens          # tokeni inputa
response.usage.completion_tokens      # tokeni outputa
response.usage.total_tokens           # ukupno
```

## Korisni parametri

```python
client.chat.completions.create(
    model="gpt-4o-mini",   # ili gpt-4o, gpt-4-turbo...
    messages=[...],
    temperature=0.7,        # 0 = deterministično, 2 = kreativno
    max_tokens=500,         # max duljina odgovora
)
```

## Modeli (cijena raste s kvalitetom)

| model          | brzina | kvaliteta | cijena |
|----------------|--------|-----------|--------|
| gpt-4o-mini    | brz    | dobra     | $      |
| gpt-4o         | srednji| odlična   | $$$    |
| gpt-4-turbo    | sporiji| izvrsna   | $$$$   |

