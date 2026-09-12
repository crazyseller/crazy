from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import random

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8986935279:AAFjOyHX7fnZRKTqOZudUxyJCQjcu3_ChMk"
CHAT_ID = "8435445040"
SMM_API_KEY = "38f043592c2e479b5a70a51b7aada85c"
SMM_API_URL = "https://smmaddaa.in/api/v2"

# Local Storage (In-memory)
pending_orders = {}
chat_messages = {}

def get_smm_balance():
    try:
        res = requests.post(SMM_API_URL, data={'key': SMM_API_KEY, 'action': 'balance'}, timeout=5)
        data = res.json()
        return float(data.get('balance', 0.0))
    except Exception:
        return 0.0

@app.route('/', methods=['GET'])
def home():
    return "CRAZY SELLER Backend is Active!"

@app.route('/order', methods=['POST'])
def handle_order():
    data = request.json or {}
    package_name = data.get('packageName', 'N/A')
    price = float(data.get('price', 0.0))
    insta_link = str(data.get('instaLink', 'N/A')).strip()
    txn_id = str(data.get('txnId', 'N/A')).strip()
    service_id = str(data.get('serviceId', 'N/A')).strip()
    quantity = int(data.get('quantity', 1000))
    
    ref_id = f"CS{random.randint(1000, 9999)}"
    smm_cost = round(price * 0.165, 2)
    profit = round(price - smm_cost, 2)
    smm_balance = get_smm_balance()

    # Save details
    pending_orders[ref_id] = {
        "service_id": service_id,
        "link": insta_link,
        "quantity": quantity,
        "price": price
    }

    text_msg = (
        f"🚨 NEW ORDER RECEIVED 🚨\n\n"
        f"🆔 Ref ID: {ref_id}\n"
        f"📦 Package: {package_name} (ID: {service_id})\n"
        f"🔗 Link: {insta_link}\n"
        f"🔢 UTR: {txn_id}\n\n"
        f"--- 💰 PROFIT COMPARISON ---\n"
        f"💵 Customer Paid: ₹{price:.2f}\n"
        f"📉 SMM Cost: ₹{smm_cost:.2f}\n"
        f"📈 Your Profit: ₹{profit:.2f}\n\n"
        f"💳 SMM Balance: ₹{smm_balance:.2f}"
    )

    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text_msg,
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "✅ Accept", "callback_data": f"accept_{ref_id}"},
                    {"text": "❌ Reject", "callback_data": f"reject_{ref_id}"}
                ]
            ]
        },
        "disable_web_page_preview": True
    }

    try:
        requests.post(telegram_url, json=payload, timeout=8)
        return jsonify({"status": "success", "refId": ref_id}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = request.json or {}

    # Handle Button Clicks
    if "callback_query" in update:
        callback = update["callback_query"]
        callback_id = callback.get("id")
        data = callback.get("data", "")
        message_id = callback["message"]["message_id"]
        chat_id = callback["message"]["chat"]["id"]
        original_text = callback["message"].get("text", "")

        # 1. First notify Telegram that button click was received (Prevents button loading error)
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": callback_id})

        if data.startswith("accept_"):
            ref_id = data.replace("accept_", "")
            order = pending_orders.get(ref_id)
            
            if order:
                try:
                    smm_res = requests.post(SMM_API_URL, data={
                        'key': SMM_API_KEY,
                        'action': 'add',
                        'service': order['service_id'],
                        'link': order['link'],
                        'quantity': order['quantity']
                    }, timeout=10).json()
                    
                    if 'order' in smm_res:
                        status_text = f"\n\n🟢 STATUS: Approved & Placed on SMM Addaa!\n🎯 SMM Order ID: {smm_res['order']}"
                    else:
                        err_msg = smm_res.get('error', 'Unknown Error')
                        status_text = f"\n\n⚠️ SMM REJECTED: {err_msg}"
                except Exception as e:
                    status_text = f"\n\n⚠️ SMM Error: {str(e)}"
                
                # Cleanup
                del pending_orders[ref_id]
            else:
                status_text = "\n\n⚠️ SERVER EXPIRED: Render app slept/restarted. Re-check on SMM manually!"

            # Edit Original Telegram Message
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": original_text + status_text
            })

        elif data.startswith("reject_"):
            ref_id = data.replace("reject_", "")
            if ref_id in pending_orders:
                del pending_orders[ref_id]

            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": original_text + "\n\n🔴 STATUS: Rejected by Admin!"
            })

    # Handle Live Chat Replies from Admin
    elif "message" in update and "reply_to_message" in update["message"]:
        msg = update["message"]
        reply_to = msg["reply_to_message"].get("text", "")
        admin_text = msg.get("text", "")
        
        if "💬 Live Chat (" in reply_to:
            try:
                session_id = reply_to.split("💬 Live Chat (")[1].split(")")[0]
                if session_id not in chat_messages:
                    chat_messages[session_id] = []
                chat_messages[session_id].append({"sender": "admin", "text": admin_text})
            except Exception:
                pass

    return jsonify({"status": "ok"}), 200

@app.route('/send-admin', methods=['POST'])
def send_admin():
    data = request.json or {}
    session_id = data.get('sessionId')
    message = data.get('message')
    if session_id not in chat_messages:
        chat_messages[session_id] = []
    chat_messages[session_id].append({"sender": "user", "text": message})
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
        "chat_id": CHAT_ID,
        "text": f"💬 Live Chat ({session_id}):\n{message}"
    })
    return jsonify({"status": "sent"})

@app.route('/get-messages/<session_id>', methods=['GET'])
def get_messages(session_id):
    messages = chat_messages.get(session_id, [])
    return jsonify({"messages": messages})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
