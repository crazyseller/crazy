import os
import random
import cloudscraper
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

TELEGRAM_BOT_TOKEN = "8986935279:AAFjOyHX7fnZRKTqOZudUxyJCQjcu3_ChMk"
TELEGRAM_CHAT_ID = "8435445040"
SMM_API_URL = "https://smmaddaa.in/api/v2"
# Restored your correct original API Key
SMM_API_KEY = "c0a1a59be99f18fbc6728b49c8173d81"

scraper = cloudscraper.create_scraper()

# Storage for pending orders awaiting click
PENDING_ORDERS = {}

def get_smm_balance():
    try:
        payload = {
            'key': SMM_API_KEY,
            'action': 'balance'
        }
        res = scraper.post(SMM_API_URL, data=payload, timeout=10)
        data = res.json()
        if "balance" in data:
            return float(data["balance"])
    except Exception as e:
        print(f"Balance Fetch Error: {e}")
    return 0.00

def place_smm_order(service_id, link, quantity):
    try:
        payload = {
            'key': SMM_API_KEY,
            'action': 'add',
            'service': service_id,
            'link': link,
            'quantity': quantity
        }
        print(f"Sending to SMM Addaa: {payload}")
        res = scraper.post(SMM_API_URL, data=payload, timeout=15)
        data = res.json()
        print(f"SMM Response: {data}")
        if "order" in data:
            return str(data["order"])
        elif "error" in data:
            return f"Error: {data['error']}"
    except Exception as e:
        print(f"SMM API Error: {e}")
    return "Failed"

def send_telegram_message_with_buttons(text, ref_id):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Accept & Send to SMM", "callback_data": f"acc_{ref_id}"},
                    {"text": "❌ Reject Order", "callback_data": f"rej_{ref_id}"}
                ]
            ]
        }
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        }
        res = scraper.post(url, json=payload, timeout=10)
        print(f"Telegram Button Msg Sent: {res.json()}")
    except Exception as e:
        print(f"Telegram Error: {e}")

def send_telegram_plain_message(text):
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

@app.route('/order', methods=['POST'])
def place_order():
    data = request.json
    package_name = data.get("packageName")
    service_id = data.get("serviceId")
    quantity = data.get("quantity")
    price = float(data.get("price"))
    cost = float(data.get("cost"))
    insta_link = data.get("instaLink")
    txn_id = data.get("txnId")

    ref_id = f"CS{random.randint(1000, 9999)}"

    PENDING_ORDERS[ref_id] = {
        "package_name": package_name,
        "service_id": service_id,
        "quantity": quantity,
        "price": price,
        "cost": cost,
        "insta_link": insta_link,
        "txn_id": txn_id
    }

    profit = price - cost

    tg_msg = (
        f"🚨 <b>NEW ORDER VERIFICATION PENDING</b> 🚨\n\n"
        f"🆔 <b>Ref ID:</b> {ref_id}\n"
        f"📦 <b>Package:</b> {package_name}\n"
        f"🔗 <b>Link:</b> {insta_link}\n"
        f"🔢 <b>UTR:</b> {txn_id}\n\n"
        f"--- 💰 <b>PROFIT</b> ---\n"
        f"💵 <b>Paid:</b> ₹{price:.2f} 
        f"📉 <b>Cost:</b> ₹{cost:.2f}\n"
        f"📈 <b>Profit:</b> ₹{profit:.2f}\n\n"
        f"👉 <i>Check UTR in bank and click below to process:</i>"
    )

    send_telegram_message_with_buttons(tg_msg, ref_id)

    return jsonify({"status": "success", "refId": ref_id, "message": "Order received! Waiting for admin approval."})

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    update = request.json
    print(f"Webhook Received: {update}")
    
    if "callback_query" in update:
        callback = update["callback_query"]
        data = callback["data"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]

        parts = data.split("_")
        action_type = parts[0]
        ref_id = parts[1]

        if ref_id in PENDING_ORDERS:
            order = PENDING_ORDERS[ref_id]

            if action_type == "acc":
                smm_order_id = place_smm_order(order['service_id'], order['insta_link'], order['quantity'])
                current_balance = get_smm_balance()
                profit = order['price'] - order['cost']

                final_msg = (
                    f"🚨 <b>NEW ORDER RECEIVED</b> 🚨\n\n"
                    f"🆔 <b>Ref ID:</b> {ref_id}\n"
                    f"📦 <b>Package:</b> {order['package_name']}\n"
                    f"🔗 <b>Link:</b> {order['insta_link']}\n"
                    f"🔢 <b>UTR:</b> {order['txn_id']}\n\n"
                    f"--- 💰 <b>PROFIT COMPARISON</b> ---\n"
                    f"💵 <b>Customer Paid:</b> ₹{order['price']:.2f}\n"
                    f"📉 <b>SMM Cost:</b> ₹{order['cost']:.2f}\n"
                    f"📈 <b>Your Profit:</b> ₹{profit:.2f}\n\n"
                    f"💳 <b>SMM Balance:</b> ₹{current_balance:.4f} INR\n\n"
                    f"🟢 <b>STATUS: Approved & Placed on SMM Addaa!</b>\n"
                    f"🎯 <b>SMM Order ID:</b> {smm_order_id}"
                )

                send_telegram_plain_message(final_msg)
                del PENDING_ORDERS[ref_id]

            elif action_type == "rej":
                reject_msg = (
                    f"❌ <b>ORDER REJECTED</b>\n\n"
                    f"🆔 <b>Ref ID:</b> {ref_id}\n"
                    f"📦 <b>Package:</b> {order['package_name']}\n"
                    f"🔢 <b>UTR:</b> {order['txn_id']}\n\n"
                    f"🔴 <b>Status:</b> Payment Verification Failed / Rejected."
                )
                send_telegram_plain_message(reject_msg)
                del PENDING_ORDERS[ref_id]

    return jsonify({"status": "ok"})

@app.route('/send-admin', methods=['POST'])
def send_admin():
    data = request.json
    session_id = data.get("sessionId")
    message = data.get("message")
    
    tg_msg = (
        f"💬 <b>LIVE CHAT MESSAGE</b> 💬\n\n"
        f"👤 <b>Session:</b> {session_id}\n"
        f"✉️ <b>Message:</b> {message}"
    )
    send_telegram_plain_message(tg_msg)
    return jsonify({"status": "sent"})

@app.route('/', methods=['GET'])
def home():
    return "CRAZY SELLER Backend is Live and Running!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
