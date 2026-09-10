from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import random

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8986935279:AAFjOyHX7fnZRKTqOZudUxyJCQjcu3_ChMk"
CHAT_ID = "8435445040"

@app.route('/', methods=['GET'])
def home():
    return "CRAZY SELLER Backend Running Successfully!"

@app.route('/order', methods=['POST'])
def handle_order():
    data = request.json or {}
    
    package_name = data.get('packageName', 'N/A')
    price = data.get('price', 0.0)
    insta_link = data.get('instaLink', 'N/A')
    txn_id = data.get('txnId', 'N/A')
    service_id = data.get('serviceId', 'N/A')
    
    # Generate Random Ref ID
    ref_id = f"CS-{random.randint(1000, 9999)}"
    
    # Calculations (உன் விருப்பத்திற்கு ஏற்ப மாற்றி அமைக்கலாம்)
    try:
        cust_paid = float(price)
    except:
        cust_paid = 0.0
        
    smm_cost = round(cust_paid * 0.165, 2)  # தோராய கணக்கீடு
    profit = round(cust_paid - smm_cost, 2)
    smm_balance = 4.66  # SMM Panel Balance

    message_text = (
        f"🚨 *NEW ORDER RECEIVED* 🚨\n\n"
        f"🆔 *Ref ID:* {ref_id}\n"
        f"📦 *Package:* {package_name} (ID: {service_id})\n"
        f"🔗 *Link:* {insta_link}\n"
        f"🔢 *UTR:* `{txn_id}`\n\n"
        f"--- 💰 *PROFIT COMPARISON* ---\n"
        f"💵 *Customer Paid:* ₹{cust_paid:.1f}\n"
        f"📉 *SMM Cost:* ₹{smm_cost}\n"
        f"📈 *Your Profit:* ₹{profit}\n\n"
        f"💳 *SMM Balance:* ₹{smm_balance}"
    )

    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    try:
        requests.post(telegram_url, json={
            "chat_id": CHAT_ID,
            "text": message_text,
            "parse_mode": "Markdown"
        })
        return jsonify({"status": "success", "refId": ref_id}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
