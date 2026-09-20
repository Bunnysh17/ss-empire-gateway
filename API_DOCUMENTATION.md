# ⚡ SS EMPIRE - Payment Gateway API Documentation
### (For Telegram Bots, Discord Bots & Web Applications)

This API allows any Telegram Bot, Discord Bot, or custom app to generate dynamic UPI QR codes and verify live bank payments without opening any web page.

---

## 🌐 Permanent 24/7 Live Cloud Base URL:
```
https://ss-empire-gateway.onrender.com
```
*(Hosted 24/7 on Cloud - Runs without your PC!)*

---

## 📌 Endpoint 1: Create Order & Generate QR
Creates a live order on the SS EMPIRE gateway and returns the UPI deep link + direct QR image URL.

* **Method:** `POST`
* **URL:** `/api/create-order`
* **Headers:** `Content-Type: application/json`

### Request Body (JSON):
```json
{
  "amount": "50",
  "customer_name": "Bunny",
  "customer_mobile": "7579923536",
  "remark": "Discord VIP Pass"
}
```
*(Only `amount` is required. Default mobile: `7579923536`)*

### Success Response (`200 OK`):
```json
{
  "success": true,
  "order_id": "TXN1789924627C92E",
  "amount": "50",
  "merchant_name": "SS EMPIRE",
  "qr_image_url": "http://127.0.0.1:5000/api/qr-image/TXN1789924627C92E",
  "upi_intent": "upi://pay?pa=paytm.s3tuyo9@pty&pn=SS%20EMPIRE&tr=TXN1789924627C92E&tn=SSEMPIRE%20...&am=50.00&cu=INR",
  "message": "Order created via TerminalX"
}
```

---

## 🖼️ Endpoint 2: Direct QR Image (PNG)
Directly returns the PNG image bytes of the dynamic QR code for the given order.

* **Method:** `GET`
* **URL:** `/api/qr-image/<ORDER_ID>`
* **Content-Type:** `image/png`

> **Tip for Bots:** You can pass this URL directly to:
> - **Telegram:** `bot.sendPhoto(chatId, qr_image_url)`
> - **Discord:** `embed.setImage(qr_image_url)` or `embed.set_image(url=qr_image_url)`

---

## 🔍 Endpoint 3: Check Payment Status & Bank UTR
Poll this endpoint every 3–5 seconds to check if the customer has paid.

* **Method:** `POST`
* **URL:** `/api/check-status`
* **Headers:** `Content-Type: application/json`

### Request Body:
```json
{
  "order_id": "TXN1789924627C92E"
}
```

### Response When Paid (`SUCCESS`):
```json
{
  "success": true,
  "status": "SUCCESS",
  "order_id": "TXN1789924627C92E",
  "amount": "50",
  "utr": "234015072629",
  "date": "2026-09-20 22:47:08"
}
```
*(Notice the real 12-digit Bank UTR `234015072629`)*

### Response When Pending:
```json
{
  "success": true,
  "status": "PENDING",
  "order_id": "TXN1789924627C92E",
  "amount": "50",
  "utr": null
}
```

---

## 💻 Developer Code Examples

### 1. Node.js / Discord.js (JavaScript)
```javascript
const axios = require('axios');
const { EmbedBuilder } = require('discord.js');

const GATEWAY = 'http://127.0.0.1:5000';

async function createDiscordPayment(channel, amount, user) {
    // 1. Create order
    const res = await axios.post(`${GATEWAY}/api/create-order`, {
        amount: String(amount),
        customer_name: user.username,
        remark: `DC_${user.id}`
    });

    const data = res.data;
    if (!data.success) return channel.send('Error creating payment order');

    // 2. Send Embed with QR Image
    const embed = new EmbedBuilder()
        .setTitle(`⚡ ${data.merchant_name} — UPI Payment`)
        .setDescription('Scan QR with PhonePe, Paytm, or Google Pay (Savings Account)')
        .setColor(0x00F0FF)
        .addFields(
            { name: '💰 Amount', value: `₹${data.amount}`, inline: true },
            { name: '🆔 Order ID', value: `\`${data.order_id}\``, inline: true }
        )
        .setImage(data.qr_image_url);

    const msg = await channel.send({ embeds: [embed] });

    // 3. Auto-poll status every 3s
    const pollInterval = setInterval(async () => {
        const check = await axios.post(`${GATEWAY}/api/check-status`, { order_id: data.order_id });
        if (check.data.status === 'SUCCESS') {
            clearInterval(pollInterval);
            const successEmbed = new EmbedBuilder()
                .setTitle('✅ Payment Verified!')
                .setColor(0x10B981)
                .setDescription(`Amount: ₹${data.amount}\nBank UTR: \`${check.data.utr}\``);
            msg.edit({ embeds: [successEmbed] });
        }
    }, 3000);
}
```

---

### 2. Python (Telegram Bot / requests)
```python
import time
import requests
import telebot

GATEWAY = "http://127.0.0.1:5000"
bot = telebot.TeleBot("YOUR_BOT_TOKEN")

@bot.message_handler(commands=['pay'])
def handle_pay(message):
    amount = message.text.split()[1] # e.g. /pay 50

    # 1. Create Order
    res = requests.post(f"{GATEWAY}/api/create-order", json={
        "amount": amount,
        "customer_name": message.from_user.first_name,
        "remark": f"TG_{message.from_user.id}"
    }).json()

    order_id = res['order_id']
    qr_url = res['qr_image_url']

    caption = (
        f"⚡ <b>SS EMPIRE UPI Payment</b>\n"
        f"💰 Amount: ₹{amount}\n"
        f"🆔 Order ID: <code>{order_id}</code>\n\n"
        f"📌 Scan with PhonePe / Paytm / GPay"
    )

    sent = bot.send_photo(message.chat.id, qr_url, caption=caption, parse_mode="HTML")

    # 2. Poll for payment
    for _ in range(60): # 3 minutes
        time.sleep(3)
        chk = requests.post(f"{GATEWAY}/api/check-status", json={"order_id": order_id}).json()
        if chk.get('status') == 'SUCCESS':
            bot.reply_to(sent, f"✅ Payment Received! Bank UTR: <code>{chk['utr']}</code>", parse_mode="HTML")
            break

bot.infinity_polling()
```

---

### 3. cURL (Terminal / Postman)
```bash
# 1. Create Order
curl -X POST http://127.0.0.1:5000/api/create-order \
     -H "Content-Type: application/json" \
     -d '{"amount": "50", "customer_name": "Bunny"}'

# 2. Check Status
curl -X POST http://127.0.0.1:5000/api/check-status \
     -H "Content-Type: application/json" \
     -d '{"order_id": "TXN1789924627C92E"}'
```
