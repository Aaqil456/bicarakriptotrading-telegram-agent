import os
import time
import requests

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-2.5-flash"  # current, fast & cheap. Change to gemini-2.5-pro if you prefer.

def translate_text_gemini(text: str, model: str = GEMINI_MODEL) -> str:
    """
    Translates `text` to Malay using Google Gemini API (Developer API).
    Returns translated text or "" on failure.
    """
    if not text or not isinstance(text, str) or not text.strip():
        print(f"[Warning] Empty or invalid text received for translation: {text}")
        return ""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,  # <-- use header, not ?key=
    }

     prompt = (
        "Translate the following text into natural, conversational Malaysian Malay.\n\n"
    
        "### TONE & STYLE:\n"
        "- Use a friendly, relaxed, and 'santai' tone, like a friend sharing info.\n"
        "- Keep it simple and easy to understand.\n"
        "- Avoid exaggerated slang or interjections (No 'Eh', 'Korang', 'Woi', 'Wooohooo').\n"
        "- Maintain a clean, neutral, and informative vibe without unnecessary excitement.\n\n"
        
        "### KEY TERMINOLOGY:\n"
        "- 'Market Events' -> 'Update Pasaran'\n"
        "- 'Top Mindshare Gainers' -> 'Projek Crypto Viral Hari Ini'\n"
        "- Do not translate brand names or product names.\n\n"
    
        "### LINK & SOURCE HANDLING (CRITICAL):\n"
        "- STRICTLY REMOVE all external source attributions, URLs, and phrases mentioning where the post originated (e.g., delete lines like 'Source: [Link]', 'Originally from...', 'Read more at...').\n"
        "- The ONLY exception is 'ref' tags. Translate 'ref0, ref1, ref2' into the format 'SUMBER: 0 1 2' while preserving their original hyperlinks.\n\n"
    
        "### OUTPUT RULES:\n"
        "- Return ONLY the translated text.\n"
        "- No explanations, no introductory text, and no emojis (unless they are in the original text).\n\n"
        f"Text:\n{text}"
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        # Optional: you can guide style further
        "generationConfig": {
            "temperature": 0.2
        }
    }

    # Retry with exponential backoff for transient errors
    retries = 5
    backoff = 2
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            # If you want to see the exact error body on non-2xx:
            if not resp.ok:
                # Helpful debug print
                try:
                    print(f"[Error] HTTP {resp.status_code}: {resp.text[:500]}")
                except Exception:
                    pass
                resp.raise_for_status()

            data = resp.json()

            # Robust parse: candidates[0].content.parts[*].text
            candidates = data.get("candidates", [])
            if not candidates:
                print(f"[Warning] No candidates returned on attempt {attempt}.")
            else:
                parts = candidates[0].get("content", {}).get("parts", [])
                for p in parts:
                    t = p.get("text", "").strip()
                    if t:
                        print(f"[Success] Translation completed for: {text[:60]}...")
                        return t

            print(f"[Warning] Empty translation on attempt {attempt}. Retrying...")
        except requests.exceptions.RequestException as e:
            print(f"[Error] Attempt {attempt} - Translation failed: {e}")
        time.sleep(backoff ** attempt)

    print(f"[Error] All attempts failed to translate: {text[:60]}...")
    return ""
