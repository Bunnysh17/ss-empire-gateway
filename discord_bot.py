"""
SS EMPIRE - Discord Payment Bot
Generates real UPI QR codes directly inside Discord channels with automatic live payment verification.
"""

import asyncio
import io
import json
import os
import sys
import qrcode
import requests
import discord
from discord.ext import commands
from discord import app_commands

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


cfg = load_config()
GATEWAY_URL = os.environ.get('GATEWAY_URL') or cfg.get('gateway_url') or "https://ss-empire-gateway.onrender.com"
DISCORD_TOKEN = os.environ.get('DISCORD_BOT_TOKEN') or cfg.get('discord_bot_token') or ""

if not DISCORD_TOKEN or DISCORD_TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
    print("=" * 65)
    print(" [!] DISCORD BOT TOKEN MISSING")
    print(" 1. Discord Developer Portal (discord.com/developers/applications) par jao")
    print(" 2. Bot banake uska Token copy karo")
    print(" 3. Us token ko config.json mein 'discord_bot_token' mein daal do")
    print("=" * 65)
    try:
        user_input = input("Paste your Discord Bot Token here (or press Enter to exit): ").strip()
        if user_input:
            DISCORD_TOKEN = user_input
            cfg['discord_bot_token'] = DISCORD_TOKEN
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2)
            print("Token saved successfully in config.json!\n")
        else:
            sys.exit(1)
    except Exception:
        sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=['!', '/'], intents=intents)


