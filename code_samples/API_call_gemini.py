from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/")


response = client.chat.completions.create(
    model="gemini-2.5-flash",
    messages=[
        {"role": "user", "content": "Write a one-sentence bedtime story about a unicorn."}
    ]
)

print(response.choices[0].message.content)
