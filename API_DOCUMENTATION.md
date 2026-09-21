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
  "qr_image_url": "https://ss-empire-gateway.onrender.com/api/qr-image/TXN1789924627C92E",
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

const GATEWAY = 'https://ss-empire-gateway.onrender.com';

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

GATEWAY = "https://ss-empire-gateway.onrender.com"
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
curl -X POST https://ss-empire-gateway.onrender.com/api/create-order \
     -H "Content-Type: application/json" \
     -d '{"amount": "50", "customer_name": "Bunny"}'

# 2. Check Status
curl -X POST https://ss-empire-gateway.onrender.com/api/check-status \
     -H "Content-Type: application/json" \
     -d '{"order_id": "TXN1789924627C92E"}'
```

---

## 🤖 Method 1 (Recommended): Direct Discord Bot REST API Integration

Whenever a customer payment is confirmed (**`status = SUCCESS`** via bank polling, UTR verification, webhook callback, or admin simulator), the SS EMPIRE Payment Gateway calls Discord's official REST API using the Bot Token. 

This posts the proof directly into the Discord channel **AS OUR BOT (Nayumi 🎀)** with an `@everyone` tag and verified embed — without relying on any local bot server or suspended Render endpoints!

### API Endpoint:
* **Endpoint:** `POST https://discord.com/api/v10/channels/<PROOF_CHANNEL_ID>/messages`
* **Headers:**
  ```http
  Authorization: Bot <DISCORD_BOT_TOKEN>
  Content-Type: application/json
  ```

### Payload Body:
```json
{
  "content": "@everyone 📢 **New Payment Received!** ₹100 from **Rahul** (Bank UTR: `760366829987`)",
  "embeds": [
    {
      "title": "💎 New Payment Received & Verified!",
      "description": "🔥 **A new payment has been successfully received and verified!**\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n👤 **Customer:** **Rahul**\n💰 **Amount Received:** `₹100`\n🏦 **Bank 12-Digit UTR:** `760366829987`\n🆔 **Order ID:** `TXN178998237745E1`\n⚡ **Gateway:** SS EMPIRE UPI Instant Gateway\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
      "color": 65406,
      "footer": {
        "text": "Nayumi 🎀 • Official Payment Proof"
      }
    }
  ],
  "allowed_mentions": {
    "parse": ["everyone", "users", "roles"]
  }
}
```

### Test Proof Endpoint:
To send a live test proof to your Discord channel at any time:
```bash
curl -X POST https://ss-empire-gateway.onrender.com/api/test-discord-bot-webhook \
     -H "Content-Type: application/json" \
     -d '{"order_id": "TEST_PROOF_101", "amount": "100", "utr": "760366829987", "customer_name": "Test User", "remark": "Discord_Test"}'
```


