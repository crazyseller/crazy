from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8986935279:AAFjOyHX7fnZRKTqOZudUxyJCQjcu3_ChMk"
CHAT_ID = "8435445040"
bot = telebot.TeleBot(BOT_TOKEN)

# SMM Panel விவரங்கள் (தேவைப்பட்டால் மாற்றவும்)
SMM_API_KEY = "YOUR_SMM_PANEL_API_KEY"  # உங்கள் SMM Panel API Key
SMM_API_URL = "https://smm-panel-domain.com/api/v2"  # உங்கள் SMM Panel URL

# தற்காலிகமாக Orders சேமிக்க (In-Memory Pending Orders)
pending_orders = {}

# SMM Balance அறியும் பகுதி
def get_smm_balance():
    try:
        res = requests.post(SMM_API_URL, data={'key': SMM_API_KEY, 'action': 'balance'})
        data = res.json()
        return float(data.get('balance', 0.0))
    except:
        return 4.66  # API இணைப்பு இல்லையென்றால் இயல்புநிலை மதிப்பு

@app.route('/', methods=['GET'])
def home():
    return "CRAZY SELLER Order Control Backend Live!"

@app.route('/order', methods=['POST'])
def handle_order():
    data = request.json or {}
    
    package_name = data.get('packageName', 'N/A')
    price = float(data.get('price', 0.0))
    insta_link = data.get('instaLink', 'N/A')
    txn_id = data.get('txnId', 'N/A')
    service_id = data.get('serviceId', 'N/A')
    quantity = data.get('quantity', 1000)
    
    ref_id = f"CS-{telebot.telebot.randint(1000, 9999)}"

    # 1. உண்மையான SMM Cost மற்றும் Profit கணக்கீடு (உதாரணத்திற்கு 30% Cost எனக் கணக்கிடப்படுகிறது)
    smm_cost = round(price * 0.30, 2)  # உங்கள் SMM அசல் விலைக்கு ஏற்ப 0.30-ஐ மாற்றிக் கொள்ளலாம்
    profit = round(price - smm_cost, 2)
    smm_balance = get_smm_balance()

    # Order தகவல்களை Pending பட்டியலில் சேமிக்கிறோம் (Accept செய்யும் வரை SMM-க்கு போகாது)
    pending_orders[ref_id] = {
        "service_id": service_id,
        "link": insta_link,
        "quantity": quantity,
        "price": price
    }

    message_text = (
        f"🚨 *NEW ORDER RECEIVED* 🚨\n\n"
        f"🆔 *Ref ID:* {ref_id}\n"
        f"📦 *Package:* {package_name} (ID: {service_id})\n"
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
        return jsonify({"status": "success", "refId": ref_id, "message": "Order Pending Admin Approval"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Telegram-ல் Accept அல்லது Reject பட்டன் அழுத்தும் போது இயங்கும் பகுதி
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    data = call.data
    
    if data.startswith("accept_"):
        ref_id = data.replace("accept_", "")
        order = pending_orders.get(ref_id)
        
        if order:
            # 2. Accept அழுத்தினால் மட்டுமே SMM Panel API-க்கு Request அனுப்பப்படும்
            smm_response = requests.post(SMM_API_URL, data={
                'key': SMM_API_KEY,
                'action': 'add',
                'service': order['service_id'],
                'link': order['link'],
                'quantity': order['quantity']
            }).json()
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=call.message.text + f"\n\n🟢 *STATUS:* Order Accepted & Sent to SMM! (Order ID: {smm_response.get('order', 'Done')})",
                parse_mode="Markdown"
            )
            del pending_orders[ref_id]
        else:
            bot.answer_callback_query(call.id, "Order expired or already processed!")

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