def generate_qr_buffer(upi_string):
    """Generate high quality QR code as in-memory PNG buffer"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(upi_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


import re

class PaymentStatusView(discord.ui.View):
    def __init__(self, order_id, amount_str, merchant_name):
        super().__init__(timeout=600)
        self.order_id = order_id
        self.amount_str = amount_str
        self.merchant_name = merchant_name

    @discord.ui.button(label="🔄 Check Payment Status", style=discord.ButtonStyle.primary)
    async def check_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        try:
            resp = requests.post(f"{GATEWAY_URL}/api/check-status", json={"order_id": self.order_id}, timeout=5)
            d = resp.json()
            if d.get('status') in ['SUCCESS', 'COMPLETED']:
                utr = d.get('utr') or 'VERIFIED'
                success_embed = discord.Embed(
                    title="✅ Payment Successful!",
                    description=f"Transaction confirmed directly with bank!",
                    color=0x10b981
                )
                success_embed.add_field(name="💰 Amount Paid", value=f"₹{self.amount_str}", inline=True)
                success_embed.add_field(name="🏦 Bank UTR", value=f"`{utr}`", inline=True)
                success_embed.add_field(name="🆔 Order ID", value=f"`{self.order_id}`", inline=False)
                success_embed.add_field(name="👤 Merchant", value=self.merchant_name, inline=True)
                success_embed.set_footer(text="SS EMPIRE UPI Gateway")

                await interaction.message.edit(embed=success_embed, view=None)
                await interaction.followup.send(f"🎉 Payment verified! Bank UTR: `{utr}`", ephemeral=True)
            else:
                await interaction.followup.send("⏳ Payment not detected yet. Please scan the QR code and pay via your UPI app, then check again.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error checking status: {str(e)}", ephemeral=True)


class PaymentDetailsModal(discord.ui.Modal, title="💳 Enter Payment Details"):
    cust_name = discord.ui.TextInput(
        label="Full Name / आपका नाम",
        placeholder="Apna poora naam likhein (e.g. Bunny Sharma)",
        required=True,
        max_length=50
    )
    cust_mobile = discord.ui.TextInput(
        label="Mobile / WhatsApp Number",
        placeholder="10-digit mobile number (e.g. 9876543210)",
        required=True,
        min_length=10,
        max_length=15
    )
    cust_amount = discord.ui.TextInput(
        label="Amount (INR ₹)",
        placeholder="e.g. 50, 100, 500",
        required=True,
        max_length=10
    )
    cust_note = discord.ui.TextInput(
        label="Payment Note / Purpose (Optional)",
        placeholder="e.g. VIP Subscription, Service Payment",
        required=False,
        max_length=80
    )

    def __init__(self, default_amount=None, default_name=None):
        super().__init__()
        if default_amount:
            self.cust_amount.default = str(default_amount)
        if default_name:
            self.cust_name.default = str(default_name)

    async def on_submit(self, interaction: discord.Interaction):
        clean_mob = re.sub(r'[^0-9]', '', self.cust_mobile.value.strip())
        if len(clean_mob) < 10:
            await interaction.response.send_message("❌ Kripya valid 10-digit mobile number enter karein.", ephemeral=True)
            return

        await interaction.response.defer()
        await process_payment(
            interaction,
            self.cust_amount.value.strip(),
            self.cust_name.value.strip(),
            interaction.user.id,
            customer_mobile=clean_mob,
            note=self.cust_note.value.strip() or "Discord Payment"
        )


class OpenPaymentModalView(discord.ui.View):
    def __init__(self, default_amount=None, author_id=None):
        super().__init__(timeout=300)
        self.default_amount = default_amount
        self.author_id = author_id

    @discord.ui.button(label="💳 Fill Details & Pay Now", style=discord.ButtonStyle.success, emoji="⚡")
    async def open_modal_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.author_id and interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Yeh payment request aapke liye nahi hai. Apna naya payment shuru karne ke liye `/pay` ya `!pay` use karein.", ephemeral=True)
            return
        await interaction.response.send_modal(
            PaymentDetailsModal(default_amount=self.default_amount, default_name=interaction.user.display_name)
        )


async def process_payment(ctx_or_interaction, amount_str, user_name, user_id, customer_mobile="9876543210", note="Discord Payment"):
    try:
        amt = float(amount_str)
        if amt < 1:
            msg = "❌ Minimum payment amount ₹1 hona chahiye."
            if hasattr(ctx_or_interaction, 'followup'):
                await ctx_or_interaction.followup.send(msg, ephemeral=True)
            elif hasattr(ctx_or_interaction, 'response'):
                await ctx_or_interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_interaction.send(msg)
            return
        amt_formatted = f"{amt:.2f}"
    except ValueError:
        msg = "❌ Invalid amount. Example: `/pay 50`"
        if hasattr(ctx_or_interaction, 'followup'):
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        elif hasattr(ctx_or_interaction, 'response'):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    # Call local backend to create live TerminalX order
    try:
        resp = requests.post(f"{GATEWAY_URL}/api/create-order", json={
            "amount": str(int(amt) if amt.is_integer() else amt),
            "customer_name": user_name,
            "customer_mobile": customer_mobile,
            "remark": f"Discord_{user_id}"
        }, timeout=10)
        data = resp.json()
    except Exception as e:
        msg = f"❌ Error creating order: {str(e)}"
        if hasattr(ctx_or_interaction, 'followup'):
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        elif hasattr(ctx_or_interaction, 'response'):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    if not data.get('success'):
        msg = f"❌ Order failed: {data.get('message', 'Unknown error')}"
        if hasattr(ctx_or_interaction, 'followup'):
            await ctx_or_interaction.followup.send(msg, ephemeral=True)
        elif hasattr(ctx_or_interaction, 'response'):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    order_id = data.get('order_id')
    merchant_name = data.get('merchant_name', 'SS EMPIRE')
    upi_intent = data.get('upi_intent') or data.get('qr_data')

    # Generate QR in memory
    qr_buf = generate_qr_buffer(upi_intent)
    qr_file = discord.File(qr_buf, filename=f"qr_{order_id}.png")

    embed = discord.Embed(
        title=f"⚡ {merchant_name} — Instant UPI Payment",
        description="Scan this QR code with **PhonePe**, **Paytm**, **Google Pay**, or **BHIM** to pay.",
        color=0x00f0ff
    )
    embed.add_field(name="👤 Customer", value=f"**{user_name}** (<@{user_id}>)", inline=True)
    embed.add_field(name="📱 Mobile", value=f"`{customer_mobile}`", inline=True)
    embed.add_field(name="💰 Amount to Pay", value=f"**₹{amt_formatted}**", inline=True)
    embed.add_field(name="🆔 Order ID", value=f"`{order_id}`", inline=True)
    embed.add_field(name="📲 Merchant VPA", value="`paytm.s3tuyo9@pty`", inline=False)
    embed.add_field(name="⏳ Status", value="Awaiting Payment (Auto-verifying... 10 Min)", inline=False)
    embed.set_image(url=f"attachment://qr_{order_id}.png")
    embed.set_footer(text="⚠️ Please pay using Bank Savings Account. Credit Cards not supported.")

    view = PaymentStatusView(order_id, amt_formatted, merchant_name)

    if hasattr(ctx_or_interaction, 'followup'):
        sent_msg = await ctx_or_interaction.followup.send(embed=embed, file=qr_file, view=view)
    elif hasattr(ctx_or_interaction, 'response'):
        await ctx_or_interaction.response.send_message(embed=embed, file=qr_file, view=view)
        sent_msg = await ctx_or_interaction.original_response()
    else:
        sent_msg = await ctx_or_interaction.send(embed=embed, file=qr_file, view=view)

    # Start background polling task
    asyncio.create_task(auto_poll_discord(sent_msg, order_id, amt_formatted, merchant_name))


async def auto_poll_discord(message, order_id, amount_str, merchant_name):
    """Polls backend every 3s for 10 minutes until paid"""
    for _ in range(200):  # 200 * 3s = 600s (10 minutes)
        await asyncio.sleep(3)
        try:
            resp = requests.post(f"{GATEWAY_URL}/api/check-status", json={"order_id": order_id}, timeout=5)
            d = resp.json()
            if d.get('status') in ['SUCCESS', 'COMPLETED']:
                utr = d.get('utr') or 'VERIFIED'
                success_embed = discord.Embed(
                    title="✅ Payment Successful!",
                    description=f"Transaction confirmed with bank!",
                    color=0x10b981
                )
                success_embed.add_field(name="💰 Amount Paid", value=f"₹{amount_str}", inline=True)
                success_embed.add_field(name="🏦 Bank UTR", value=f"`{utr}`", inline=True)
                success_embed.add_field(name="🆔 Order ID", value=f"`{order_id}`", inline=False)
                success_embed.add_field(name="👤 Merchant", value=merchant_name, inline=True)
                success_embed.set_footer(text="SS EMPIRE UPI Gateway • Verified")

                await message.edit(embed=success_embed, view=None)
                await message.reply(f"🎉 **Payment Received!** Order `{order_id}` (₹{amount_str}) has been verified. Bank UTR: `{utr}`")
                return
        except Exception:
            pass


@bot.event
async def on_ready():
    print("=" * 55)
    print(f"  🚀 SS EMPIRE DISCORD BOT READY: {bot.user}")
    print("  Commands available: !pay or /pay")
    print("=" * 55)
    try:
        synced = await bot.tree.sync()
        print(f"  Synced {len(synced)} slash command(s).")
    except Exception as e:
        print("  Error syncing slash commands:", e)


@bot.command(name="pay")
async def cmd_pay(ctx, amount: str = None):
    """Command: !pay <amount>"""
    embed = discord.Embed(
        title="⚡ SS EMPIRE UPI Instant Checkout",
        description=(
            "Kripya niche diye gaye button par click karke apna **Naam**, **Mobile Number**, aur **Amount** bharein.\n"
            "Jaise hi aap form submit karenge, turant real-time UPI QR code generate ho jayega!"
        ),
        color=0xff1744
    )
    if amount:
        embed.add_field(name="💰 Amount", value=f"₹{amount}", inline=True)
    embed.set_footer(text="Nayumi 🎀 • 24/7 Instant Auto Verification")

    view = OpenPaymentModalView(default_amount=amount, author_id=ctx.author.id)
    await ctx.send(embed=embed, view=view)


@bot.tree.command(name="pay", description="Pay via instant UPI QR code with live verification")
@app_commands.describe(amount="Amount in INR (optional, can also enter in form)")
async def slash_pay(interaction: discord.Interaction, amount: str = None):
    """Slash command: /pay with direct modal popup"""
    await interaction.response.send_modal(
        PaymentDetailsModal(default_amount=amount, default_name=interaction.user.display_name)
    )


if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
