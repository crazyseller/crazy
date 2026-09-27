const express = require('express');
const cors = require('cors');
const path = require('path');
const TelegramBot = require('node-telegram-bot-api');

const app = express();
app.use(express.json());
app.use(cors());

// Serve HTML frontend directly from root folder
app.use(express.static(path.join(__dirname)));

// --- CONFIGURATIONS ---
const TELEGRAM_BOT_TOKEN = "8986935279:AAFjOyHX7fnZRKTqOZudUxyJCQjcu3_ChMk";
const ADMIN_CHAT_ID = "8435445040"; 
const SMM_API_URL = "https://smmaddaa.in/api/v2";
const SMM_API_KEY = "85cceded0707c2e48ede121db223869f";

const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });

let pendingOrders = {};
let activeSessions = {}; 

// 1. Order Endpoint
app.post('/order', async (req, res) => {
    try {
        const { packageName, serviceId, quantity, price, cost, instaLink, txnId } = req.body;
        const refId = "CS" + Math.floor(1000 + Math.random() * 9000);

        pendingOrders[refId] = { packageName, serviceId, quantity, price, cost, instaLink, txnId };

        const profit = (price - (cost || 0)).toFixed(2);

        const message = `🚨 **NEW SMM ORDER RECEIVED!**\n\n` +
                        `🆔 Ref ID: \`${refId}\`\n` +
                        `📦 Package: ${packageName} (₹${price})\n` +
                        `🔗 Link: ${instaLink}\n` +
                        `🔢 UTR: \`${txnId}\`\n\n` +
                        `--- 💰 PROFIT COMPARISON ---\n` +
                        `💵 Customer Paid: ₹${price}\n` +
                        `📉 SMM Cost: ₹${cost || 0}\n` +
                        `📈 Your Profit: ₹${profit}`;

        const keyboard = {
            inline_keyboard: [
                [
                    { text: "✅ Accept & Push", callback_data: `accept_${refId}` },
                    { text: "❌ Reject", callback_data: `reject_${refId}` }
                ]
            ]
        };

        await bot.sendMessage(ADMIN_CHAT_ID, message, { parse_mode: 'Markdown', reply_markup: keyboard });
        res.json({ status: "success", message: "Order sent to Telegram!" });
    } catch (error) {
        console.error(error);
        res.status(500).json({ status: "error", message: error.message });
    }
});

// 2. Live Chat Endpoint
app.post('/send-admin', async (req, res) => {
    try {
        const { sessionId, message } = req.body;
        activeSessions[sessionId] = ADMIN_CHAT_ID;

        const chatMsg = `💬 **Live Support Message**\n👤 Session: \`${sessionId}\`\n✉️ Message: ${message}`;
        await bot.sendMessage(ADMIN_CHAT_ID, chatMsg, { parse_mode: 'Markdown' });
        
        res.json({ status: "success" });
    } catch (error) {
        res.status(500).json({ status: "error" });
    }
});

// Telegram Button Click Handler
bot.on('callback_query', async (query) => {
    const data = query.data;
    const chatId = query.message.chat.id;
    const messageId = query.message.message_id;

    if (data.startsWith('accept_')) {
        const refId = data.split('_')[1];
        const order = pendingOrders[refId];

        if (!order) {
            await bot.answerCallbackQuery(query.id, { text: "❌ Order data expired or not found!" });
            return;
        }

        try {
            const balanceRes = await fetch(SMM_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ key: SMM_API_KEY, action: 'balance' })
            });
            const balanceData = await balanceRes.json();
            const smmBalance = balanceData.balance ? `₹${balanceData.balance}` : "N/A";

            const smmRes = await fetch(SMM_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({
                    key: SMM_API_KEY,
                    action: 'add',
                    service: order.serviceId,
                    link: order.instaLink,
                    quantity: order.quantity
                })
            });
            const smmData = await smmRes.json();

            if (smmData.order) {
                const updatedMsg = query.message.text + 
                    `\n\n💳 SMM Balance: ${smmBalance}` +
                    `\n🟢 STATUS: Approved & Placed on SMM Addaa!` +
                    `\n🎯 SMM Order ID: ${smmData.order}`;

                await bot.editMessageText(updatedMsg, {
                    chat_id: chatId,
                    message_id: messageId,
                    parse_mode: 'Markdown'
                });
                await bot.answerCallbackQuery(query.id, { text: "✅ Order successfully placed on SMM Addaa!" });
            } else {
                await bot.answerCallbackQuery(query.id, { text: "❌ SMM API Error: " + (smmData.error || "Failed") });
            }
        } catch (err) {
            console.error(err);
            await bot.answerCallbackQuery(query.id, { text: "❌ Network error connecting to SMM API." });
        }
    } 
    else if (data.startsWith('reject_')) {
        const refId = data.split('_')[1];
        const updatedMsg = query.message.text + `\n\n🔴 STATUS: Rejected by Admin`;

        await bot.editMessageText(updatedMsg, {
            chat_id: chatId,
            message_id: messageId,
            parse_mode: 'Markdown'
        });
        await bot.answerCallbackQuery(query.id, { text: "Order rejected." });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
