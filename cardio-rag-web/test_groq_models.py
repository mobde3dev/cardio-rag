import os
import sys
import json
import urllib.request
import urllib.error
import ssl

sys.stdout.reconfigure(encoding='utf-8')
ssl_context = ssl._create_unverified_context()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "CardioRAG-Test/1.0"
}

def list_models():
    req = urllib.request.Request("https://api.groq.com/openai/v1/models", headers=headers)
    try:
        with urllib.request.urlopen(req, context=ssl_context) as resp:
            data = json.loads(resp.read().decode())
            print("Available Groq Models:")
            models = [m['id'] for m in data.get("data", [])]
            for m in models:
                print(f" - {m}")
            return models
    except Exception as e:
        print(f"Error fetching models: {e}")
        return []

def test_translation_and_completion(model="llama-3.3-70b-versatile"):
    sample_arabic_q = "ما هي الفئات الدوائية الثلاث الموصى بها كعلاج أولي للبالغين المصابين بارتفاع ضغط الدم؟"
    
    # 1. Test translation prompt using qwen/qwen3.6-27b or openai/gpt-oss-20b
    translate_payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [
            {
                "role": "system",
                "content": "You are a professional medical translator. Translate the given Arabic clinical question into clear, precise English optimized for medical literature and vector embedding semantic search. Output ONLY the English translation."
            },
            {
                "role": "user",
                "content": sample_arabic_q
            }
        ],
        "temperature": 0.1,
        "max_tokens": 150
    }
    
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(translate_payload).encode(),
        headers=headers
    )
    
    translated_en = ""
    try:
        with urllib.request.urlopen(req, context=ssl_context) as resp:
            res = json.loads(resp.read().decode())
            translated_en = res["choices"][0]["message"]["content"].strip()
            print(f"\n[Translation Test]")
            print(f"Original Arabic: {sample_arabic_q}")
            print(f"Translated English: {translated_en}")
    except Exception as e:
        print(f"Translation Error: {e}")
        return

    # 2. Test Clinical Answering prompt
    rag_payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {
                "role": "system",
                "content": """You are CardioRAG, an evidence-based clinical cardiology AI assistant.
Answer the user's question accurately in Arabic (matching the user's original language), strictly based on clinical guidelines (NICE NG136 & WHO 2021).
Structure your response clearly with:
1. Direct clinical answer
2. Specific guideline citations (e.g. NICE NG136, WHO 2021)
3. Recommendation strength (e.g. Strong / Conditional)
4. Clinical safety note"""
            },
            {
                "role": "user",
                "content": sample_arabic_q
            }
        ],
        "temperature": 0.2,
        "max_tokens": 800
    }
    
    req2 = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(rag_payload).encode(),
        headers=headers
    )
    
    try:
        with urllib.request.urlopen(req2, context=ssl_context) as resp:
            res2 = json.loads(resp.read().decode())
            answer = res2["choices"][0]["message"]["content"].strip()
            print(f"\n[Clinical Answer from openai/gpt-oss-120b]:")
            print(answer)
    except Exception as e:
        print(f"Completion Error: {e}")

if __name__ == "__main__":
    models = list_models()
    test_translation_and_completion()

