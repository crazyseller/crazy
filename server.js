const express = require('express');
const cors = require('cors');
const path = require('path');
const TelegramBot = require('node-telegram-bot-api');
const app = express();
app.use(express.json());
app.use(cors());
app.use(express.static(path.join(__dirname)));

const TELEGRAM_BOT_TOKEN = "8986935279:AAFjOyHX7fnZRKTqOZudUxyJCQjcu3_ChMk";
const ADMIN_CHAT_ID = "8435445040"; 
const SMM_API_URL = "https://smmaddaa.in/api/v2";
const SMM_API_KEY = "c585e62bf7ce7f2dd357695249f96af1";

const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });
let pendingOrders = {};

// Check SMM Balance Endpoint
app.get('/balance', async (req, res) => {
    try {
        const params = new URLSearchParams();
        params.append('key', SMM_API_KEY);
        params.append('action', 'balance');

        const response = await fetch(SMM_API_URL, { method: 'POST', body: params });
        const data = await response.json();
        res.json(data);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Order Endpoint
app.post('/order', async (req, res) => {
    try {
        const { packageName, serviceId, quantity, price, cost, instaLink, txnId } = req.body;
        const refId = "CS" + Math.floor(1000 + Math.random() * 9000);

        pendingOrders[refId] = { packageName, serviceId, quantity, price, cost, instaLink, txnId };

        const profit = (price - (cost || 0)).toFixed(2);
        const message = `🚨 *NEW SMM ORDER RECEIVED!*\n\n` +
                        `🆔 Ref ID: \`${refId}\`\n` +
                        `📦 Package: ${packageName} (₹${price})\n` +                         `🔗 Link: ${instaLink}\n` +
                        `🔢 UTR: \`${txnId}\`\n\n` +
                        `--- 💰 PROFIT COMPARISON ---\n` +
                        `💵 Customer Paid: ₹${price}\n` +
                        `📉 SMM Cost: ₹${cost || 0}\n` +
                        `📈 Your Profit: ₹${profit}`;
        
        const keyboard = {
            inline_keyboard: [
                [
                    { text: "✅ Accept & Push", callback_data: `accept_${refId}` },                     { text: "❌ Reject", callback_data: `reject_${refId}` }
                ]
            ]
        };
        
        await bot.sendMessage(ADMIN_CHAT_ID, message, { parse_mode: 'Markdown', reply_markup: keyboard });
        res.json({ status: "success", message: "Order sent to Telegram!" });
    } catch (error) {
        console.error("Order API Error:", error);
        res.status(500).json({ status: "error", message: error.message });
    }
});

// Live Chat Endpoint
app.post('/send-admin', async (req, res) => {
    try {
        const { sessionId, message } = req.body;
        const chatMsg = `💬 *Live Support Message*\nSession: \`${sessionId}\`\nMessage: ${message}`;
        await bot.sendMessage(ADMIN_CHAT_ID, chatMsg, { parse_mode: 'Markdown' });
        res.json({ status: "success" });
    } catch (error) {
        res.status(500).json({ status: "error", message: error.message });
    }
});

// Telegram Button Click Handler
bot.on('callback_query', async (query) => {
    const actionData = query.data; 
    const chatId = query.message.chat.id;
    const messageId = query.message.message_id;

    const [action, refId] = actionData.split('_');
    const order = pendingOrders[refId];

    if (!order) {
        await bot.answerCallbackQuery(query.id, { text: "⚠️ Order expired or already processed!" });
        return;
    }

    if (action === 'accept') {
        try {
            const params = new URLSearchParams();
            params.append('key', SMM_API_KEY);
            params.append('action', 'add');
            params.append('service', order.serviceId);
            params.append('link', order.instaLink);
            params.append('quantity', order.quantity);

            const response = await fetch(SMM_API_URL, { method: 'POST', body: params });
            const smmResult = await response.json();

            if (smmResult.order) {
                await bot.editMessageText(
                    query.message.text + `\n\n✅ *Status:* ACCEPTED & PUSHED TO SMM!\n🚀 SMM Order ID: \`${smmResult.order}\``,
                    { chat_id: chatId, message_id: messageId, parse_mode: 'Markdown' }
                );
                delete pendingOrders[refId];
            } else {
                await bot.answerCallbackQuery(query.id, { text: "❌ SMM Error: " + (smmResult.error || "Failed") });
                await bot.sendMessage(chatId, `⚠ Failed to push order ${refId} to SMM Addaa: ${JSON.stringify(smmResult)}`);
            }
        } catch (err) {
            console.error("SMM API Fetch Error:", err);
            await bot.answerCallbackQuery(query.id, { text: "❌ Network error connecting to SMM API!" });
        }
    } else if (action === 'reject') {
        await bot.editMessageText(
            query.message.text + `\n\n❌ *Status:* REJECTED by Admin`,
            { chat_id: chatId, message_id: messageId, parse_mode: 'Markdown' }
        );
        delete pendingOrders[refId];
        await bot.answerCallbackQuery(query.id, { text: "Order Rejected." });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
