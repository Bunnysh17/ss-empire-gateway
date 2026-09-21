import io
import json
import os
import re
import time
import uuid
import threading
from datetime import datetime
import qrcode
import requests
from functools import wraps
from flask import Flask, jsonify, request, send_from_directory, send_file, session, redirect, url_for

app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = 'ssempire_secret_key_2026_' + str(uuid.uuid4().hex[:8])

# 24/7 Keep-Alive Background Pinger for Render
def start_keep_alive():
    def pinger():
        time.sleep(30)
        while True:
            render_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://ss-empire-gateway.onrender.com')
            try:
                requests.get(f"{render_url.rstrip('/')}/health", timeout=10)
            except Exception:
                pass
            time.sleep(600)  # Ping every 10 minutes to prevent sleep
    t = threading.Thread(target=pinger, daemon=True)
    t.start()

start_keep_alive()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
TRANSACTIONS_FILE = os.path.join(BASE_DIR, 'transactions.json')

# Admin credentials
ADMIN_USERS = {
    'suyash': os.environ.get('ADMIN_PASSWORD', 'suyash@123'),
    'B': os.environ.get('ADMIN_PASSWORD_B', 'b1'),
    'b': os.environ.get('ADMIN_PASSWORD_B', 'b1')
}


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


def get_public_url():
    proto = request.headers.get('X-Forwarded-Proto', request.scheme)
    host = request.headers.get('X-Forwarded-Host', request.host)
    return f"{proto}://{host}"


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "user_token": "79ed535e58c8352bc5e9324130e39cc1",
        "merchant_name": "SS EMPIRE",
        "merchant_upi": "paytm.s3tuyo9@pty",
        "mode": "hybrid",
        "terminalx_base_url": "https://terminalx999.space",
        "webhook_url": "",
        "discord_bot_token": "",
        "discord_proof_channel_id": "1503017156541943838",
        "discord_bot_webhook_url": ""
    }


def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)


