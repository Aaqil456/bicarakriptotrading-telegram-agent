import os
import time
import requests

# Pastikan API Key ada dalam Environment Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Menggunakan 1.5-flash untuk kestabilan rate limit yang lebih baik pada akaun percuma
GEMINI_MODEL = "gemini-2.5-flash" 

def translate_text_gemini(text: str, model: str = GEMINI_MODEL) -> str:
    """
    Translates `text` to Malay using Google Gemini API.
    Implemented with Throttling & 429 Handling to prevent Rate Limits.
    """
    if not text or not isinstance(text, str) or not text.strip():
        print(f"[Warning] Teks kosong atau tidak sah diterima.")
        return ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }

    prompt = (
        "Translate the following text into natural, conversational Malaysian Malay.\n\n"
        "### TONE & STYLE:\n"
        "- Use a friendly, relaxed, and 'santai' tone, like a friend sharing info.\n"
        "- Keep it simple and easy to understand.\n"
        "- Avoid exaggerated slang or interjections.\n"
        "- Maintain a clean, neutral, and informative vibe.\n\n"
        "### KEY TERMINOLOGY:\n"
        "- 'Market Events' -> 'Update Pasaran'\n"
        "- 'Top Mindshare Gainers' -> 'Projek Crypto Viral Hari Ini'\n\n"
        "### LINK & SOURCE HANDLING:\n"
        "- STRICTLY REMOVE platform tags and source links.\n"
        "- PURGE call-to-action phrases (e.g., 'Read more').\n"
        "- Exception: 'ref0, ref1' -> 'SUMBER: 0 1'.\n\n"
        "### OUTPUT RULES:\n"
        "- Return ONLY the translated text.\n"
        f"Text:\n{text}"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }

    retries = 5
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            
            # Jika terkena Rate Limit (429)
            if resp.status_code == 429:
                wait_time = 60  # Tunggu 1 minit penuh jika kena block
                print(f"[Warning] HTTP 429 (Rate Limit). Rehat {wait_time}s sebelum cuba balik...")
                time.sleep(wait_time)
                continue 

            if not resp.ok:
                print(f"[Error] HTTP {resp.status_code}: {resp.text[:200]}")
                resp.raise_for_status()

            data = resp.json()
            candidates = data.get("candidates", [])
            
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for p in parts:
                    t = p.get("text", "").strip()
                    if t:
                        print(f"[Success] Terjemahan selesai.")
                        
                        # --- CARA 1: FIXED THROTTLING ---
                        # Kita paksa rehat 5 saat selepas setiap kejayaan.
                        # Ini memastikan kita tidak hantar lebih 12 request seminit.
                        time.sleep(5) 
                        
                        return t

            print(f"[Warning] Tiada hasil pada cubaan {attempt}. Cuba lagi...")
            
        except requests.exceptions.RequestException as e:
            print(f"[Error] Cubaan {attempt} gagal: {e}")
            time.sleep(2 ** attempt) # Exponential backoff untuk error rangkaian biasa

    print(f"[Error] Semua cubaan gagal untuk teks: {text[:50]}...")
    return ""
