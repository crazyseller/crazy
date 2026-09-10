from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import random
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8986935279:AAFjOyHX7fnZRKTqOZudUxyJCQjcu3_ChMk"
CHAT_ID = "8435445040"
bot = telebot.TeleBot(BOT_TOKEN)

# SMM Panel API Details (smmaddaa.in)
SMM_API_KEY = "38f043592c2e479b5a70a51b7aada85c"
SMM_API_URL = "https://smmaddaa.in/api/v2"

# Pending orders temporarily stored in memory
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
    return "CRAZY SELLER Backend Running Successfully!"

# --- ORDER HANDLING ---
@app.route('/order', methods=['POST'])
def handle_order():
    data = request.json or {}
    
    package_name = data.get('packageName', 'N/A')
    price = float(data.get('price', 0.0))
    insta_link = data.get('instaLink', 'N/A')
    txn_id = data.get('txnId', 'N/A')
    service_id = data.get('serviceId', 'N/A')
    quantity = data.get('quantity', 1000)
    
    ref_id = f"CS-{random.randint(1000, 9999)}"

    # Cost & Profit Calculations
    smm_cost = round(price * 0.165, 2)
    profit = round(price - smm_cost, 2)
    smm_balance = get_smm_balance()

    # Save to pending orders dictionary until Accept is clicked
    pending_orders[ref_id] = {
        "service_id": service_id,
        "link": insta_link,
        "quantity": quantity,
        "price": price
    }

    message_text = (
        f"🚨 *NEW ORDER RECEIVED* 🚨\n\n"
        f"🆔 *Ref ID:* {ref_id}\n"
        f"📦 *Package:* {package_name} (Service ID: {service_id})\n"
        f"🔗 *Link:* {insta_link}\n"
        f"🔢 *UTR:* `{txn_id}`\n\n"
        f"--- 💰 *PROFIT COMPARISON* ---\n"
        f"💵 *Customer Paid:* ₹{price:.2f}\n"
        f"📉 *SMM Cost:* ₹{smm_cost:.2f}\n"
        f"📈 *Your Profit:* ₹{profit:.2f}\n\n"
        f"💳 *SMM Balance:* ₹{smm_balance:.2f}"
    )

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Accept Order", callback_data=f"accept_{ref_id}"),
        InlineKeyboardButton("❌ Reject Order", callback_data=f"reject_{ref_id}")
    )

    try:
        bot.send_message(CHAT_ID, message_text, parse_mode="Markdown", reply_markup=markup)
        return jsonify({"status": "success", "refId": ref_id}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- TELEGRAM CALLBACK BUTTONS (ACCEPT / REJECT) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    data = call.data
    
    if data.startswith("accept_"):
        ref_id = data.replace("accept_", "")
        order = pending_orders.get(ref_id)
        
        if order:
            try:
                # Direct API Call to SMM Addaa Panel
                smm_response = requests.post(SMM_API_URL, data={
                    'key': SMM_API_KEY,
                    'action': 'add',
                    'service': order['service_id'],
                    'link': order['link'],
                    'quantity': order['quantity']
                }, timeout=8).json()
                
                if 'order' in smm_response:
                    order_id = smm_response.get('order')
                    status_text = f"\n\n🟢 *STATUS:* Order Placed on SMM Addaa! (SMM Order ID: {order_id})"
                else:
                    error_msg = smm_response.get('error', 'Unknown Error')
                    status_text = f"\n\n⚠️ *SMM API ERROR:* {error_msg}"
            except Exception as e:
                status_text = f"\n\n⚠️ *STATUS:* Connection Error: {str(e)}"
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=call.message.text + status_text,
                parse_mode="Markdown"
            )
            del pending_orders[ref_id]

    elif data.startswith("reject_"):
        ref_id = data.replace("reject_", "")
        if ref_id in pending_orders:
            del pending_orders[ref_id]
            
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text + "\n\n🔴 *STATUS:* Order Rejected by Admin!",
            parse_mode="Markdown"
        )

# --- CHATBOT BACKEND ENDPOINTS ---
@app.route('/send-admin', methods=['POST'])
def send_admin():
    data = request.json or {}
    session_id = data.get('sessionId')
    message = data.get('message')
    
    if session_id not in chat_messages:
        chat_messages[session_id] = []
    
    chat_messages[session_id].append({"sender": "user", "text": message})
    
    bot.send_message(CHAT_ID, f"💬 *Live Chat ({session_id}):*\n{message}", parse_mode="Markdown")
    return jsonify({"status": "sent"})

@app.route('/get-messages/<session_id>', methods=['GET'])
def get_messages(session_id):
    messages = chat_messages.get(session_id, [])
    return jsonify({"messages": messages})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
