import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import json
import os
import logging

from keep_alive import keep_alive  # import keep_alive z keep_alive.py

# --- Konfiguracja loggera ---
logging.basicConfig(
    filename='logsy_bot.txt',
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Intents ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # potrzebne do reakcji na wiadomości i przyciski

# --- Bot i Tree ---
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# --- Stałe i zmienne globalne ---
LOG_CHANNEL_ID = 1383475893128663232
DATA_FILE = "invite_data.json"
AUTO_ROLE_ID = 1383499862003159242  # podmień na swoje ID roli

invite_counts = {}
leave_counts = {}
fake_counts = {}
bonus_counts = {}

user_invites = {}

cached_invites = {}

# --- Funkcje do zapisu i odczytu danych ---

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

# --- Eventy bota ---

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

# --- Komendy ---

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

# --- System Ticketów ---

TICKET_CATEGORY_NAME = "Tickety"  # Nazwa kategorii ticketów
WELCOME_MESSAGE = (
    "Witaj w tickecie! Napisz tu swój problem lub pytanie. "
    "I poczekaj aż administracja odpisze."
)
TICKET_LOG_CHANNEL_ID = LOG_CHANNEL_ID  # Możesz tu podać inny kanał

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.primary, emoji="🛠", label="Pomoc", custom_id="ticket_help"))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.secondary, emoji="❓", label="Pytanie", custom_id="ticket_question"))

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="🛠", label="Pomoc", custom_id="ticket_help")
    async def help_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "pomoc")

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji="❓", label="Pytanie", custom_id="ticket_question")
    async def question_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "pytanie")

class TicketManageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.danger, label="Zamknij", custom_id="ticket_close"))
        self.add_item(discord.ui.Button(style=discord.ButtonStyle.success, label="Przyjmij + Zamknij", custom_id="ticket_accept_close"))

    @discord.ui.button(style=discord.ButtonStyle.danger, label="Zamknij", custom_id="ticket_close")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await close_ticket(interaction)

    @discord.ui.button(style=discord.ButtonStyle.success, label="Przyjmij + Zamknij", custom_id="ticket_accept_close")
    async def accept_close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ticket przyjęty i zamknięty!", ephemeral=True)
        await close_ticket(interaction)

async def create_ticket(interaction: discord.Interaction, ticket_type: str):
    guild = interaction.guild
    author = interaction.user

    # Szukamy kategorii lub tworzymy ją, jeśli nie istnieje
    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if category is None:
        category = await guild.create_category(TICKET_CATEGORY_NAME)

    # Sprawdzamy, czy użytkownik ma już otwarty ticket
    existing = None
    for ch in category.channels:
        if ch.topic == f"Ticket użytkownika {author.id}":
            existing = ch
            break
    if existing:
        await interaction.response.send_message(f"Masz już otwarty ticket: {existing.mention}", ephemeral=True)
        return

    # Tworzymy kanał ticketu z odpowiednimi uprawnieniami
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    # Dodaj rolę moderatora, jeśli jest
    mod_role = discord.utils.get(guild.roles, name="Mod")
    if mod_role:
        overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    channel_name = f"ticket-{author.name}".lower().replace(" ", "-")
    ticket_channel = await category.create_text_channel(channel_name, overwrites=overwrites, topic=f"Ticket użytkownika {author.id}")

    # Wysyłamy ping @everyone jako osobną wiadomość
    await ticket_channel.send("@everyone")

    # Embed powitalny
    embed = discord.Embed(
        title="Witaj w tickecie!",
        description=WELCOME_MESSAGE,
        color=discord.Color.orange()
    )
    await ticket_channel.send(embed=embed, view=TicketManageView())

    await interaction.response.send_message(f"Ticket został utworzony: {ticket_channel.mention}", ephemeral=True)

async def close_ticket(interaction: discord.Interaction):
    channel = interaction.channel
    if not channel.topic or not channel.topic.startswith("Ticket użytkownika"):
        await interaction.response.send_message("To nie jest kanał ticketowy!", ephemeral=True)
        return

    await channel.delete(reason=f"Ticket zamknięty przez {interaction.user}")

# --- Slash komenda do tworzenia panelu ticketowego ---

@tree.command(name="ticket-panel-create", description="Tworzy panel z przyciskami ticketów")
async def ticket_panel_create(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Panel Ticketów",
        description="Kliknij w przycisk aby utworzyć ticket:\n🛠 Pomoc\n❓ Pytanie",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed, view=TicketPanelView())

# --- Uruchomienie bota ---

if __name__ == "__main__":
    keep_alive()  # uruchom serwer Flask w tle (jeśli masz)
    bot.run(os.environ["DISCORD_TOKEN"])  # token z env
