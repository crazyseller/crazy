import os
import random
import cloudscraper
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

app = Flask(__name__, template_folder='.')
CORS(app)

TELEGRAM_BOT_TOKEN = "8986935279:AAFjOyHX7fnZRKTqOZudUxyJCQjcu3_ChMk"
TELEGRAM_CHAT_ID = "8435445040"
SMM_API_URL = "https://smmaddaa.in/api/v2"
SMM_API_KEY = "c0a1a59be99f18fbc6728b49c8173d81"

scraper = cloudscraper.create_scraper()
ORDERS_DB = []

def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        scraper.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/order', methods=['POST'])
def place_order():
    data = request.json
    service_name = data.get("serviceName")
    price = data.get("price")
    insta_link = data.get("instaLink")
    
    ref_id = f"CS{random.randint(1000, 9999)}"

    # Send notification to Telegram
    tg_msg = (
        f"🚨 <b>NEW INSTAGRAM ORDER</b> 🚨\n\n"
        f"🆔 <b>Ref ID:</b> {ref_id}\n"
        f"📦 <b>Service:</b> {service_name}\n"
        f"💰 <b>Price:</b> ₹{price}\n"
        f"🔗 <b>Link:</b> {insta_link}"
    )
    send_telegram_message(tg_msg)

    ORDERS_DB.append({"ref_id": ref_id, "service": service_name, "link": insta_link, "status": "Processing"})
    return jsonify({"status": "success", "ref_id": ref_id})

@app.route('/add-funds', methods=['POST'])
def add_funds():
    data = request.json
    utr_id = data.get("utrId")
    
    tg_msg = (
        f"💳 <b>NEW FUND ADD REQUEST</b> 💳\n\n"
        f"🔢 <b>UTR ID:</b> {utr_id}"
    )
    send_telegram_message(tg_msg)
    
    return jsonify({"status": "success", "message": "Funds verification submitted!"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
