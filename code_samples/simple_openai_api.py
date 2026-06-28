from dotenv import load_dotenv
from openai import OpenAI
from openai import RateLimitError

# Učitava varijable iz .env datoteke.
# U našem slučaju učitava OPENAI_API_KEY tako da ga ne moramo pisati direktno u kod.
load_dotenv()

# Kreira OpenAI klijenta.
# Klijent automatski koristi API ključ spremljen u environment varijabli OPENAI_API_KEY.
client = OpenAI()


try:
    # Slanje zahtjeva LLM modelu preko API-ja.
    response = client.chat.completions.create(
        # Model koji će obraditi zahtjev.
        model="gpt-5",

        # "messages" predstavlja razgovor između korisnika i modela.
        # Svaka poruka ima:
        # - role: tko šalje poruku
        # - content: sadržaj poruke
        messages=[
            {
                # SYSTEM definira ponašanje modela.
                "role": "system",
                "content": "Ti si koristan AI asistent koji odgovara kratko i jasno."
            },
            {
                # USER predstavlja stvarni upit korisnika.
                "role": "user",
                "content": "Objasni što je umjetna inteligencija u dvije rečenice."
            }
        ]
    )

    # Dohvaćanje teksta odgovora koji je generirao model.
    answer = response.choices[0].message.content

    # Ispis odgovora.
    print(answer)


except RateLimitError:
    # Ova greška se događa kada nema dovoljno kredita
    # ili je prekoračena API kvota.
    print("Nema dovoljno creditsa za korištenje OpenAI API-ja.")


except Exception as e:
    # Ostale neočekivane greške.
    print(f"Dogodila se greška: {e}")
