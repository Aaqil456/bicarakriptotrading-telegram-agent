import os
import time
import requests

# Use the technical Model ID (e.g., adding '-001' or '-preview' as per AI Studio specs)
# For Gemini 3.1 Flash Lite, the stable endpoint is usually:
GEMINI_MODEL = "gemini-3.1-flash-lite-preview" 

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def translate_text_gemini(text: str, model: str = GEMINI_MODEL) -> str:
    """
    Translates text to Malay and PURGES all source links/platforms.
    Limits retries to 2 attempts to prevent long hangs.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }

    prompt = (
        "Translate the following text into natural, conversational Malaysian Malay.\n\n"
        "### TONE & STYLE:\n"
        "- Use a friendly, relaxed, and 'santai' tone.\n"
        "- Keep it simple and easy to understand.\n"
        "- Maintain a clean, neutral, and informative vibe.\n\n"
        "### LINK & SOURCE HANDLING:\n"
        "- STRICTLY REMOVE platform tags and source links.\n"
        "- PURGE call-to-action phrases (e.g., 'Read more').\n"
        "### OUTPUT RULES:\n"
        "- Return ONLY the translated text.\n"
        f"Text:\n{text}"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            
            # 1. Handle Success
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    output = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                    print(f"[Success] Cubaan #{attempt} Berjaya.")
                    # Optional: Small delay to respect rate limits (RPM)
                    time.sleep(2) 
                    return output

            # 2. Handle Specific "Model Not Found" (404) - Stop immediately
            if resp.status_code == 404:
                print(f"[Critical] Error 404: Model '{model}' tidak dijumpai. Sila semak Model ID.")
                break 

            # 3. Handle Rate Limits (429)
            if resp.status_code == 429:
                wait_time = 30 * attempt
                print(f"[Warning] Google Sekat (429). Rehat {wait_time}s...")
                time.sleep(wait_time)
            
            # 4. Handle other Server Errors (500, 503)
            else:
                print(f"[Error] HTTP {resp.status_code}. Rehat 10s sebelum cubaan terakhir...")
                time.sleep(10)

        except Exception as e:
            print(f"[Error] Masalah teknikal: {e}")
            time.sleep(5)

    # If all attempts fail, return original text so the bot doesn't crash
    print(f"[Fail] Gagal selepas {max_retries} cubaan. Menggunakan teks asal.")
    return text
