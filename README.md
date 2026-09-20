# 🚀 TerminalX & UPI Payment Gateway System

Ek complete, modern, aur dynamic **UPI Payment Gateway Web Application** jo aapke TerminalX account (`terminalx999.space`) aur Direct UPI merchant payments ko handle karta hai.

---

## ⚡ Quick Start (1 Click Me Run Karein)

1. Apne folder me **`start.bat`** par double click karein.
2. Server start ho jayega aur aapke browser me `http://127.0.0.1:5000` automatically open ho jayega!

---

## 🌟 Key Features (Is Gateway Me Kya Kya Hai)

1. **Customer Checkout Portal (`/`)**:
   - Customer apna naam, mobile aur amount daal kar **"Generate UPI QR & Pay"** dabata hai.
   - Dynamic UPI QR Code generate hota hai (Paytm, PhonePe, Google Pay, BHIM, Cred sabse payable).
   - Real-time **10 minute countdown timer** aur payment confirmation ke liye auto-polling chalti hai.
   - Mobile users ke liye direct 1-tap app opening buttons (**Google Pay**, **PhonePe**, **Paytm**).
   - Payment hote hi automatic **Success Receipt** popup hota hai with UTR & Confetti animation.

2. **Shareable Payment Links (`/pay`)**:
   - Kisi bhi customer ya product ke liye direct link generate karein (jaise: `http://localhost:5000/pay?amount=299&desc=VIP+Access`).
   - Ek-click me link copy karke WhatsApp/Telegram/Discord par bhejein.

3. **Live Transactions Log**:
   - Har order ka record (Order ID, Amount, Customer, Status, UTR, Timestamp) automatically save hota hai.
   - Status: `PENDING`, `SUCCESS`, `FAILED`.

4. **Dual-Engine Architecture (Smart Fallback)**:
   - **Engine 1 (TerminalX API)**: Aapke `terminalx999.space` account se connected hai (Token: `79ed535e58c8352bc5e9324130e39cc1`). Jaise hi Suyash/admin aapka plan activate karega, payments unhi ke system se auto-route hone lagenge.
   - **Engine 2 (Direct UPI Intent)**: Agar TerminalX plan expired hai, toh yeh fail hone ke bajaye turant dynamic UPI QR code generate karta hai aapke Paytm/PhonePe UPI ID ke saath taaki business aur testing na ruke!

5. **Settings & Diagnostics**:
   - UI se hi aap apna **TerminalX Token**, **Merchant UPI ID**, aur **Routing Mode** badal sakte hain.
   - **"Run Token Diagnostics"** button se live check kar sakte hain ki TerminalX server aur token active hai ya nahi.

---

## 📂 File Structure

```
PAYMENT GATEWAY/
├── app.py              # Flask Backend Server (APIs & Order routing)
├── config.json         # Settings & API Credentials
├── transactions.json   # Order database
├── start.bat           # 1-Click launcher
├── README.md           # Documentation
└── static/
    ├── index.html      # Main Gateway Dashboard
    ├── pay.html        # Customer Payment Page
    ├── style.css       # Premium Dark Fintech UI styling
    └── app.js          # QR Code generation, polling & animations
```

---

## 💡 Important Note on TerminalX Account

Aapke panel par login karne par account status **Deactive** aur plan expire date **2026-09-18** mili.
- Aap seller ko yeh bol sakte hain: *"Bhai token test kiya toh PLAN_EXPIRED_PLEASE_RENEW bol raha hai, isko panel se active kar do."*
- Jab tak vo active nahi karte, tab tak aapka gateway **Direct UPI Mode** aur **Sandbox Test Mode** me 100% chalega!
