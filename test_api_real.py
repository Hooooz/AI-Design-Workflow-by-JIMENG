
import os
import sys
import json
from openai import OpenAI

# 模拟 config.py 中的配置
API_KEY = "sk-C66yMy0MUM_n0vPU4PgCF_mtzNYsYYfY3YmgZsBlhqIS0oq6"
BASE_URL = "http://47.89.249.90:8000/openai/v1"
MODEL = "gemini-2.5-flash"

def test_real_api():
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    
    print(f"Testing API at {BASE_URL} with model {MODEL}...")
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": "你好，请问你是谁？请回复一段随机的字符串以证明你是实时的。"}
            ],
            temperature=0.7
        )
        content = response.choices[0].message.content
        print("\n--- API Response ---")
        print(content)
        print("--------------------\n")
    except Exception as e:
        print(f"API Call Failed: {e}")

if __name__ == "__main__":
    test_real_api()
