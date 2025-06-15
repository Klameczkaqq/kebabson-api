import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import json
import os
import logging

from keep_alive import keep_alive  # import keep_alive z keep_alive.py

keep_alive()

# Konfiguracja loggera
logging.basicConfig(
    filename='logsy_bot.txt',
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

LOG_CHANNEL_ID = 1383475893128663232
DATA_FILE = "invite_data.json"

AUTO_ROLE_ID = 1383499862003159242  # zmień na swoje ID roli

invite_counts = {}
leave_counts = {}
fake_counts = {}
bonus_counts = {}

user_invites = {}

cached_invites = {}

def load_data():
    global invite_counts, leave_counts, fake_counts, bonus_counts, user_invites
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                content = f.read().strip()
                if not content:
                    invite_counts.clear()
                    leave_counts.clear()
                    fake_counts.clear()
                    bonus_counts.clear()
                    user_invites.clear()
                    return
                data = json.loads(content)
                invite_counts.update({int(k): v for k, v in data.get("invite_counts", {}).items()})
                leave_counts.update({int(k): v for k, v in data.get("leave_counts", {}).items()})
                fake_counts.update({int(k): v for k, v in data.get("fake_counts", {}).items()})
                bonus_counts.update({int(k): v for k, v in data.get("bonus_counts", {}).items()})
                user_invites.update({int(k): v for k, v in data.get("user_invites", {}).items()})
        except (json.JSONDecodeError, FileNotFoundError):
            invite_counts.clear()
            leave_counts.clear()
            fake_counts.clear()
            bonus_counts.clear()
            user_invites.clear()
    else:
        invite_counts.clear()
        leave_counts.clear()
        fake_counts.clear()
        bonus_counts.clear()
        user_invites.clear()

def save_data():
    data = {
        "invite_counts": invite_counts,
        "leave_counts": leave_counts,
        "fake_counts": fake_counts,
        "bonus_counts": bonus_counts,
        "user_invites": user_invites
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

@bot.event
async def on_ready():
    load_data()
    for guild in bot.guilds:
        invites = await guild.invites()
        cached_invites[guild.id] = {invite.code: invite.uses for invite in invites}
    synced = await tree.sync()
    print(f"Zsynchronizowano {len(synced)} slash commandów.")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Imperium Kebabów"))
    print(f"Bot gotowy jako {bot.user}")

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel is None:
        return

    guild = member.guild
    invites_before = cached_invites.get(guild.id, {})

    invites_after = await guild.invites()
    inviter = None

    for invite in invites_after:
        before_uses = invites_before.get(invite.code, 0)
        if invite.uses > before_uses:
            inviter = invite.inviter
            break

    cached_invites[guild.id] = {invite.code: invite.uses for invite in invites_after}

    if inviter:
        invite_counts[inviter.id] = invite_counts.get(inviter.id, 0) + 1

        if inviter.id not in user_invites:
            user_invites[inviter.id] = []
        if member.id not in user_invites[inviter.id]:
            user_invites[inviter.id].append(member.id)

        save_data()

    now = datetime.now()
    created = member.created_at
    account_creation_timestamp = int(created.timestamp())
    member_count = member.guild.member_count

    embed = discord.Embed(
        title="`🥖` Nowy Czlonek",
        description=(
            f"👋🏻Witamy na **Imperium Kebabów**\n"
            f"👤Nazwa Uzytkownika: **{member}**\n"
            f"📅Konto założone: <t:{account_creation_timestamp}:F>\n"
            f"⏰Dołączył/a: <t:{int(member.joined_at.timestamp())}:R>\n"
            f"👥Aktualnie jest nas: ** {member_count} **\n"
        ),
        color=discord.Color(0xFFA500)
    )

    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    footer_time = now.strftime("Today at %H:%M")
    embed.set_footer(text=footer_time)

    await channel.send(embed=embed)

    # automatyczne nadawanie roli
    role = member.guild.get_role(AUTO_ROLE_ID)
    if role:
        try:
            await member.add_roles(role)
            print(f"Nadano rolę {role.name} użytkownikowi {member.name}")
        except Exception as e:
            print(f"Błąd podczas nadawania roli: {e}")

@bot.event
async def on_member_remove(member):
    leave_counts[member.id] = leave_counts.get(member.id, 0) + 1
    save_data()

@bot.command(name="invites")
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author
    count = invite_counts.get(member.id, 0)
    leaves = leave_counts.get(member.id, 0)
    fakes = fake_counts.get(member.id, 0)
    bonuses = bonus_counts.get(member.id, 0)

    embed = discord.Embed(
        title=f"{member.name}",
        description=(
            f":white_check_mark: {count} zaproszeń\n"
            f":x: {leaves} wyjść\n"
            f":poop: {fakes} fałszywych\n"
            f":sparkles: {bonuses} bonusowych\n\n"
            f"Masz {count} zaproszeń! :clap:"
        ),
        color=discord.Color(0xFFA500)
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.set_footer(text=datetime.now().strftime("Today at %H:%M"))
    await ctx.send(embed=embed)

@tree.command(name="invites", description="Sprawdź ile zaproszeń masz ty lub podany użytkownik")
@app_commands.describe(member="Użytkownik, którego zaproszenia chcesz sprawdzić")
async def slash_invites(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    count = invite_counts.get(member.id, 0)
    leaves = leave_counts.get(member.id, 0)
    fakes = fake_counts.get(member.id, 0)
    bonuses = bonus_counts.get(member.id, 0)

    embed = discord.Embed(
        title=f"{member.name}",
        description=(
            f":white_check_mark: {count} zaproszeń\n"
            f":x: {leaves} wyjść\n"
            f":poop: {fakes} fałszywych\n"
            f":sparkles: {bonuses} bonusowych\n\n"
            f"Masz {count} zaproszeń! :clap:"
        ),
        color=discord.Color(0xFFA500)
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.set_footer(text=datetime.now().strftime("Today at %H:%M"))
    await interaction.response.send_message(embed=embed)

@tree.command(name="invites-list", description="Pokaż listę osób, które zostały zaproszone przez podanego użytkownika")
@app_commands.describe(member="Użytkownik, którego zaproszonych chcesz zobaczyć (opcjonalne)")
async def invites_list(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    invited_ids = user_invites.get(member.id)
    if not invited_ids:
        await interaction.response.send_message(f"{member.display_name} nie zaprosił jeszcze żadnych osób.", ephemeral=True)
        return

    guild = interaction.guild
    mentions = []
    for user_id in invited_ids:
        m = guild.get_member(user_id)
        if m:
            mentions.append(m.mention)
        else:
            mentions.append(f"<@{user_id}>")

    chunk_size = 50
    chunks = [mentions[i:i + chunk_size] for i in range(0, len(mentions), chunk_size)]

    embed = discord.Embed(
        title=f"Lista zaproszonych przez {member.display_name} ({len(invited_ids)})",
        description="\n".join(chunks[0]),
        color=discord.Color(0xFFA500)
    )
    await interaction.response.send_message(embed=embed)

    for chunk in chunks[1:]:
        await interaction.followup.send("\n".join(chunk))


if __name__ == "__main__":
    keep_alive()  # uruchom serwer Flask w tle
    bot.run(os.environ["DISCORD_TOKEN"])  # używa tokena z secretów Replit
