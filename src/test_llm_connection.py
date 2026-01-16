from llm_wrapper import LLMService
import config

def test_llm():
    print(f"Testing LLM with Base URL: {config.OPENAI_BASE_URL}")
    print(f"API Key: {config.OPENAI_API_KEY[:5]}...")
    
    llm = LLMService()
    if not llm.client:
        print("Failed to initialize client")
        return

    messages = [{"role": "user", "content": "Hello, are you working?"}]
    response = llm.chat_completion(messages)
    print(f"Response: {response}")

if __name__ == "__main__":
    test_llm()
