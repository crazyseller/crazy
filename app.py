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

    # Telegram Message Text
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

    # Inline Keyboards / Buttons Setup
    markup = InlineKeyboardMarkup(row_width=2)
    btn_accept = InlineKeyboardButton("✅ Accept", callback_data=f"accept_{ref_id}")
    btn_reject = InlineKeyboardButton("❌ Reject", callback_data=f"reject_{ref_id}")
    markup.add(btn_accept, btn_reject)

    try:
        # Send message with reply_markup
        bot.send_message(
            CHAT_ID, 
            message_text, 
            parse_mode="Markdown", 
            reply_markup=markup,
            disable_web_page_preview=True
        )
        return jsonify({"status": "success", "refId": ref_id}), 200
    except Exception as e:
        print("Telegram Send Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500
