from flask import Flask, request, jsonify
from flask_cors import CORS
import cloudscraper
import requests
import random
import json

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8986935279:AAFjOyHX7fnZRKTqOZudUxyJCQjcu3_ChMk"
CHAT_ID = "8435445040"
SMM_API_KEY = "c0a1a59be99f18fbc6728b49c8173d81"
SMM_API_URL = "https://smmadda.com/api/v2"

scraper = cloudscraper.create_scraper()

pending_orders = {}
chat_sessions = {}

def safe_json_response(res):
    try:
        text = res.text.strip()
        if not text or text.startswith('<') or '<html>' in text.lower():
            return {"error": "SMM Server returned HTML block"}
        return res.json()
    except:
        return {"error": "Invalid JSON from SMM"}

@app.route('/order', methods=['POST'])
def handle_order():
    data = request.json or {}
    ref_id = f"CS{random.randint(1000, 9999)}"
    
    pending_orders[ref_id] = {
        "service_id": data.get('serviceId'),
        "link": data.get('instaLink'),
        "quantity": int(data.get('quantity', 100))
    }

    text_msg = (
        f"🚨 NEW ORDER RECEIVED 🚨\n\n🆔 Ref ID: {ref_id}\n"
        f"📦 Package: {data.get('packageName')}\n🔗 Link: {data.get('instaLink')}\n"
        f"🔢 UTR: {data.get('txnId')}\n💵 Paid: ₹{data.get('price')}"
    )

    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
        "chat_id": CHAT_ID, "text": text_msg,
        "reply_markup": {"inline_keyboard": [[{"text": "✅ Accept", "callback_data": f"accept_{ref_id}"}, {"text": "❌ Reject", "callback_data": f"reject_{ref_id}"}]]}
    })
    return jsonify({"status": "success", "refId": ref_id})

@app.route('/send-admin', methods=['POST'])
def send_admin():
    data = request.json or {}
    sid = data.get('sessionId')
    msg = data.get('message')
    if sid not in chat_sessions:
        chat_sessions[sid] = [{"sender": "admin", "text": "Hello Crazy! How can I help?"}]
    chat_sessions[sid].append({"sender": "user", "text": msg})
    
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
        "chat_id": CHAT_ID, "text": f"💬 Chat from User ({sid}):\n{msg}"
    })
    return jsonify({"status": "sent"})

@app.route('/get-chat', methods=['GET'])
def get_chat():
    sid = request.args.get('sessionId')
    messages = chat_sessions.get(sid, [{"sender": "admin", "text": "Welcome to Crazy Seller!"}])
    return jsonify({"messages": messages})

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = request.json or {}
    if "callback_query" in update:
        cb = update["callback_query"]
        data = cb.get("data", "")
        chat_id = cb["message"]["chat"]["id"]
        msg_id = cb["message"]["message_id"]
        orig_text = cb["message"]["text"]

        if data.startswith("accept_"):
            ref_id = data.replace("accept_", "")
            order = pending_orders.get(ref_id)
            if order:
                res = scraper.post(SMM_API_URL, data={
                    'key': SMM_API_KEY, 'action': 'add',
                    'service': order['service_id'], 'link': order['link'], 'quantity': order['quantity']
                })
                smm_res = safe_json_response(res)
                if 'order' in smm_res or 'orderID' in smm_res:
                    status = f"\n\n🟢 Approved! SMM ID: {smm_res.get('order', smm_res.get('orderID'))}"
                else:
                    status = f"\n\n⚠️ Error: {smm_res.get('error', 'Failed')}"
            else:
                status = "\n\n⚠️ Expired/Restarted"
            
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                "chat_id": chat_id, "message_id": msg_id, "text": orig_text + status
            })
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
