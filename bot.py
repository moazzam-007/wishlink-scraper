# wishlink_scraper_bot.py (telegram-friendly + render-ready version)
import requests
import re
import os
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")  # optional if you want to restrict only one user

# == Core Logic ==
def get_final_url_from_redirect(start_url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        }
        response = requests.get(start_url, timeout=15, headers=headers, allow_redirects=True)
        return response.url
    except Exception as e:
        return f"Error redirecting: {e}"

def extract_post_id_from_url(url):
    match = re.search(r"/(?:post|reels)/(\d+)", url)
    return match.group(1) if match else None

def get_product_links_from_post(post_id):
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://www.wishlink.com",
        "referer": "https://www.wishlink.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "wishlinkid": "1752163729058-1dccdb9e-a0f9-f088-a678-e14f8997f719",
    }
    api_url = f"https://api.wishlink.com/api/store/getPostOrCollectionProducts?page=1&limit=50&postType=POST&postOrCollectionId={post_id}&sourceApp=STOREFRONT"

    try:
        response = requests.get(api_url, headers=headers)
        data = response.json()
        products = data.get("data", {}).get("products", [])
        return [p["purchaseUrl"] for p in products if "purchaseUrl" in p]
    except Exception as e:
        return [f"Error in API: {e}"]


def process_url_list(text):
    urls = re.findall(r"https?://\S+", text)
    result = []
    for url in urls:
        if "/share/" in url:
            redirected = get_final_url_from_redirect(url)
            result.append(f"🔁 {url} ->\n{redirected}\n")
            continue

        post_id = extract_post_id_from_url(url)
        if not post_id:
            result.append(f"🚫 {url} -> No valid post/reel ID found.\n")
            continue

        links = get_product_links_from_post(post_id)
        formatted_links = "\n".join(links)
        result.append(f"✅ {url} ->\n{formatted_links}\n")
    return "\n".join(result)


def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, data=payload)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.json
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if text.startswith("/start"):
        send_telegram(chat_id, "👋 Welcome! Send me a Wishlink URL (or multiple) to start scraping.")
    else:
        send_telegram(chat_id, "🔍 Processing your links...")
        result = process_url_list(text)
        send_telegram(chat_id, result[:4096])  # Telegram max message size
    return {"ok": True}

@app.route("/")
def home():
    return "✅ Bot is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
