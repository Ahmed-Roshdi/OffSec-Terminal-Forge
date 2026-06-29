#!/usr/bin/env python3
import requests
from base64 import b64encode
from nacl import encoding, public

# ==========================================
# Target Repository Configuration
# ==========================================
REPO_OWNER = "Ahmed-Roshdi"
REPO_NAME = "OffSec-Terminal-Forge"
SECRET_NAME = "GROQ_API_KEY"

def encrypt(public_key: str, secret_value: str) -> str:
    public_key_bytes = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key_bytes)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")

def main():
    print(f"[*] Target Repository: {REPO_OWNER}/{REPO_NAME}")
    print(f"[*] Target Secret: {SECRET_NAME}\n")

    # استخدام input العادية لرؤية النص بوضوح
    github_token = input("[?] Enter your GitHub PAT (starts with ghp_): ").strip()
    if not github_token:
        print("[!] GitHub PAT cannot be empty. Exiting.")
        return

    secret_value = input(f"[?] Enter the value for {SECRET_NAME}: ").strip()
    if not secret_value:
        print("[!] Secret value cannot be empty. Exiting.")
        return

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    print("\n[*] Fetching public key from GitHub API...")
    url_pub_key = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/secrets/public-key"
    
    res = requests.get(url_pub_key, headers=headers )
    if res.status_code != 200:
        print(f"[!] Failed to fetch public key. HTTP {res.status_code}: {res.json()}")
        return

    key_data = res.json()
    public_key = key_data["key"]
    key_id = key_data["key_id"]
    print("[+] Public key fetched successfully.")

    print("[*] Encrypting secret using Libsodium (X25519)...")
    encrypted_value = encrypt(public_key, secret_value)

    print(f"[*] Uploading encrypted secret '{SECRET_NAME}' to GitHub...")
    url_secret = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/secrets/{SECRET_NAME}"
    
    payload = {
        "encrypted_value": encrypted_value,
        "key_id": key_id
    }

    res_put = requests.put(url_secret, headers=headers, json=payload )
    
    if res_put.status_code in [201, 204]:
        print(f"[+] Success! Secret '{SECRET_NAME}' has been securely set/updated.")
    else:
        print(f"[!] Failed to upload secret. HTTP {res_put.status_code}: {res_put.text}")

if __name__ == "__main__":
    main()
