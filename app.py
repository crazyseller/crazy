import os
import random
import cloudscraper
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Updated Credentials as you provided
TELEGRAM_BOT_TOKEN = "8986935279:AAFjOyHX7fnZRKTqOZudUxyJCQjcu3_ChMk"
TELEGRAM_CHAT_ID = "8435445040"
SMM_API_URL = "https://smmaddaa.in/api/v2"
SMM_API_KEY = "c0a1a59be99f18fbc6728b49c8173d81"

scraper = cloudscraper.create_scraper()


def send_telegram_message(text):
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

  smm_status = "Pending"
  smm_error_msg = ""
  smm_balance_text = "N/A"

  try:
    smm_payload = {
        "key": SMM_API_KEY,
        "action": "add",
        "service": service_id,
        "link": insta_link,
        "quantity": quantity,
    }

    response = scraper.post(SMM_API_URL, data=smm_payload, timeout=15)
    raw_text = response.text.strip()

    if raw_text.startswith("<") or "html" in raw_text.lower():
      smm_status = "REJECTED"
      smm_error_msg = "SMM Server returned HTML block (Cloudflare/Error)"
    else:
      try:
        res_json = response.json()
        if "order" in res_json:
          smm_status = f"Success (ID: {res_json['order']})"
        elif "error" in res_json:
          smm_status = "REJECTED"
          smm_error_msg = res_json["error"]
        else:
          smm_status = "REJECTED"
          smm_error_msg = "Unknown JSON response from SMM"
      except Exception:
        smm_status = "REJECTED"
        smm_error_msg = "Invalid JSON format received"

    bal_payload = {"key": SMM_API_KEY, "action": "balance"}
    bal_res = scraper.post(SMM_API_URL, data=bal_payload, timeout=10)
    if not bal_res.text.strip().startswith("<"):
      bal_json = bal_res.json()
      if "balance" in bal_json:
        smm_balance_text = f"₹{bal_json['balance']} {bal_json.get('currency', 'INR')}"

  except Exception as e:
    smm_status = "REJECTED"
    smm_error_msg = str(e)

  profit = float(price) - float(cost)

  tg_msg = (
      f"🚨 <b>NEW ORDER RECEIVED</b> 🚨\n\n"
      f"🆔 <b>Ref ID:</b> {ref_id}\n"
      f"📦 <b>Package:</b> {package_name}\n"
      f"🔗 <b>Link:</b> {insta_link}\n"
      f"🔢 <b>UTR:</b> {txn_id}\n\n"
      f"--- 💰 <b>PROFIT COMPARISON</b> ---\n"
      f"💵 <b>Customer Paid:</b> ₹{price}\n"
      f"📉 <b>SMM Cost:</b> ₹{cost}\n"
      f"📈 <b>Your Profit:</b> ₹{profit:.2f}\n\n"
      f"💳 <b>SMM Balance:</b> {smm_balance_text}\n"
  )

  if smm_status.startswith("Success"):
    tg_msg += f"\n🟢 <b>STATUS:</b> Approved & Placed on SMM Addaa!\n🎯 <b>SMM Order ID:</b> {smm_status.split(': ')[1][:-1]}"
  else:
    tg_msg += f"\n⚠️ <b>SMM REJECTED:</b> {smm_error_msg}"

  send_telegram_message(tg_msg)

  return jsonify(
      {
          "status": "success",
          "refId": ref_id,
          "message": "Order processed and logged successfully!",
      }
  )


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
  send_telegram_message(tg_msg)
  return jsonify({"status": "sent"})


@app.route("/", methods=["GET"])
def home():
  return "CRAZY SELLER Backend is Live and Running!"


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
