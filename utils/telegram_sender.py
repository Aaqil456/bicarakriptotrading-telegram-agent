import os
import re
import html
import json
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

API_BASE = "https://api.telegram.org"
MESSAGE_LIMIT = 4096
CAPTION_LIMIT = 1024  # Safe caption limit for Telegram photos

# -------------------- Markdown → HTML (safe subset) --------------------

def render_html_with_basic_md(text: str) -> str:
    if not text:
        return ""

    token_re = re.compile(
        r'(\[([^\]]+)\]\((https?://[^)\s]+)\)|'          # [label](url)
        r'(\*\*|__)(.+?)\4|'                             # **bold**
        r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|'          # *italic*
        r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_))',               # _italic_
        re.DOTALL
    )

    out = []
    i = 0
    for m in token_re.finditer(text):
        out.append(html.escape(text[i:m.start()]))

        full = m.group(1)
        link_label = m.group(2)
        link_href  = m.group(3)
        bold_delim = m.group(4)
        bold_inner = m.group(5)
        italic_star_inner = m.group(6)
        italic_underscore_inner = m.group(7)

        if link_label and link_href:
            out.append(f'<a href="{html.escape(link_href, quote=True)}">{html.escape(link_label)}</a>')
        elif bold_delim and bold_inner is not None:
            out.append(f'<b>{html.escape(bold_inner)}</b>')
        elif italic_star_inner is not None:
            out.append(f'<i>{html.escape(italic_star_inner)}</i>')
        elif italic_underscore_inner is not None:
            out.append(f'<i>{html.escape(italic_underscore_inner)}</i>')
        else:
            out.append(html.escape(full))
        i = m.end()

    out.append(html.escape(text[i:]))
    return "".join(out)

# -------------------- Splitter --------------------

def _split_for_telegram_raw(text: str, limit: int) -> list[str]:
    if text is None:
        return [""]
    if len(text) <= limit:
        return [text]

    parts, current = [], []
    cur_len = 0
    for para in text.split("\n\n"):
        chunk = para + "\n\n"
        if cur_len + len(chunk) <= limit:
            current.append(chunk); cur_len += len(chunk)
        else:
            if current:
                parts.append("".join(current).rstrip())
                current, cur_len = [], 0
            if len(chunk) > limit:
                for line in chunk.split("\n"):
                    line_n = line + "\n"
                    if len(line_n) > limit:
                        words = line_n.split(" ")
                        buf, L = [], 0
                        for w in words:
                            w2 = w + " "
                            if L + len(w2) <= limit:
                                buf.append(w2); L += len(w2)
                            else:
                                parts.append("".join(buf).rstrip())
                                buf, L = [w2], len(w2)
                        if buf: parts.append("".join(buf).rstrip())
                    else:
                        if cur_len + len(line_n) <= limit:
                            current.append(line_n); cur_len += len(line_n)
                        else:
                            parts.append("".join(current).rstrip())
                            current, cur_len = [line_n], len(line_n)
            else:
                current, cur_len = [chunk], len(chunk)
    if current:
        parts.append("".join(current).rstrip())
    return [p[:limit] for p in parts]

# -------------------- Public send functions --------------------

def send_telegram_message_html(translated_text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram credentials not set.")
        return []

    raw_chunks = _split_for_telegram_raw(translated_text or "", MESSAGE_LIMIT)
    url = f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    results = []

    for i, raw_chunk in enumerate(raw_chunks, 1):
        safe_html = render_html_with_basic_md(raw_chunk)
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": safe_html,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        try:
            r = requests.post(url, json=payload, timeout=20)
            results.append(r.json())
            if r.ok and r.json().get("ok"):
                print(f"✅ Telegram message part {i}/{len(raw_chunks)} sent.")
            else:
                print(f"❌ Telegram error: {r.text}")
        except Exception as e:
            print(f"❌ Telegram exception: {e}")
    return results

def send_photo_to_telegram_channel(image_path: str, translated_caption: str):
    """Sends a single photo with caption."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return None

    raw_caption = translated_caption or ""
    head_raw = raw_caption[:CAPTION_LIMIT]
    tail_raw = raw_caption[CAPTION_LIMIT:]
    caption_html = render_html_with_basic_md(head_raw)

    url = f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(image_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption_html, "parse_mode": "HTML"}
            r = requests.post(url, data=data, files=files, timeout=30)
        
        if r.ok:
            print(f"✅ Photo sent. Caption len={len(head_raw)}.")
            if tail_raw:
                send_telegram_message_html(tail_raw)
        return r.json()
    except Exception as e:
        print(f"❌ Photo exception: {e}")
        return None

def send_media_group_to_telegram(image_paths: list[str], translated_caption: str):
    """
    Sends multiple photos as an album. 
    Handles single photo fallback and caption splitting.
    """
    if not image_paths:
        return None
    
    if len(image_paths) == 1:
        return send_photo_to_telegram_channel(image_paths[0], translated_caption)

    raw_caption = translated_caption or ""
    head_raw = raw_caption[:CAPTION_LIMIT]
    tail_raw = raw_caption[CAPTION_LIMIT:]
    caption_html = render_html_with_basic_md(head_raw)

    url = f"{API_BASE}/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup"
    
    media = []
    files = {}
    
    # Telegram requires the 'media' field to be a JSON string referencing the files
    for i, path in enumerate(image_paths):
        file_key = f"photo_{i}"
        try:
            files[file_key] = open(path, "rb")
            item = {
                "type": "photo",
                "media": f"attach://{file_key}",
                "parse_mode": "HTML"
            }
            if i == 0:  # Attach caption only to the first photo
                item["caption"] = caption_html
            media.append(item)
        except Exception as e:
            print(f"❌ Error opening {path}: {e}")

    try:
        # Multi-part post: files + the media list as a string
        payload = {
            "chat_id": (None, TELEGRAM_CHAT_ID),
            "media": (None, json.dumps(media))
        }
        
        r = requests.post(url, files={**files, **payload}, timeout=60)
        
        # Cleanup: close files
        for f in files.values(): f.close()

        if r.ok:
            print(f"✅ Media Group (Album) sent with {len(image_paths)} photos.")
            if tail_raw:
                send_telegram_message_html(tail_raw)
        else:
            print(f"❌ Failed to send Media Group: {r.text}")
        return r.json()
    except Exception as e:
        print(f"❌ Media Group exception: {e}")
        return None