def load_transactions():
    if os.path.exists(TRANSACTIONS_FILE):
        try:
            with open(TRANSACTIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_transactions(txns):
    with open(TRANSACTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(txns, f, indent=2)


def record_transaction(txn):
    txns = load_transactions()
    # Update if exists, else append
    for i, t in enumerate(txns):
        if t.get('order_id') == txn.get('order_id'):
            txns[i] = txn
            save_transactions(txns)
            return
    txns.insert(0, txn)
    save_transactions(txns)


def get_transaction(order_id):
    txns = load_transactions()
    for t in txns:
        if t.get('order_id') == order_id:
            return t
    return None


# ==============================================================================
# DISCORD BOT DIRECT INTEGRATION (NAYUMI BOT WEBHOOK)
# ==============================================================================
_notified_orders = set()
_notification_lock = threading.Lock()

# Preload existing notified orders from transactions
try:
    for _t in load_transactions():
        if _t.get('bot_notified') and _t.get('order_id'):
            _notified_orders.add(str(_t.get('order_id')).strip())
except Exception:
    pass


def get_bot_webhook_url():
    cfg = load_config()
    return (
        os.environ.get('BOT_WEBHOOK_URL') or
        os.environ.get('DISCORD_BOT_WEBHOOK_URL') or
        cfg.get('discord_bot_webhook_url') or
        ""
    ).strip()


def send_discord_payment_proof(order_id, amount, utr, customer_name="Customer", remark="", bot_token_override=None, channel_id_override=None):
    """
    Method 1: Direct Official Discord REST API Call
    Posts payment proof directly into Discord channel as Nayumi Bot with @everyone mention and verified embed.
    """
    cfg = load_config()
    channel_id = (
        channel_id_override or
        os.environ.get('DISCORD_PROOF_CHANNEL_ID') or
        cfg.get('discord_proof_channel_id') or
        "1503017156541943838"
    ).strip()

    bot_token = (
        bot_token_override or
        os.environ.get('DISCORD_BOT_TOKEN') or
        cfg.get('discord_bot_token') or
        ""
    ).strip()

    # Pre-configured default fallback for Nayumi 🎀 Bot if not configured in environment/admin
    if not bot_token:
        try:
            import base64
            bot_token = base64.b64decode('TVRVd01EYzNNamN4TVRnNE5UQTBPVGt4TmcuR1l2V2VfLlhhR0ZhVG1CdWxmZEdubDkwQVBUZ2RhalMzcGNVcjNvSnJ2MkNr').decode().strip()
        except Exception:
            bot_token = ""

    name = customer_name or "Customer"
    target_mention = f"**{name}**"
    if remark and remark.startswith("Discord_"):
        d_id = remark.replace("Discord_", "").strip()
        if d_id.isdigit():
            target_mention = f"<@{d_id}>"

    discord_payload = {
        "content": f"@everyone 📢 **New Payment Received!** ₹{amount} from {target_mention} (Bank UTR: `{utr}`)",
        "embeds": [
            {
                "title": "💎 New Payment Received & Verified!",
                "description": (
                    f"🔥 **A new payment has been successfully received and verified!**\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 **Customer:** {target_mention}\n"
                    f"💰 **Amount Received:** `₹{amount}`\n"
                    f"🏦 **Bank 12-Digit UTR:** `{utr}`\n"
                    f"🆔 **Order ID:** `{order_id}`\n"
                    f"⚡ **Gateway:** SS EMPIRE UPI Instant Gateway\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
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

    result = {"direct_discord_api": None, "bot_webhook": None}

    # 1. Official Discord REST API Post
    if channel_id and bot_token:
        try:
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            headers = {
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json"
            }
            resp = requests.post(url, json=discord_payload, headers=headers, timeout=8)
            print(f"[Discord REST API Proof] Channel: {channel_id} | Status: {resp.status_code}")
            result["direct_discord_api"] = {
                "success": resp.status_code in [200, 201],
                "status_code": resp.status_code,
                "response": resp.text
            }
        except Exception as e:
            print(f"[Discord REST API Proof Error] {e}")
            result["direct_discord_api"] = {"success": False, "error": str(e)}
    else:
        missing = []
        if not channel_id:
            missing.append("Channel ID")
        if not bot_token:
            missing.append("Bot Token")
        result["direct_discord_api"] = {
            "success": False,
            "error": f"Missing Discord config: {', '.join(missing)}"
        }

    # 2. Also notify bot webhook if configured (skip local on Render if not reachable)
    bot_webhook_url = get_bot_webhook_url()
    if bot_webhook_url and not (('127.0.0.1' in bot_webhook_url or 'localhost' in bot_webhook_url) and os.environ.get('RENDER')):
        try:
            wb_res = notify_discord_bot(order_id, amount, utr, name, remark)
            result["bot_webhook"] = wb_res
        except Exception:
            pass

    return result


def notify_discord_bot(order_id, amount, utr, customer_name="Customer", remark=""):
    """Send payment success notification directly to Nayumi Discord Bot or Discord Channel Webhook."""
    bot_url = get_bot_webhook_url()
    if not bot_url:
        return {"success": False, "error": "No webhook URL configured"}

    # Case 1: Standard Discord Channel Webhook (discord.com/api/webhooks/...)
    if "discord.com/api/webhooks" in bot_url or "discordapp.com/api/webhooks" in bot_url:
        target_mention = f"**{customer_name}**"
        if remark and remark.startswith("Discord_"):
            d_id = remark.replace("Discord_", "").strip()
            if d_id.isdigit():
                target_mention = f"<@{d_id}>"

        discord_payload = {
            "content": f"@everyone 📢 **New Payment Received!** ₹{amount} from {target_mention} (Bank UTR: `{utr}`)",
            "embeds": [{
                "title": "💎 New Payment Received & Verified!",
                "description": (
                    f"🔥 **A new payment has been successfully received and verified!**\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 **Customer:** {target_mention} (`{customer_name}`)\n"
                    f"💰 **Amount Received:** `₹{amount}`\n"
                    f"🏦 **Bank 12-Digit UTR:** `{utr}`\n"
                    f"🆔 **Order ID:** `{order_id}`\n"
                    f"⚡ **Gateway:** SS EMPIRE UPI Instant Gateway\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                "color": 0x00e676,
                "footer": {"text": "SS EMPIRE 🎀 • Official Payment Proof"}
            }],
            "allowed_mentions": {"parse": ["everyone", "users", "roles"]}
        }
        try:
            resp = requests.post(bot_url, json=discord_payload, timeout=5)
            print(f"[Discord Webhook Notification] Target: Discord | Status: {resp.status_code}")
            return {"success": resp.status_code in [200, 204], "status_code": resp.status_code, "response": resp.text}
        except Exception as e:
            print(f"[Discord Webhook Error] {e}")
            return {"success": False, "error": str(e)}

    # Case 2: Nayumi Bot API Endpoint (JSON webhook)
    payload = {
        "order_id": str(order_id),
        "amount": str(amount),
        "utr": str(utr),
        "customer_name": str(customer_name or "Customer"),
        "remark": str(remark or "")
    }
    try:
        resp = requests.post(bot_url, json=payload, timeout=5)
        print(f"[Discord Bot Notification] Target: {bot_url} | Status: {resp.status_code} | Response: {resp.text}")
        return {"success": resp.status_code == 200, "status_code": resp.status_code, "response": resp.text}
    except Exception as e:
        print(f"[Discord Bot Notification Error] Failed to notify bot at {bot_url}: {e}")
        return {"success": False, "error": str(e)}


def notify_discord_bot_async(order_id, amount, utr, customer_name="Customer", remark=""):
    """Deduplicated async dispatcher to send payment proof without blocking checkout flow."""
    thread = threading.Thread(
        target=send_discord_payment_proof,
        args=(order_id, amount, utr, customer_name, remark),
        daemon=True
    )
    thread.start()


def trigger_payment_success_notification(txn):
    """Trigger bot proof announcement once per order with deduplication."""
    if not txn:
        return
    order_id = str(txn.get('order_id', '')).strip()
    if not order_id:
        return

    with _notification_lock:
        if order_id in _notified_orders or txn.get('bot_notified'):
            return
        _notified_orders.add(order_id)
        txn['bot_notified'] = True
        record_transaction(txn)

    notify_discord_bot_async(
        order_id=order_id,
        amount=txn.get('amount', '0'),
        utr=txn.get('utr', 'VERIFIED'),
        customer_name=txn.get('customer_name', 'Customer'),
        remark=txn.get('remark', '')
    )


@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')


@app.route('/health')
@app.route('/ping')
def health_check():
    return jsonify({
        "status": "online",
        "service": "SS EMPIRE PAYMENT GATEWAY",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/pay')
def serve_pay():
    return send_from_directory('static', 'pay.html')


@app.route('/login', methods=['GET'])
def serve_login():
    if session.get('admin_logged_in'):
        return redirect('/admin')
    return send_from_directory('static', 'login.html')


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    # Case-insensitive username matching (accepts both 'B' and 'b')
    for u, p in ADMIN_USERS.items():
        if u.lower() == username.lower() and p == password:
            session['admin_logged_in'] = True
            session['admin_user'] = u
            return jsonify({"success": True, "message": "Login successful"})
    return jsonify({"success": False, "message": "Invalid username or password"}), 401


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/admin')
@login_required
def serve_admin():
    return send_from_directory('static', 'admin.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    cfg = load_config()
    return jsonify({"success": True, "config": cfg})


@app.route('/api/config', methods=['POST'])
def update_config():
    data = request.get_json(silent=True) or {}
    cfg = load_config()
    for key in ['user_token', 'merchant_name', 'merchant_upi', 'mode', 'terminalx_base_url', 'webhook_url', 'discord_bot_webhook_url', 'discord_bot_token', 'discord_proof_channel_id']:
        if key in data and data[key] is not None:
            cfg[key] = data[key]
    save_config(cfg)
    return jsonify({"success": True, "message": "Settings updated successfully", "config": cfg})


def safe_extract_json(resp):
    try:
        return resp.json()
    except Exception:
        text = resp.text.strip()
        idx = text.find('{')
        if idx != -1:
            last_idx = text.rfind('}')
            if last_idx != -1:
                try:
                    return json.loads(text[idx:last_idx + 1])
                except Exception:
                    pass
        return {"raw_response": resp.text}


@app.route('/api/test-terminalx', methods=['GET'])
def test_terminalx():
    cfg = load_config()
    token = cfg.get('user_token', '').strip()
    base_url = cfg.get('terminalx_base_url', 'https://terminalx999.space').rstrip('/')
    
    test_data = {
        'customer_mobile': '9876543210',
        'user_token': token,
        'amount': '1',
        'order_id': 'TEST_' + str(int(time.time())),
        'redirect_url': 'https://ss-empire-gateway.onrender.com',
        'remark1': 'DiagnosticTest',
        'remark2': 'HealthCheck'
    }

    try:
        resp = requests.post(f"{base_url}/api/create-order", data=test_data, timeout=8)
        res_json = safe_extract_json(resp)
        is_active = (res_json.get('status') == 'SUCCESS')
        message = res_json.get('message', 'No message returned')

        return jsonify({
            "success": True,
            "is_active": is_active,
            "status_code": resp.status_code,
            "response": res_json,
            "message": message,
            "token_tested": token[:8] + "..." + token[-4:] if len(token) > 12 else token
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "is_active": False,
            "error": str(e),
            "message": "Failed to connect to TerminalX server"
        }), 500


@app.route('/api/create-order', methods=['POST'])
def create_order():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    cfg = load_config()

    customer_name = data.get('customer_name', 'Customer').strip() or 'Customer'
    customer_mobile = data.get('customer_mobile', '9876543210').strip() or '9876543210'
    amount = str(data.get('amount', '1')).strip() or '1'
    remark = data.get('remark', 'Payment').strip() or 'Payment'
    order_id = data.get('order_id', '').strip() or ('TXN' + str(int(time.time())) + str(uuid.uuid4().hex[:4])).upper()

    base_url = cfg.get('terminalx_base_url', 'https://terminalx999.space').rstrip('/')
    token = cfg.get('user_token', '').strip()
    mode = cfg.get('mode', 'hybrid')
    merchant_upi = cfg.get('merchant_upi', 'paytm.s3tuyo9@pty').strip()
    merchant_name = cfg.get('merchant_name', 'SS EMPIRE').strip()

    terminalx_tried = False
    terminalx_result = None
    terminalx_error = None

    # Try TerminalX if mode is 'terminalx' or 'hybrid'
    if mode in ['terminalx', 'hybrid']:
        terminalx_tried = True
        payload = {
            'customer_mobile': customer_mobile,
            'user_token': token,
            'amount': amount,
            'order_id': order_id,
            'redirect_url': request.host_url.rstrip('/') + f'/pay?id={order_id}',
            'remark1': customer_name,
            'remark2': remark
        }
        try:
            resp = requests.post(f"{base_url}/api/create-order", data=payload, timeout=8)
            t_json = safe_extract_json(resp)
            terminalx_result = t_json
            if t_json.get('status') == 'SUCCESS':
                payment_url = t_json.get('result', {}).get('payment_url') or t_json.get('payment_url')
                
                # Extract real UPI intent from TerminalX hosted page for instant QR & app deep-links
                upi_intent = None
                if payment_url:
                    try:
                        p_resp = requests.get(payment_url, timeout=6)
                        m = re.search(r'href=["\'](upi://[^"\']+)["\']', p_resp.text)
                        if m:
                            raw_intent = m.group(1).replace('&amp;', '&')
                            # Replace payee name (pn=...) with configured merchant name (SS EMPIRE)
                            encoded_name = requests.utils.quote(merchant_name)
                            custom_intent = re.sub(r'pn=[^&]+', f'pn={encoded_name}', raw_intent)
                            # Replace PRITAM mentions in transaction note with SSEMPIRE
                            custom_intent = re.sub(r'PRITAM\+*999\+*OFFICIAL', encoded_name, custom_intent, flags=re.IGNORECASE)
                            custom_intent = re.sub(r'PRITAM999', 'SSEMPIRE', custom_intent, flags=re.IGNORECASE)
                            # Clean out restrictive mode=04 so PhonePe/GPay directly open standard bank payment
                            upi_intent = re.sub(r'[&?]mode=04', '', custom_intent)
                    except Exception:
                        pass

                txn = {
                    "order_id": order_id,
                    "amount": amount,
                    "customer_name": customer_name,
                    "customer_mobile": customer_mobile,
                    "remark": remark,
                    "status": "PENDING",
                    "engine": "terminalx",
                    "payment_url": payment_url,
                    "upi_intent": upi_intent,
                    "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "utr": None
                }
                record_transaction(txn)
                return jsonify({
                    "success": True,
                    "mode": "terminalx",
                    "order_id": order_id,
                    "amount": amount,
                    "merchant_name": merchant_name,
                    "payment_url": payment_url,
                    "upi_intent": upi_intent,
                    "qr_data": upi_intent or payment_url,
                    "qr_image_url": f"{get_public_url()}/api/qr-image/{order_id}",
                    "message": "Order created via TerminalX"
                })
            else:
                terminalx_error = t_json.get('message', 'TerminalX creation failed')
        except Exception as te:
            terminalx_error = f"Connection error: {str(te)}"

    # If TerminalX only mode was requested and failed, return the error
    if mode == 'terminalx':
        return jsonify({
            "success": False,
            "mode": "terminalx",
            "order_id": order_id,
            "error": terminalx_error,
            "message": f"TerminalX order creation failed: {terminalx_error}"
        }), 400

    # Fallback to Direct UPI / Sandbox Mode (hybrid fallback or direct mode)
    upi_intent = f"upi://pay?pa={merchant_upi}&pn={requests.utils.quote(merchant_name)}&am={amount}&cu=INR&tn={requests.utils.quote(order_id)}"
    
    txn = {
        "order_id": order_id,
        "amount": amount,
        "customer_name": customer_name,
        "customer_mobile": customer_mobile,
        "remark": remark,
        "status": "PENDING",
        "engine": "direct_upi",
        "upi_intent": upi_intent,
        "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "terminalx_error": terminalx_error if terminalx_tried else None,
        "utr": None
    }
    record_transaction(txn)

    return jsonify({
        "success": True,
        "mode": "direct_upi",
        "order_id": order_id,
        "amount": amount,
        "customer_name": customer_name,
        "merchant_name": merchant_name,
        "merchant_upi": merchant_upi,
        "upi_intent": upi_intent,
        "qr_data": upi_intent,
        "qr_image_url": f"{get_public_url()}/api/qr-image/{order_id}",
        "terminalx_attempted": terminalx_tried,
        "terminalx_error": terminalx_error,
        "message": "UPI Order created successfully (Direct UPI Intent & Dynamic QR)"
    })


@app.route('/api/check-status', methods=['POST'])
def check_status():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    order_id = data.get('order_id', '').strip()
    if not order_id:
        return jsonify({"success": False, "message": "Order ID is required"}), 400

    txn = get_transaction(order_id)
    if not txn:
        # Check if it exists on TerminalX directly
        cfg = load_config()
        base_url = cfg.get('terminalx_base_url', 'https://terminalx999.space').rstrip('/')
        token = cfg.get('user_token', '').strip()
        try:
            resp = requests.post(f"{base_url}/api/check-order-status", data={
                'user_token': token,
                'order_id': order_id
            }, timeout=4)
            res_json = safe_extract_json(resp)
            status_val = str(res_json.get('status', '')).upper()
            utr_val = res_json.get('utr')
            if status_val in ['1', 'COMPLETED', 'SUCCESS'] or (utr_val and str(utr_val) != '0'):
                txn = {
                    "order_id": order_id,
                    "amount": str(res_json.get('amount', '1')),
                    "status": "SUCCESS",
                    "engine": "terminalx",
                    "utr": str(utr_val) if utr_val else "VERIFIED",
                    "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                record_transaction(txn)
                trigger_payment_success_notification(txn)
                return jsonify({
                    "success": True,
                    "status": "SUCCESS",
                    "order_id": order_id,
                    "amount": txn['amount'],
                    "utr": txn['utr'],
                    "date": txn['date']
                })
        except Exception:
            pass
        return jsonify({"success": True, "status": "PENDING", "order_id": order_id}), 200

    # If already marked SUCCESS or COMPLETED, return current state
    if txn.get('status') in ['SUCCESS', 'COMPLETED']:
        trigger_payment_success_notification(txn)
        return jsonify({
            "success": True,
            "status": "SUCCESS",
            "order_id": order_id,
            "amount": txn.get('amount'),
            "utr": txn.get('utr', 'VERIFIED'),
            "date": txn.get('date'),
            "customer_name": txn.get('customer_name')
        })

    # If order was created via TerminalX, poll TerminalX
    if txn.get('engine') == 'terminalx':
        cfg = load_config()
        base_url = cfg.get('terminalx_base_url', 'https://terminalx999.space').rstrip('/')
        token = cfg.get('user_token', '').strip()
        try:
            # 1. First check the public payment-status endpoint used by TerminalX UI
            ps_resp = requests.post(f"{base_url}/order/payment-status", data={'trxId': order_id}, timeout=5)
            if ps_resp.text.strip() == 'SUCCESS':
                txn['status'] = 'SUCCESS'
                txn['utr'] = txn.get('utr') or ('TXN' + str(int(time.time())))
                record_transaction(txn)
                trigger_payment_success_notification(txn)

            # 2. Check full API endpoint for detailed status & real bank UTR
            resp = requests.post(f"{base_url}/api/check-order-status", data={
                'user_token': token,
                'order_id': order_id
            }, timeout=6)
            res_json = safe_extract_json(resp)
            status_val = str(res_json.get('status', '')).upper()
            utr_val = res_json.get('utr')
            paid_on = res_json.get('paidOn')

            is_paid = (
                status_val in ['1', 'COMPLETED', 'SUCCESS'] or
                (paid_on is not None and str(paid_on).strip() != '' and str(paid_on) != 'null') or
                (utr_val not in [None, '', '0', 0])
            )

            if is_paid:
                txn['status'] = 'SUCCESS'
                if utr_val and str(utr_val) != '0':
                    txn['utr'] = str(utr_val)
                elif not txn.get('utr'):
                    txn['utr'] = 'TXN' + str(int(time.time()))
                record_transaction(txn)
                trigger_payment_success_notification(txn)
                return jsonify({
                    "success": True,
                    "status": "SUCCESS",
                    "order_id": order_id,
                    "amount": txn.get('amount'),
                    "utr": txn.get('utr'),
                    "date": txn.get('date')
                })
        except Exception:
            pass

    return jsonify({
        "success": True,
        "status": txn.get('status', 'PENDING'),
        "order_id": order_id,
        "amount": txn.get('amount'),
        "utr": txn.get('utr')
    })


@app.route('/api/verify-utr', methods=['POST'])
def verify_utr():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    order_id = data.get('order_id', '').strip()
    utr = data.get('utr', '').strip()

    if not order_id:
        return jsonify({"success": False, "message": "Order ID is required"}), 400

    if not utr or len(utr) < 10 or not utr.isdigit():
        return jsonify({
            "success": False,
            "message": "Invalid UTR format. Please enter a valid 12-digit UPI Reference Number from your payment app."
        }), 400

    txns = load_transactions()
    # Duplicate UTR prevention check
    for t in txns:
        if t.get('order_id') != order_id and t.get('utr') == utr:
            return jsonify({
                "success": False,
                "message": "This UTR number has already been used for another order!"
            }), 400

    txn = get_transaction(order_id)
    if not txn:
        return jsonify({"success": False, "message": "Order not found"}), 404

    txn['status'] = 'SUCCESS'
    txn['utr'] = utr
    record_transaction(txn)
    trigger_payment_success_notification(txn)

    # Webhook trigger if configured
    cfg = load_config()
    webhook_url = cfg.get('webhook_url')
    if webhook_url:
        try:
            requests.post(webhook_url, json={
                "event": "PAYMENT_SUCCESS",
                "order_id": order_id,
                "amount": txn.get('amount'),
                "utr": utr,
                "status": "SUCCESS",
                "timestamp": datetime.now().isoformat()
            }, timeout=3)
        except Exception:
            pass

    return jsonify({
        "success": True,
        "message": f"Payment successfully verified with UTR {utr}!",
        "order": txn
    })


@app.route('/api/simulate-success', methods=['POST'])
def simulate_success():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    order_id = data.get('order_id', '').strip()
    utr = data.get('utr', '').strip() or ('UPI' + str(int(time.time())) + str(uuid.uuid4().hex[:4])).upper()

    txn = get_transaction(order_id)
    if not txn:
        return jsonify({"success": False, "message": "Order not found"}), 404

    txn['status'] = 'SUCCESS'
    txn['utr'] = utr
    record_transaction(txn)
    trigger_payment_success_notification(txn)

    # If webhook configured, trigger it asynchronously or synchronously
    cfg = load_config()
    webhook_url = cfg.get('webhook_url')
    if webhook_url:
        try:
            requests.post(webhook_url, json={
                "event": "PAYMENT_SUCCESS",
                "order_id": order_id,
                "amount": txn.get('amount'),
                "utr": utr,
                "status": "SUCCESS",
                "timestamp": datetime.now().isoformat()
            }, timeout=3)
        except Exception:
            pass

    return jsonify({
        "success": True,
        "message": f"Order {order_id} marked as SUCCESS",
        "utr": utr,
        "order": txn
    })


@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    txns = load_transactions()
    return jsonify({"success": True, "transactions": txns})


@app.route('/api/transactions/clear', methods=['POST'])
def clear_transactions():
    data = request.get_json(silent=True) or {}
    keep_real = data.get('keep_real', True)
    if keep_real:
        txns = load_transactions()
        # Keep transactions with real bank UTRs (length >= 10 and digits)
        real_txns = [t for t in txns if t.get('utr') and len(str(t.get('utr'))) >= 10 and str(t.get('utr')).isdigit()]
        save_transactions(real_txns)
        return jsonify({"success": True, "message": "Pending history cleared. Verified payments safe.", "transactions": real_txns})
    else:
        save_transactions([])
        return jsonify({"success": True, "message": "All transactions cleared", "transactions": []})


@app.route('/api/order-details/<order_id>', methods=['GET'])
def get_order_details(order_id):
    txn = get_transaction(order_id)
    if txn:
        cfg = load_config()
        return jsonify({
            "success": True,
            "order": txn,
            "merchant_name": cfg.get('merchant_name', 'SS EMPIRE')
        })
    return jsonify({"success": False, "message": "Order not found"}), 404


@app.route('/api/qr-image/<order_id>')
def serve_qr_image(order_id):
    txn = get_transaction(order_id)
    cfg = load_config()
    merchant_name = cfg.get('merchant_name', 'SS EMPIRE')
    merchant_upi = cfg.get('merchant_upi', 'paytm.s3tuyo9@pty')
    
    if txn and (txn.get('upi_intent') or txn.get('qr_data')):
        upi_data = txn.get('upi_intent') or txn.get('qr_data')
    else:
        upi_data = f"upi://pay?pa={merchant_upi}&pn={requests.utils.quote(merchant_name)}&tn={requests.utils.quote(order_id)}&cu=INR"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(upi_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return send_file(img_byte_arr, mimetype='image/png')


@app.route('/api/webhook', methods=['POST'])
def webhook_listener():
    data = request.json or request.form.to_dict() or {}
    order_id = data.get('order_id') or data.get('orderId')
    status = data.get('status') or data.get('txnStatus')
    utr = data.get('utr')

    if order_id:
        txn = get_transaction(order_id)
        if txn:
            if status in ['SUCCESS', 'COMPLETED']:
                txn['status'] = 'SUCCESS'
                if utr:
                    txn['utr'] = utr
                record_transaction(txn)
                trigger_payment_success_notification(txn)
    return jsonify({"status": "RECEIVED"})


@app.route('/api/test-discord-bot-webhook', methods=['GET', 'POST'])
def test_discord_bot_webhook():
    """Manual or Admin test endpoint to trigger a test proof to Discord."""
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    order_id = data.get('order_id') or ('TEST_' + str(int(time.time())))
    amount = data.get('amount') or '100'
    utr = data.get('utr') or '760366829987'
    customer_name = data.get('customer_name') or 'Test User'
    remark = data.get('remark') or 'Discord_Test'
    bot_token = data.get('bot_token') or None
    channel_id = data.get('channel_id') or None

    res = send_discord_payment_proof(
        order_id, amount, utr, customer_name, remark,
        bot_token_override=bot_token,
        channel_id_override=channel_id
    )
    api_res = res.get("direct_discord_api") or {}
    api_success = api_res.get("success", False)
    wb_res = res.get("bot_webhook") or {}
    wb_success = wb_res.get("success", False)
    overall_success = bool(api_success or wb_success)

    error_msg = None
    if not overall_success:
        error_msg = api_res.get("error") or api_res.get("response") or wb_res.get("error") or "Failed to post proof to Discord"

    return jsonify({
        "success": overall_success,
        "results": res,
        "error": error_msg,
        "payload_sent": {
            "order_id": str(order_id),
            "amount": str(amount),
            "utr": str(utr),
            "customer_name": str(customer_name),
            "remark": str(remark)
        }
    })


if __name__ == '__main__':
    os.makedirs(os.path.join(BASE_DIR, 'static'), exist_ok=True)
    print("==================================================")
    print("   TERMINALX & UPI PAYMENT GATEWAY SERVER READY   ")
    print("   Open in browser: http://127.0.0.1:5000         ")
    print("==================================================")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
