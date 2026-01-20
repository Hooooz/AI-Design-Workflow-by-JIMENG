import asyncio
import os
import sys

# Add the directory to sys.path to import server
sys.path.append(os.getcwd())

from server import generate_image

async def main():
    print("Testing generate_image function directly...")
    try:
        # prompt, file_name, save_folder
        # Using a simple prompt
        prompt = "A cute cat"
        file_name = "test_cat.jpg"
        save_folder = os.path.join(os.getcwd(), "images")
        
        print(f"Prompt: {prompt}")
        print(f"Save folder: {save_folder}")
        
        result = await generate_image(
            prompt=prompt,
            file_name=file_name,
            save_folder=save_folder,
            sample_strength=0.5,
            width=1024,
            height=1024
        )
        
        print("Result:", result)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
