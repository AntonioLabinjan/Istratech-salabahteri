from pydantic import BaseModel
from dotenv import load_dotenv
import os
import ollama


load_dotenv()

MODEL = os.getenv("MODEL", "qwen2.5:0.5b")


class AIResponse(BaseModel):
    category: str
    priority: int
    summary: str
    confidence: float


response = ollama.chat(
    model=MODEL,
    messages=[
        {
            "role": "system",
            "content": """
            You are an AI assistant that analyzes customer complaints.

            Return ONLY valid JSON matching the schema.

            Rules:
            - category: short label
            - priority: integer from 1 to 5 (5 = critical)
            - summary: short explanation of the issue
            - confidence: value between 0 and 100
            """
        },
        {
            "role": "user",
            "content": """
            I have submitted an order using a webshop,
            but no confirmation email has been received.

            I ordered 4 hours ago, and the website said
            I should receive an answer within 10 minutes.

            It would be good to fix this, because I need my stuff urgently.
            You can contact me using my email: joe@gmail.com
            """
        }
    ],
    format=AIResponse.model_json_schema()
)


result = AIResponse.model_validate_json(
    response["message"]["content"]
)


print("Category:", result.category)
print("Priority:", result.priority)
print("Summary:", result.summary)
print("Confidence:", result.confidence)
