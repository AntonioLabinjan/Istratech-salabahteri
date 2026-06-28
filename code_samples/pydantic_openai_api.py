from dotenv import load_dotenv
from openai import OpenAI
from openai import RateLimitError
from pydantic import BaseModel


# Učitava API ključ iz .env datoteke
load_dotenv()

# Kreira OpenAI klijenta
client = OpenAI()


# Definiramo strukturu koju želimo dobiti od modela.
# LLM neće vratiti običan tekst nego objekt koji odgovara ovoj shemi.
class AIResponse(BaseModel):
    topic: str
    explanation: str
    confidence: float


try:
    response = client.chat.completions.parse(
        model="gpt-5",

        messages=[
            {
                # System definira ponašanje modela
                "role": "system",
                "content": "Ti si AI asistent koji daje strukturirane odgovore."
            },
            {
                # User šalje upit
                "role": "user",
                "content": "Objasni što je umjetna inteligencija."
            }
        ],

        # Govorimo API-ju da odgovor mora odgovarati AIResponse Pydantic shemi
        response_format=AIResponse
    )


    # Umjesto običnog stringa dobivamo Python objekt.
    result = response.choices[0].message.parsed


    # Pristupamo poljima kao kod normalnog Python objekta
    print("Tema:", result.topic)
    print("Objašnjenje:", result.explanation)
    print("Sigurnost:", result.confidence)


except RateLimitError:
    print("Nema dovoljno creditsa za korištenje OpenAI API-ja.")


except Exception as e:
    print(f"Dogodila se greška: {e}")
