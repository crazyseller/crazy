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
const SMM_API_KEY = "85cceded0707c2e48ede121db223869f";

const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });

let pendingOrders = {};
let activeSessions = {}; // Maps sessionId -> Telegram Chat ID or reverse

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

// 2. Live Chat from Customer to Telegram
app.post('/send-admin', async (req, res) => {
    try {
        const { sessionId, message } = req.body;
        activeSessions[ADMIN_CHAT_ID] = sessionId; // Track current active session

        const chatMsg = `💬 **Live Support Message**\n👤 Session: \`${sessionId}\`\n✉️ Message: ${message}`;
        await bot.sendMessage(ADMIN_CHAT_ID, chatMsg, { parse_mode: 'Markdown' });
        
        res.json({ status: "success" });
    } catch (error) {
        res.status(500).json({ status: "error" });
    }
});

// 3. SMM Balance Check Endpoint for Frontend
app.get('/balance', async (req, res) => {
    try {
        const params = new URLSearchParams();
        params.append('key', SMM_API_KEY);
        params.append('action', 'balance');

        const response = await fetch(SMM_API_URL, { method: 'POST', body: params });
        const result = await response.json();

        res.json({ status: "success", balance: result.balance || "0.00", currency: result.currency || "INR" });
    } catch (err) {
        res.status(500).json({ status: "error", balance: "N/A" });
    }
});

// 4. Telegram Message Handler (For Admin Replies & Callback buttons)
bot.on('message', async (msg) => {
    if (msg.chat.id.toString() === ADMIN_CHAT_ID && msg.reply_to_message) {
        // If admin replies to a message in Telegram, parse session and send back (Simulated or store-based)
        // For simplicity, we can broadcast or use active session mapping
        const repliedText = msg.reply_to_message.text;
        const match = repliedText ? repliedText.match(/Session:\s*`([^`]+)`/) : null;
        
        if (match && match[1]) {
            const targetSession = match[1];
            // Here you can store message in memory to pull via a polling endpoint from frontend if needed!
            console.log(`Admin replied to session ${targetSession}:${msg.text}`);
        }
    }
});

bot.on('callback_query', async (query) => {
    const data = query.data;
    const chatId = query.message.chat.id;
    const messageId = query.message.message_id;

    const [action, refId] = data.split('_');

    if (!pendingOrders[refId]) {
        await bot.answerCallbackQuery(query.id, { text: "⚠️ Order expired!" });
        return;
    }

    const order = pendingOrders[refId];

    if (action === 'accept') {
        try {
            const params = new URLSearchParams();
            params.append('key', SMM_API_KEY);
            params.append('action', 'add');
            params.append('service', order.serviceId);
            params.append('link', order.instaLink);
            params.append('quantity', order.quantity);

            const response = await fetch(SMM_API_URL, { method: 'POST', body: params });
            const result = await response.json();

            if (result.order) {
                await bot.editMessageText(
                    query.message.text + `\n\n✅ **STATUS: ACCEPTED & PUSHED**\n🆔 SMM ID: \`${result.order}\``,
                    { chat_id: chatId, message_id: messageId, parse_mode: 'Markdown' }
                );
            } else {
                await bot.editMessageText(
                    query.message.text + `\n\n❌ **SMM ERROR:** ${result.error || 'Failed'}`,
                    { chat_id: chatId, message_id: messageId, parse_mode: 'Markdown' }
                );
            }
        } catch (err) {
            await bot.answerCallbackQuery(query.id, { text: "❌ API Failed!" });
        }
    } else if (action === 'reject') {
        await bot.editMessageText(
            query.message.text + `\n\n❌ **STATUS: REJECTED**`,
            { chat_id: chatId, message_id: messageId, parse_mode: 'Markdown' }
        );
    }

    delete pendingOrders[refId];
    await bot.answerCallbackQuery(query.id);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
