const express = require('express');
const cors = require('cors');
const TelegramBot = require('node-telegram-bot-api');

const app = express();
app.use(express.json());
app.use(cors());

// --- CONFIGURATIONS ---
const TELEGRAM_BOT_TOKEN = "8986935279:AAFjOyHX7fnZRKTqOZudUxyJCQjcu3_ChMk";
const ADMIN_CHAT_ID = "8435445040"; // Unoda Telegram Admin ID
const SMM_API_URL = "https://smmaddaa.in/api/v2";
const SMM_API_KEY = "85cceded0707c2e48ede121db223869f";

const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });

// Temporary storage for active sessions & orders
let activeSessions = {}; 

// 1. Order Endpoint (Website-l irunthu order varum pothu)
app.post('/order', async (req, res) => {
    try {
        const { packageName, serviceId, quantity, price, instaLink, txnId } = req.body;

        const message = `🚨 **NEW SMM ORDER RECEIVED!**\n\n` +
                        `📦 Service: ${packageName}\n` +
                        `🆔 Service ID: ${serviceId}\n` +
                        `🔢 Qty: ${quantity}\n` +
                        `💰 Price: ₹${price}\n` +
                        `🔗 Link: ${instaLink}\n` +
                        `💳 UTR ID: \`${txnId}\``;

        const keyboard = {
            inline_keyboard: [
                [
                    { text: "✅ Accept & Push to SMM", callback_data: `accept_${serviceId}_${quantity}_${encodeURIComponent(instaLink)}_${txnId}` },
                    { text: "❌ Reject", callback_data: `reject_${txnId}` }
                ]
            ]
        };

        await bot.sendMessage(ADMIN_CHAT_ID, message, { parse_mode: 'Markdown', reply_markup: keyboard });
        res.json({ status: "success", message: "Order sent to Telegram for verification!" });
    } catch (error) {
        console.error(error);
        res.status(500).json({ status: "error", message: error.message });
    }
});

// 2. Live Chat Endpoint (Website chat irunthu message varum pothu)
app.post('/send-admin', async (req, res) => {
    try {
        const { sessionId, message } = req.body;
        activeSessions[sessionId] = ADMIN_CHAT_ID; // Map session to admin

        const chatMsg = `💬 **Live Support Message**\n👤 Session: \`${sessionId}\`\n✉️ Message: ${message}`;
        await bot.sendMessage(ADMIN_CHAT_ID, chatMsg, { parse_mode: 'Markdown' });
        
        res.json({ status: "success" });
    } catch (error) {
        res.status(500).json({ status: "error" });
    }
});

// Telegram Button Click & Reply Handler
bot.on('callback_query', async (query) => {
    const data = query.data;
    const chatId = query.message.chat.id;
    const messageId = query.message.message_id;

    if (data.startsWith('accept_')) {
        const parts = data.split('_');
        const serviceId = parts[1];
        const quantity = parts[2];
        const instaLink = decodeURIComponent(parts[3]);
        const txnId = parts[4];

        try {
            // SMM API Request-ku payload
            const params = new URLSearchParams();
            params.append('key', SMM_API_KEY);
            params.append('action', 'add');
            params.append('service', serviceId);
            params.append('link', instaLink);
            params.append('quantity', quantity);

            const response = await fetch(SMM_API_URL, {
                method: 'POST',
                body: params
            });
            const smmResult = await response.json();

            if (smmResult.order) {
                bot.editMessageText(`✅ **ORDER ACCEPTED & SENT TO SMM!**\nSMM Order ID: ${smmResult.order}\nUTR: ${txnId}`, {
                    chat_id: chatId,
                    message_id: messageId,
                    parse_mode: 'Markdown'
                });
            } else {
                bot.editMessageText(`⚠️ **Accepted, but SMM Error:** ${JSON.stringify(smmResult)}`, {
                    chat_id: chatId,
                    message_id: messageId,
                    parse_mode: 'Markdown'
                });
            }
        } catch (err) {
            bot.editMessageText(`❌ API Error: ${err.message}`, { chat_id: chatId, message_id: messageId });
        }
    } else if (data.startsWith('reject_')) {
        const txnId = data.split('_')[1];
        bot.editMessageText(`❌ **ORDER REJECTED!**\nUTR: ${txnId} was cancelled by admin.`, {
            chat_id: chatId,
            message_id: messageId,
            parse_mode: 'Markdown'
        });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
