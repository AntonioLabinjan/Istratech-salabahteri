from pydantic import BaseModel
import ollama


class AIResponse(BaseModel):
    category: str
    priority: int
    summary: str
    confidence: float


response = ollama.chat(
    model="qwen2.5:0.5b",
    messages=[
        {
            "role": "system",
            "content": """
            You are an AI assistant that analyzes customer complaints.
            Categorize the complaint, assign a priority from 1 to 5,
            summarize the issue, and provide confidence score.
            Your response must be only valid JSON matching the provided schema.
            Return confidence as a percentage between 0 and 100.
            """
        },
        {
            "role": "user",
            "content": """
            I have submitted an order using webshop, but no conformation email has been recieved.
            I ordered 4 hours ago, and site said that I should expect an answer in 10 minutes.
            """
        }
    ],
    format=AIResponse.model_json_schema()
)


raw = response["message"]["content"]

result = AIResponse.model_validate_json(raw)


print("Category:", result.category)
print("Priority:", result.priority)
print("Summary:", result.summary)
print("Confidence:", result.confidence)
