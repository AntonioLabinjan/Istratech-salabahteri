# Python venv & API key šalabahter

## Kreiranje i aktivacija

```bash
python -m venv .venv          # napravi venv folder
source .venv/bin/activate     # macOS / Linux
.venv\Scripts\activate        # Windows
deactivate                    # izlaz iz venv-a
```

## Paketi

```bash
pip install requests                  # instaliraj paket
pip freeze > requirements.txt         # spremi popis
pip install -r requirements.txt       # instaliraj sve
pip list                              # što je instalirano
```

## Struktura projekta

```
projekt/
├── .venv/            # NIKAD u git!
├── .env              # NIKAD u git!
├── .gitignore
├── requirements.txt
└── main.py
```

## .gitignore

```
.env
.venv/
__pycache__/
```

## .env

```
API_KEY=tvoj-tajni-kljuc
DB_URL=postgres://localhost/mydb
```

## main.py — čitanje API key-a

```python
# pip install python-dotenv
from dotenv import load_dotenv
import os

load_dotenv()  # učita .env

api_key = os.getenv("API_KEY")
```

> ⚠ API key nikad ne ide direktno u kod — samo kroz .env
