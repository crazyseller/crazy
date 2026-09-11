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

    # HTML Format (இது லிங்க்குகளில் உள்ள சிறப்பு எழுத்துக்களால் உடையாது)
    message_text = (
        f"🚨 <b>NEW ORDER RECEIVED</b> 🚨\n\n"
        f"🆔 <b>Ref ID:</b> {ref_id}\n"
        f"📦 <b>Package:</b> {package_name} (ID: {service_id})\n"
        f"🔗 <b>Link:</b> {insta_link}\n"
        f"🔢 <b>UTR:</b> <code>{txn_id}</code>\n\n"
        f"--- 💰 <b>PROFIT COMPARISON</b> ---\n"
        f"💵 <b>Customer Paid:</b> ₹{price:.2f}\n"
        f"📉 <b>SMM Cost:</b> ₹{smm_cost:.2f}\n"
        f"📈 <b>Your Profit:</b> ₹{profit:.2f}\n\n"
        f"💳 <b>SMM Balance:</b> ₹{smm_balance:.2f}"
    )

    # Inline Keyboards / Buttons Setup
    markup = InlineKeyboardMarkup()
    btn_accept = InlineKeyboardButton("✅ Accept", callback_data=f"accept_{ref_id}")
    btn_reject = InlineKeyboardButton("❌ Reject", callback_data=f"reject_{ref_id}")
    markup.row(btn_accept, btn_reject)

    try:
        # Send message using HTML parse_mode
        bot.send_message(
            CHAT_ID, 
            message_text, 
            parse_mode="HTML", 
            reply_markup=markup,
            disable_web_page_preview=True
        )
        return jsonify({"status": "success", "refId": ref_id}), 200
    except Exception as e:
        print("Telegram Send Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500
