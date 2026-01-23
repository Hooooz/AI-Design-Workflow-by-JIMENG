
import os
import sys
from openai import OpenAI

# Config
API_KEY = "sk-C66yMy0MUM_n0vPU4PgCF_mtzNYsYYfY3YmgZsBlhqIS0oq6"
BASE_URL = "http://47.89.249.90:8000/openai/v1"

models_to_test = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash-exp", "gpt-4o-mini"]

print(f"Testing LLM connection...")
print(f"URL: {BASE_URL}")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

for model in models_to_test:
    print(f"\n--- Testing {model} ---")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10
        )
        content = response.choices[0].message.content
        print(f"Response: {content}")
        if content:
            print(f"✅ {model} Success")
        else:
            print(f"❌ {model} Returned Empty")
    except Exception as e:
        print(f"❌ {model} Failed: {e}")
