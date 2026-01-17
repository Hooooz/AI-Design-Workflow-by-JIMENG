
import os
import sys
from openai import OpenAI
import config

# Define the models to test using IDs from the server list
models_to_test = [
    "models/gemini-3-flash-preview",
    "models/gemini-2.5-flash",
    "models/gemini-2.5-flash-lite",
    "models/gemma-3-12b-it",
    "models/gemini-2.0-flash",
    "models/gemini-2.0-flash-lite",
    "models/gemini-flash-latest",
    "models/gemini-pro-latest"
]

def test_models():
    print("Starting model availability test...")
    print(f"Base URL: {config.OPENAI_BASE_URL}")
    # Don't print the full key for security
    print(f"API Key: {config.OPENAI_API_KEY[:5]}...")

    client = OpenAI(
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL
    )

    print("\nAttempting to list available models from server...")
    try:
        models = client.models.list()
        print("Available models:")
        for model in models:
            print(f"- {model.id}")
    except Exception as e:
        print(f"Could not list models: {str(e)}")

    results = {}

    for model in models_to_test:
        print(f"\nTesting model: {model}...")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": "Hello, are you available? Reply with 'Yes' only."}
                ],
                max_tokens=10
            )
            reply = response.choices[0].message.content
            print(f"✅ Success! Reply: {reply}")
            results[model] = True
        except Exception as e:
            print(f"❌ Failed. Error: {str(e)}")
            results[model] = False

    print("\n--- Summary ---")
    for model, success in results.items():
        status = "Available" if success else "Unavailable"
        print(f"{model}: {status}")

if __name__ == "__main__":
    test_models()
