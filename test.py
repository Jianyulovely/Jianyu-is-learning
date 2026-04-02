import requests

resp = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen2.5:0.5b",
        "prompt": "Why is the sky blue?",
        "stream": False
    }
)

print(resp.json().get('response'))