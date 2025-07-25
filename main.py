import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
import os
import threading
from flask import Flask

# === Flask app ===
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot działa"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# === Baza danych ===
conn = sqlite3.connect("economy.db")
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    wallet INTEGER DEFAULT 0,
    bank INTEGER DEFAULT 0,
    last_work TEXT,
    last_crime TEXT,
    last_slut TEXT
)
""")
conn.commit()
conn.close()

# === Bot ===
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# === Pomocnicze funkcje ===
def get_user_data(user_id):
    conn = sqlite3.connect("economy.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    data = c.fetchone()
    if data is None:
        c.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        data = c.fetchone()
    conn.close()
    return data

def update_user_data(user_id, field, value):
    conn = sqlite3.connect("economy.db")
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

def check_cooldown(last_time_str, cooldown_seconds):
    if last_time_str is None:
        return True, 0
    last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
    now = datetime.utcnow()
    elapsed = (now - last_time).total_seconds()
    if elapsed >= cooldown_seconds:
        return True, 0
    else:
        return False, cooldown_seconds - elapsed

def create_embed(title, description, color=0x00FF00):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="Ekonomia bota")
    embed.timestamp = datetime.utcnow()
    return embed

# === Slash commands ===

@bot.tree.command(name="balance", description="Sprawdź swoje saldo")
async def balance(interaction: discord.Interaction):
    user_id = interaction.user.id
    data = get_user_data(user_id)
    wallet, bank = data[1], data[2]
    embed = create_embed("Twój balans", f"💼 Portfel: {wallet}$\n🏦 Bank: {bank}$")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="bank", description="Sprawdź stan portfela i banku")
async def bank(interaction: discord.Interaction):
    user_id = interaction.user.id
    data = get_user_data(user_id)
    wallet, bank_amount = data[1], data[2]
    embed = create_embed("Stan konta", f"💼 Portfel: {wallet}$ | 🏦 Bank: {bank_amount}$")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="work", description="Pracuj i zarabiaj pieniądze (1h cooldown)")
async def work(interaction: discord.Interaction):
    user_id = interaction.user.id
    data = get_user_data(user_id)
    can_use, cd = check_cooldown(data[3], 3600)
    if not can_use:
        embed = create_embed("⏳ Cooldown", f"Poczekaj {int(cd // 60)} minut, zanim znów popracujesz!", color=0xFF0000)
        await interaction.response.send_message(embed=embed)
        return

    earned = random.randint(100, 300)
    update_user_data(user_id, "wallet", data[1] + earned)
    update_user_data(user_id, "last_work", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    embed = create_embed("🛠️ Praca", f"Pracowałeś i zarobiłeś {earned}$!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="crime", description="Spróbuj popełnić przestępstwo (ryzyko!)")
async def crime(interaction: discord.Interaction):
    user_id = interaction.user.id
    data = get_user_data(user_id)
    can_use, cd = check_cooldown(data[4], 20*60)
    if not can_use:
        embed = create_embed("⏳ Cooldown", f"Poczekaj {int(cd // 60)} minut, zanim spróbujesz ponownie!", color=0xFF0000)
        await interaction.response.send_message(embed=embed)
        return

    success = random.choice([True, False])
    if success:
        earned = random.randint(200, 600)
        update_user_data(user_id, "wallet", data[1] + earned)
        msg = f"🎉 Udało się! Ukradłeś {earned}$"
        color = 0x00FF00
    else:
        lost = random.randint(100, 400)
        new_wallet = max(0, data[1] - lost)
        update_user_data(user_id, "wallet", new_wallet)
        msg = f"🚓 Zostałeś złapany i straciłeś {lost}$"
        color = 0xFF0000

    update_user_data(user_id, "last_crime", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    embed = create_embed("🚨 Przestępstwo", msg, color=color)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="slut", description="Spróbuj flirtować dla pieniędzy (mniejsze ryzyko)")
async def slut(interaction: discord.Interaction):
    user_id = interaction.user.id
    data = get_user_data(user_id)
    can_use, cd = check_cooldown(data[5], 10*60)
    if not can_use:
        embed = create_embed("⏳ Cooldown", f"Musisz poczekać {int(cd // 60)} minut!", color=0xFF0000)
        await interaction.response.send_message(embed=embed)
        return

    success = random.choices([True, False], weights=[70, 30])[0]
    if success:
        earned = random.randint(100, 300)
        update_user_data(user_id, "wallet", data[1] + earned)
        msg = f"😉 Udało się! Zarobiłeś {earned}$ na flirtowaniu."
        color = 0x00FF00
    else:
        lost = random.randint(50, 150)
        new_wallet = max(0, data[1] - lost)
        update_user_data(user_id, "wallet", new_wallet)
        msg = f"😢 Nikt nie był zainteresowany. Straciłeś {lost}$"
        color = 0xFF0000

    update_user_data(user_id, "last_slut", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    embed = create_embed("💋 Flirt", msg, color=color)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="deposit", description="Wpłać pieniądze do banku")
@app_commands.describe(amount="Ile chcesz wpłacić")
async def deposit(interaction: discord.Interaction, amount: int):
    user_id = interaction.user.id
    data = get_user_data(user_id)
    if amount <= 0:
        embed = create_embed("❌ Błąd", "Podaj poprawną kwotę (> 0)", color=0xFF0000)
        await interaction.response.send_message(embed=embed)
        return
    if data[1] < amount:
        embed = create_embed("❌ Błąd", "Nie masz tyle pieniędzy w portfelu", color=0xFF0000)
        await interaction.response.send_message(embed=embed)
        return
    update_user_data(user_id, "wallet", data[1] - amount)
    update_user_data(user_id, "bank", data[2] + amount)
    embed = create_embed("✅ Sukces", f"Wpłacono {amount}$ do banku!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="withdraw", description="Wypłać pieniądze z banku")
@app_commands.describe(amount="Ile chcesz wypłacić")
async def withdraw(interaction: discord.Interaction, amount: int):
    user_id = interaction.user.id
    data = get_user_data(user_id)
    if amount <= 0:
        embed = create_embed("❌ Błąd", "Podaj poprawną kwotę (> 0)", color=0xFF0000)
        await interaction.response.send_message(embed=embed)
        return
    if data[2] < amount:
        embed = create_embed("❌ Błąd", "Nie masz tyle pieniędzy w banku", color=0xFF0000)
        await interaction.response.send_message(embed=embed)
        return
    update_user_data(user_id, "bank", data[2] - amount)
    update_user_data(user_id, "wallet", data[1] + amount)
    embed = create_embed("✅ Sukces", f"Wypłacono {amount}$ z banku!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="pay", description="Wyślij pieniądze innej osobie")
@app_commands.describe(user="Komu chcesz zapłacić", amount="Ile chcesz przelać")
async def pay(interaction: discord.Interaction, user: discord.User, amount: int):
    from_id = interaction.user.id
    to_id = user.id
    if from_id == to_id:
        embed = create_embed("❌ Błąd", "Nie możesz zapłacić samemu sobie", color=0xFF0000)
        await interaction.response.send_message(embed=embed)
        return
    if amount <= 0:
        embed = create_embed("❌ Błąd", "Kwota musi być większa niż 0", color=0xFF0000)
        await interaction.response.send_message(embed=embed)
        return
    sender_data = get_user_data(from_id)
    if sender_data[1] < amount:
        embed = create_embed("❌ Błąd", "Nie masz tyle w portfelu", color=0xFF0000)
        await interaction.response.send_message(embed=embed)
        return
    receiver_data = get_user_data(to_id)

    update_user_data(from_id, "wallet", sender_data[1] - amount)
    update_user_data(to_id, "wallet", receiver_data[1] + amount)
    embed = create_embed("✅ Sukces", f"Przesłano {amount}$ do {user.name}!")
    await interaction.response.send_message(embed=embed)

# === Prefix commands ===

@bot.command(name="work", help="Pracuj i zarabiaj pieniądze (1h cooldown)")
async def work_cmd(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, cd = check_cooldown(data[3], 3600)
    if not can_use:
        embed = create_embed("⏳ Cooldown", f"Poczekaj {int(cd // 60)} minut, zanim znów popracujesz!", color=0xFF0000)
        await ctx.send(embed=embed)
        return

    earned = random.randint(100, 300)
    update_user_data(user_id, "wallet", data[1] + earned)
    update_user_data(user_id, "last_work", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    embed = create_embed("🛠️ Praca", f"Pracowałeś i zarobiłeś {earned}$!")
    await ctx.send(embed=embed)

@bot.command(name="crime", help="Spróbuj popełnić przestępstwo (ryzyko!)")
async def crime_cmd(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, cd = check_cooldown(data[4], 20*60)
    if not can_use:
        embed = create_embed("⏳ Cooldown", f"Poczekaj {int(cd // 60)} minut, zanim spróbujesz ponownie!", color=0xFF0000)
        await ctx.send(embed=embed)
        return

    success = random.choice([True, False])
    if success:
        earned = random.randint(200, 600)
        update_user_data(user_id, "wallet", data[1] + earned)
        msg = f"🎉 Udało się! Ukradłeś {earned}$"
        color = 0x00FF00
    else:
        lost = random.randint(100, 400)
        new_wallet = max(0, data[1] - lost)
        update_user_data(user_id, "wallet", new_wallet)
        msg = f"🚓 Zostałeś złapany i straciłeś {lost}$"
        color = 0xFF0000

    update_user_data(user_id, "last_crime", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    embed = create_embed("🚨 Przestępstwo", msg, color=color)
    await ctx.send(embed=embed)

@bot.command(name="slut", help="Spróbuj flirtować dla pieniędzy (mniejsze ryzyko)")
async def slut_cmd(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    can_use, cd = check_cooldown(data[5], 10*60)
    if not can_use:
        embed = create_embed("⏳ Cooldown", f"Musisz poczekać {int(cd // 60)} minut!", color=0xFF0000)
        await ctx.send(embed=embed)
        return

    success = random.choices([True, False], weights=[70, 30])[0]
    if success:
        earned = random.randint(100, 300)
        update_user_data(user_id, "wallet", data[1] + earned)
        msg = f"😉 Udało się! Zarobiłeś {earned}$ na flirtowaniu."
        color = 0x00FF00
    else:
        lost = random.randint(50, 150)
        new_wallet = max(0, data[1] - lost)
        update_user_data(user_id, "wallet", new_wallet)
        msg = f"😢 Nikt nie był zainteresowany. Straciłeś {lost}$"
        color = 0xFF0000

    update_user_data(user_id, "last_slut", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    embed = create_embed("💋 Flirt", msg, color=color)
    await ctx.send(embed=embed)

@bot.command(name="balance", help="Sprawdź swoje saldo")
async def balance_cmd(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    wallet, bank = data[1], data[2]
    embed = create_embed("Twój balans", f"💼 Portfel: {wallet}$\n🏦 Bank: {bank}$")
    await ctx.send(embed=embed)

@bot.command(name="bank", help="Sprawdź stan portfela i banku")
async def bank_cmd(ctx):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    wallet, bank_amount = data[1], data[2]
    embed = create_embed("Stan konta", f"💼 Portfel: {wallet}$ | 🏦 Bank: {bank_amount}$")
    await ctx.send(embed=embed)

@bot.command(name="deposit", help="Wpłać pieniądze do banku")
async def deposit_cmd(ctx, amount: int):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    if amount <= 0:
        embed = create_embed("❌ Błąd", "Podaj poprawną kwotę (> 0)", color=0xFF0000)
        await ctx.send(embed=embed)
        return
    if data[1] < amount:
        embed = create_embed("❌ Błąd", "Nie masz tyle pieniędzy w portfelu", color=0xFF0000)
        await ctx.send(embed=embed)
        return
    update_user_data(user_id, "wallet", data[1] - amount)
    update_user_data(user_id, "bank", data[2] + amount)
    embed = create_embed("✅ Sukces", f"Wpłacono {amount}$ do banku!")
    await ctx.send(embed=embed)

@bot.command(name="withdraw", help="Wypłać pieniądze z banku")
async def withdraw_cmd(ctx, amount: int):
    user_id = ctx.author.id
    data = get_user_data(user_id)
    if amount <= 0:
        embed = create_embed("❌ Błąd", "Podaj poprawną kwotę (> 0)", color=0xFF0000)
        await ctx.send(embed=embed)
        return
    if data[2] < amount:
        embed = create_embed("❌ Błąd", "Nie masz tyle pieniędzy w banku", color=0xFF0000)
        await ctx.send(embed=embed)
        return
    update_user_data(user_id, "bank", data[2] - amount)
    update_user_data(user_id, "wallet", data[1] + amount)
    embed = create_embed("✅ Sukces", f"Wypłacono {amount}$ z banku!")
    await ctx.send(embed=embed)

@bot.command(name="pay", help="Wyślij pieniądze innej osobie")
async def pay_cmd(ctx, member: discord.Member, amount: int):
    from_id = ctx.author.id
    to_id = member.id
    if from_id == to_id:
        embed = create_embed("❌ Błąd", "Nie możesz zapłacić samemu sobie", color=0xFF0000)
        await ctx.send(embed=embed)
        return
    if amount <= 0:
        embed = create_embed("❌ Błąd", "Kwota musi być większa niż 0", color=0xFF0000)
        await ctx.send(embed=embed)
        return
    sender_data = get_user_data(from_id)
    if sender_data[1] < amount:
        embed = create_embed("❌ Błąd", "Nie masz tyle w portfelu", color=0xFF0000)
        await ctx.send(embed=embed)
        return
    receiver_data = get_user_data(to_id)

    update_user_data(from_id, "wallet", sender_data[1] - amount)
    update_user_data(to_id, "wallet", receiver_data[1] + amount)
    embed = create_embed("✅ Sukces", f"Przesłano {amount}$ do {member.name}!")
    await ctx.send(embed=embed)

# === Event on_ready ===
@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands synced: {len(synced)}")
    except Exception as e:
        print(f"Błąd podczas synchronizacji slash commands: {e}")

# === Start Flask w osobnym wątku ===
threading.Thread(target=run_flask).start()

# === Uruchomienie bota ===
token = os.getenv("DISCORD_TOKEN")
if not token:
    print("❌ Brak tokena w zmiennych środowiskowych!")
else:
    bot.run(token)
