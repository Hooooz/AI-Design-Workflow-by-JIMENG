
import requests
import json

BASE_URL = "http://localhost:8000"

def test_autocomplete():
    print("Testing /api/ai/autocomplete...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/ai/autocomplete",
            json={"brief": "设计一款简约风格的智能台灯", "model_name": "models/gemma-3-12b-it"},
            timeout=30
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

def test_tags():
    print("\nTesting /api/ai/tags...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/ai/tags",
            json={"brief": "设计一款简约风格的智能台灯", "model_name": "models/gemini-2.5-flash-lite"},
            timeout=30
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_autocomplete()
    test_tags()
