from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import random

app = Flask(__name__)
CORS(app)

SMM_API_KEY = "59ebc87f01ec0285a4f05839ee9e2cc5"
SMM_API_URL = "https://smmaddaa.in/api/v2"
BOT_TOKEN = "8986935279:AAFjOyHX7fnZRKTqOZudUxyJCQjcu3_ChMk"
CHAT_ID = "8435445040"

@app.route('/order', methods=['POST'])
def handle_order():
    data = request.json
    service_id = data.get('serviceId')
    quantity = int(data.get('quantity', 0))
    customer_price = float(data.get('price', 0))
    package_name = data.get('packageName')
    insta_link = data.get('instaLink')
    txn_id = data.get('txnId')

    ref_id = f"CS-{random.randint(1000, 9999)}"

    try:
        # 1. Fetch SMM Balance
        bal_res = requests.get(f"{SMM_API_URL}?key={SMM_API_KEY}&action=balance").json()
        smm_balance = float(bal_res.get('balance', 0))

        # 2. Fetch SMM Services to get Original Cost
        services_res = requests.get(f"{SMM_API_URL}?key={SMM_API_KEY}&action=services").json()
        original_cost = 0.0

        for service in services_res:
            if str(service.get('service')) == str(service_id):
                rate_per_1k = float(service.get('rate', 0))
                original_cost = (rate_per_1k / 1000) * quantity
                break

        profit = customer_price - original_cost

        # 3. Check Low Balance Warning
        if smm_balance < original_cost:
            warn_msg = (
                f"⚠️ *LOW SMM BALANCE WARNING!* ⚠️\n\n"
                f"Order Cost: ₹{original_cost:.2f}\n"
                f"SMM Balance: ₹{smm_balance:.2f}\n"
                f"👉 *Fund shortage! Add balance in SMM Panel.*"
            )
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": warn_msg, "parse_mode": "Markdown"}
            )

        # 4. Telegram Message with Price & Profit Comparison
        smm_order_url = f"{SMM_API_URL}?key={SMM_API_KEY}&action=add&service={service_id}&link={insta_link}&quantity={quantity}"
        
        text_msg = (
            f"🚨 *NEW ORDER RECEIVED* 🚨\n\n"
            f"🆔 *Ref ID:* `{ref_id}`\n"
            f"📦 *Package:* {package_name}\n"
            f"🔗 *Link:* {insta_link}\n"
            f"🔢 *UTR:* `{txn_id}`\n\n"
            f"--- 💰 *PROFIT COMPARISON* ---\n"
            f"💵 Customer Paid: ₹{customer_price}\n"
            f"📉 SMM Cost: ₹{original_cost:.2f}\n"
            f"📈 *Your Profit:* ₹{profit:.2f}\n\n"
            f"💳 *SMM Balance:* ₹{smm_balance:.2f}"
        )

        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Accept & Start Order", "url": smm_order_url}
            ]]
        }

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text_msg,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            }
        )

        return jsonify({"success": True, "refId": ref_id}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
