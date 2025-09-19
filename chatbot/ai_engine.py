import os
import requests
from chatbot.context import inject_portfolio_context

def get_ai_reply(user_message: str) -> str:
    prompt = inject_portfolio_context(user_message)

    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistralai/mistral-small-3.1-24b-instruct:free",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("❌ OpenRouter API error:", e)
        return "Sorry, something went wrong while generating the response."
