import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Ungaloda Correct API Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8986935279:AAFjOyHX7fnZRKTqOZudUxyJCQjcu3_ChMk")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8435445040")

# In-Memory Storage for Chat Messages
chat_messages = {} # session_id: [messages]

@app.route('/', methods=['GET'])
def home():
    return "CRAZY SELLER Backend Running Successfully!"

# Automatic Webhook Activator Route
@app.route('/setup-webhook', methods=['GET'])
def setup_webhook():
    webhook_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url=https://crazy-v97r.onrender.com/webhook"
    res = requests.get(webhook_url).json()
    return jsonify(res)

# 1. WEBSITE-LA IRUNDHU MESSAGE TELEGRAM-KU ANUPPA
@app.route('/send-admin', methods=['POST'])
def send_to_admin():
    try:
        data = request.json
        session_id = data.get("sessionId")
        user_msg = data.get("message")
        user_name = data.get("name", "Customer")

        if session_id not in chat_messages:
            chat_messages[session_id] = []

        chat_messages[session_id].append({"sender": "user", "text": user_msg})

        # Telegram Message Format with Session ID
        tg_text = (
            f"💬 *NEW WEBSITE MESSAGE*\n\n"
            f"👤 *From:* {user_name}\n"
            f"🆔 *Session ID:* `{session_id}`\n"
            f"✉️ *Message:* {user_msg}\n\n"
            f"⚠️ *Note:* Indha message-ku Telegram-la *REPLY* pannunga. Website-la customer-ku reply pogum!"
        )

        tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(tg_url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": tg_text,
            "parse_mode": "Markdown"
        })

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 2. TELEGRAM-LA NEENGA REPLY PANNA WEBSITE-KU VARA (WEBHOOK)
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    try:
        update = request.json
        if "message" in update:
            msg = update["message"]
            
            # Telegram-la neenga Reply panni irundha
            if "reply_to_message" in msg and "text" in msg["reply_to_message"]:
                original_text = msg["reply_to_message"]["text"]
                admin_reply = msg["text"]

                # Original Message-la irundhu Session ID-ai edukkuroom
                if "Session ID:" in original_text:
                    session_id = original_text.split("Session ID:")[1].split("\n")[0].strip().replace("`", "")

                    if session_id in chat_messages:
                        chat_messages[session_id].append({"sender": "admin", "text": admin_reply})

        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 3. WEBSITE-LA NEW MESSAGES FETCH PANNA (POLLING)
@app.route('/get-messages/<session_id>', methods=['GET'])
def get_messages(session_id):
    msgs = chat_messages.get(session_id, [])
    return jsonify({"messages": msgs})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
