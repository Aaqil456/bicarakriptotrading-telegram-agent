from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto

# Fungsi ini yang hilang tadi:
def extract_channel_username(url):
    """Mengambil username daripada URL Telegram"""
    if not url:
        return ""
    return '@' + url.strip().rstrip('/').split('/')[-1]

async def fetch_latest_messages(api_id, api_hash, channel_username, limit=10):
    client = TelegramClient("telegram_session", api_id, api_hash)
    await client.start()
    
    messages = []
    # Dictionary untuk group media ikut grouped_id (Album)
    media_groups = {}

    async for message in client.iter_messages(channel_username, limit=limit):
        has_photo = isinstance(message.media, MessageMediaPhoto)
        
        # Jika mesej adalah sebahagian daripada album
        if message.grouped_id:
            if message.grouped_id not in media_groups:
                media_groups[message.grouped_id] = {
                    "id": message.id,
                    "text": message.text or "",
                    "photos": [],
                    "date": str(message.date),
                    "raw": message
                }
            
            if has_photo:
                media_groups[message.grouped_id]["photos"].append(message.media)
            
            # Ambil caption (biasanya cuma satu mesej dalam album ada text)
            if message.text and not media_groups[message.grouped_id]["text"]:
                media_groups[message.grouped_id]["text"] = message.text
        
        else:
            # Mesej biasa (bukan album)
            if message.text or has_photo:
                messages.append({
                    "id": message.id,
                    "text": message.text or "",
                    "has_photo": has_photo,
                    "photos": [message.media] if has_photo else [],
                    "raw": message,
                    "date": str(message.date)
                })

    # Masukkan album yang dah di-group tadi ke dalam list utama
    for g_id in media_groups:
        messages.append(media_groups[g_id])

    await client.disconnect()
    # Sort balik ikut ID supaya susunan mesej tak berterabur
    return sorted(messages, key=lambda x: x["id"])
