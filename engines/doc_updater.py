import os
import json
import requests
import sys

# Fetch the secret API key
API_KEY = os.getenv("AI_Auto_Projrct_Information_Updater")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "meta-llama/llama-3.3-70b-instruct"

if not API_KEY:
    print("[!] Error: AI_Auto_Projrct_Information_Updater environment variable is missing." )
    sys.exit(1)

def generate_markdown(prompt_instruction, context_data):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system", 
                "content": "You are an elite Systems Architect and Technical Writer. Output ONLY valid Markdown. Do not include conversational filler."
            },
            {
                "role": "user", 
                "content": f"{prompt_instruction}\n\n### PROJECT ARCHITECTURE CONTEXT:\n{context_data}"
            }
        ]
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"[!] API Request Failed: {e}")
        sys.exit(1)

def main():
    memory_path = "PROJECT_MEMORY.md"
    
    if not os.path.exists(memory_path):
        print(f"[!] {memory_path} not found. Cannot update documentation without context.")
        sys.exit(1)
        
    with open(memory_path, "r", encoding="utf-8") as f:
        project_memory = f.read()

    print("[*] Generating README.md...")
    readme_prompt = "Write a comprehensive, professional README.md for this project. Include project overview, architecture, and usage instructions based on the provided context. Maintain a Cyberpunk/OffSec aesthetic in the writing style."
    readme_content = generate_markdown(readme_prompt, project_memory)
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("[+] README.md updated successfully.")

    print("[*] Generating DEVELOP.md...")
    develop_prompt = "Write a highly technical DEVELOP.md guide for contributors. Detail the file structure, function call chains, and how the engines (alien_generator, dialogue_generator, core_engine) interact. Provide strict guidelines for adding new features."
    develop_content = generate_markdown(develop_prompt, project_memory)
    
    with open("DEVELOP.md", "w", encoding="utf-8") as f:
        f.write(develop_content)
    print("[+] DEVELOP.md updated successfully.")

if __name__ == "__main__":
    main()
