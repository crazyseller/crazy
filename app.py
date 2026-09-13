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
SMM_API_KEY = "c0a1a59be99f18fbc6728b49c8173d81"

scraper = cloudscraper.create_scraper()


def send_telegram_message_with_buttons(text, ref_id):
  try:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # Create Accept and Reject Inline Buttons
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Accept & Send to SMM", "callback_data": f"acc_{ref_id}"},
                {"text": "❌ Reject Order", "callback_data": f"rej_{ref_id}"},
            ]
        ]
    }
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": keyboard,
    }
    scraper.post(url, json=payload, timeout=10)
  except Exception as e:
    print(f"Telegram Error: {e}")


def send_telegram_plain_message(text):
  try:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    scraper.post(url, json=payload, timeout=10)
  except Exception as e:
    print(f"Telegram Error: {e}")


# Temporary storage for pending orders in memory
PENDING_ORDERS = {}


@app.route("/order", methods=["POST"])
def place_order():
  data = request.json
  package_name = data.get("packageName")
  service_id = data.get("serviceId")
  quantity = data.get("quantity")
  price = data.get("price")
  cost = data.get("cost")
  insta_link = data.get("instaLink")
  txn_id = data.get("txnId")

  ref_id = f"CS{random.randint(1000, 9999)}"

  # Store order details temporarily so we can process it when you click Accept
  PENDING_ORDERS[ref_id] = {
      "package_name": package_name,
      "service_id": service_id,
      "quantity": quantity,
      "price": price,
      "cost": cost,
      "insta_link": insta_link,
      "txn_id": txn_id,
  }

  profit = float(price) - float(cost)

  # Send message with buttons (Doesn't go to SMM yet!)
  tg_msg = (
      f"🚨 <b>NEW ORDER VERIFICATION PENDING</b> 🚨\n\n"
      f"🆔 <b>Ref ID:</b> {ref_id}\n"
      f"📦 <b>Package:</b> {package_name}\n"
      f"🔗 <b>Link:</b> {insta_link}\n"
      f"🔢 <b>UTR:</b> {txn_id}\n\n"
      f"--- 💰 <b>PROFIT</b> ---\n"
      f"💵 <b>Paid:</b> ₹{price} | 📉 <b>Cost:</b> ₹{cost}\n"
      f"📈 <b>Profit:</b> ₹{profit:.2f}\n\n"
      f"👉 <i>Check payment UTR in bank and click below:</i>"
  )

  send_telegram_message_with_buttons(tg_msg, ref_id)

  return jsonify(
      {
          "status": "success",
          "refId": ref_id,
          "message": "Order received! Waiting for admin approval.",
      }
  )


# Webhook endpoint for Telegram Button Clicks (Optional/Advanced, requires bot webhook setup or polling)
# NOTE: To make buttons work automatically via webhook, you need to configure Telegram Webhook or handle updates.
# If you just want a simple alert, check below note.


@app.route("/send-admin", methods=["POST"])
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


@app.route("/", methods=["GET"])
def home():
  return "CRAZY SELLER Backend is Live and Running!"


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
