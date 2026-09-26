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
ADMIN_SECRET_PASS = "crazyadmin123"  # Change this password for your mobile admin panel

scraper = cloudscraper.create_scraper()

# Mock Database for testing (Can be upgraded to Firestore/MongoDB easily)
USERS_WALLET = {} # { "user@email.com": balance }
ORDERS_DB = []

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
        res = scraper.post(SMM_API_URL, data=payload, timeout=15)
        data = res.json()
        if "order" in data:
            return str(data["order"])
        elif "error" in data:
            return f"Error: {data['error']}"
    except Exception as e:
        print(f"SMM API Error: {e}")
    return "Failed"

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

@app.route('/order', methods=['POST'])
def place_order():
    data = request.json
    package_name = data.get("packageName")
    service_id = data.get("serviceId")
    quantity = data.get("quantity")
    price = float(data.get("price"))
    cost = float(data.get("cost"))
    insta_link = data.get("instaLink")
    txn_id = data.get("txnId", "N/A")
    user_email = data.get("userEmail", "guest@user.com")

    ref_id = f"CS{random.randint(1000, 9999)}"
    profit = round(price - cost, 2)

    # Check SMM Balance first
    smm_bal = get_smm_balance()
    
    # Place order on SMM Addaa automatically
    smm_order_id = place_smm_order(service_id, insta_link, quantity)
    
    status = "Approved & Placed on SMM Addaa!" if not smm_order_id.startswith("Error") and smm_order_id != "Failed" else "Failed / Low Balance"

    # Format Telegram Message as requested
    tg_msg = (
        f"🚨 <b>NEW ORDER RECEIVED</b> 🚨\n\n"
        f"🆔 <b>Ref ID:</b> {ref_id}\n"
        f"📦 <b>Package:</b> {package_name} (₹{price}) (ID: {service_id})\n"
        f"🔗 <b>Link:</b> {insta_link}\n"
        f"🔢 <b>UTR:</b> {txn_id}\n\n"
        f"--- 💰 <b>PROFIT COMPARISON</b> ---\n"
        f"💵 <b>Customer Paid:</b> ₹{price:.2f}\n"
        f"📉 <b>SMM Cost:</b> ₹{cost:.2f}\n"
        f"📈 <b>Your Profit:</b> ₹{profit:.2f}\n\n"
        f"💳 <b>SMM Balance:</b> ₹{smm_bal:.2f}\n\n"
        f"🟢 <b>STATUS:</b> {status}\n"
        f"🎯 <b>SMM Order ID:</b> {smm_order_id}"
    )

    send_telegram_message(tg_msg)

    # Save to orders database
    order_record = {
        "ref_id": ref_id,
        "package": package_name,
        "link": insta_link,
        "price": price,
        "status": status,
        "smm_id": smm_order_id,
        "user": user_email
    }
    ORDERS_DB.append(order_record)

    return jsonify({"status": "success", "ref_id": ref_id, "smm_id": smm_order_id})

@app.route('/complaint', methods=['POST'])
def handle_complaint():
    data = request.json
    user = data.get("user")
    message = data.get("message")
    
    tg_msg = f"⚠️ <b>NEW COMPLAINT / SUPPORT TICKET</b>\n👤 <b>User:</b> {user}\n💬 <b>Message:</b> {message}"
    send_telegram_message(tg_msg)
    return jsonify({"status": "success"})

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    if data.get("password") == ADMIN_SECRET_PASS:
        return jsonify({"status": "success", "orders": ORDERS_DB, "smm_balance": get_smm_balance()})
    return jsonify({"status": "error", "message": "Invalid Password"}), 401

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
