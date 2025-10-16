import discord
from discord.ext import commands
import random, asyncio, json, os, itertools

# ----------------------------------------
# CONFIG
# ----------------------------------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

OWNER_IDS = [1424825251388461176]   # replace with your own ID(s)
STAFF_IDS = [1387598091275993220]   # replace or extend as needed

# ----------------------------------------
# FILES
# ----------------------------------------
WARNINGS_FILE = "warnings.json"
STATUSES_FILE = "statuses.json"

# ----------------------------------------
# LOAD / SAVE HELPERS
# ----------------------------------------
def load_json(filename, default):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump(default, f)
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

# ----------------------------------------
# LOAD DATA
# ----------------------------------------
WARNINGS = load_json(WARNINGS_FILE, {})
STATUSES = load_json(STATUSES_FILE, [
    "Moderating the server 🛡️",
    "Watching over members 👀",
    "Use !help for commands ⚙️",
    "Keeping things peaceful 💫"
])

# ----------------------------------------
# PERMISSION CHECKS
# ----------------------------------------
def is_staff():
    async def predicate(ctx):
        if ctx.author.id in OWNER_IDS or ctx.author.id in STAFF_IDS or ctx.author.guild_permissions.administrator:
            return True
        await ctx.send("🚫 You are not authorized to use this command.")
        return False
    return commands.check(predicate)

def is_owner():
    async def predicate(ctx):
        if ctx.author.id in OWNER_IDS:
            return True
        await ctx.send("🚫 Only a bot owner can use this command.")
        return False
    return commands.check(predicate)

# ----------------------------------------
# STATUS SYSTEM
# ----------------------------------------
stop_rotation = False
_rotation_task = None

async def rotate_status():
    global stop_rotation
    statuses = itertools.cycle(STATUSES)
    while True:
        try:
            if not stop_rotation:
                current_status = next(statuses)
                activity_type = random.choice([
                    discord.ActivityType.playing,
                    discord.ActivityType.watching,
                    discord.ActivityType.listening
                ])
                await bot.change_presence(
                    activity=discord.Activity(type=activity_type, name=current_status),
                    status=discord.Status.online
                )
            await asyncio.sleep(30)
        except Exception as e:
            print(f"[status] Error: {e}")
            await asyncio.sleep(10)

@bot.event
async def on_ready():
    global _rotation_task
    print(f"✅ Logged in as {bot.user}")
    if not _rotation_task or _rotation_task.done():
        _rotation_task = bot.loop.create_task(rotate_status())
        print("[status] Rotation task started.")

# ----------------------------------------
# STATUS CONTROL COMMANDS
# ----------------------------------------
@bot.command()
@is_owner()
async def setstatus(ctx, *, text: str):
    """Manually set bot status and pause rotation."""
    global stop_rotation
    stop_rotation = True
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.playing, name=text),
        status=discord.Status.online
    )
    await ctx.send(f"📝 Status manually set to: `{text}`\n⏸️ Rotation paused.")

@bot.command()
@is_owner()
async def resetstatus(ctx):
    """Resume automatic rotating status."""
    global stop_rotation
    stop_rotation = False
    await ctx.send("▶️ Status rotation resumed.")

# ----------------------------------------
# STAFF MANAGEMENT
# ----------------------------------------
@bot.command()
@is_staff()
async def addstaff(ctx, member: discord.Member):
    if member.id in STAFF_IDS:
        return await ctx.send("⚠️ That user is already staff.")
    STAFF_IDS.append(member.id)
    await ctx.send(f"✅ {member.mention} has been added as staff.")

@bot.command()
@is_staff()
async def removestaff(ctx, member: discord.Member):
    if member.id not in STAFF_IDS:
        return await ctx.send("⚠️ That user isn’t staff.")
    STAFF_IDS.remove(member.id)
    await ctx.send(f"🗑️ {member.mention} has been removed from staff.")

@bot.command()
@is_staff()
async def stafflist(ctx):
    if not STAFF_IDS:
        return await ctx.send("⚠️ No staff members yet.")
    staff_mentions = [f"<@{sid}>" for sid in STAFF_IDS]
    await ctx.send("👥 **Staff List:**\n" + "\n".join(staff_mentions))

# ----------------------------------------
# OWNER MANAGEMENT
# ----------------------------------------
@bot.command()
@is_owner()
async def addowner(ctx, member: discord.Member):
    if member.id in OWNER_IDS:
        return await ctx.send("⚠️ That user is already an owner.")
    OWNER_IDS.append(member.id)
    await ctx.send(f"👑 {member.mention} has been added as an owner.")

@bot.command()
@is_owner()
async def removeowner(ctx, member: discord.Member):
    if member.id not in OWNER_IDS:
        return await ctx.send("⚠️ That user isn’t an owner.")
    if member.id == ctx.author.id:
        return await ctx.send("❌ You can’t remove yourself.")
    OWNER_IDS.remove(member.id)
    await ctx.send(f"🗑️ {member.mention} removed from owners.")

@bot.command()
@is_owner()
async def ownerlist(ctx):
    owners = [f"<@{oid}>" for oid in OWNER_IDS]
    await ctx.send("👑 **Bot Owners:**\n" + "\n".join(owners))

# ----------------------------------------
# MODERATION COMMANDS
# ----------------------------------------
@bot.command()
@is_staff()
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    user_id = str(member.id)
    WARNINGS.setdefault(user_id, []).append(reason)
    save_json(WARNINGS_FILE, WARNINGS)
    await ctx.send(f"⚠️ {member.mention} has been warned: `{reason}`")

@bot.command()
@is_staff()
async def warnings(ctx, member: discord.Member):
    user_id = str(member.id)
    user_warnings = WARNINGS.get(user_id, [])
    if not user_warnings:
        return await ctx.send(f"✅ {member.mention} has no warnings.")
    formatted = "\n".join([f"{i+1}. {w}" for i, w in enumerate(user_warnings)])
    await ctx.send(f"⚠️ **Warnings for {member.mention}:**\n{formatted}")

@bot.command()
@is_staff()
async def removewarn(ctx, member: discord.Member, index: int = None):
    user_id = str(member.id)
    if user_id not in WARNINGS or not WARNINGS[user_id]:
        return await ctx.send(f"✅ {member.mention} has no warnings.")
    if index is None:
        WARNINGS[user_id] = []
        save_json(WARNINGS_FILE, WARNINGS)
        return await ctx.send(f"🗑️ Cleared all warnings for {member.mention}.")
    try:
        removed = WARNINGS[user_id].pop(index - 1)
        save_json(WARNINGS_FILE, WARNINGS)
        await ctx.send(f"✅ Removed warning #{index}: `{removed}`")
    except IndexError:
        await ctx.send("⚠️ Invalid warning number.")

@bot.command()
@is_staff()
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 Cleared {amount} messages.", delete_after=3)

@bot.command()
@is_staff()
async def mute(ctx, member: discord.Member, *, reason="No reason provided"):
    guild = ctx.guild
    muted_role = discord.utils.get(guild.roles, name="Muted")
    if not muted_role:
        muted_role = await guild.create_role(name="Muted")
        for channel in guild.channels:
            await channel.set_permissions(muted_role, send_messages=False)
    await member.add_roles(muted_role, reason=reason)
    await ctx.send(f"🔇 {member.mention} has been muted. Reason: `{reason}`")

@bot.command()
@is_staff()
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role in member.roles:
        await member.remove_roles(muted_role)
        await ctx.send(f"🔊 {member.mention} has been unmuted.")
    else:
        await ctx.send(f"⚠️ {member.mention} isn’t muted.")

# ----------------------------------------
# FUN COMMANDS
# ----------------------------------------
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")

@bot.command()
async def flip(ctx):
    await ctx.send(random.choice(["🪙 Heads!", "🪙 Tails!"]))

@bot.command()
async def roll(ctx, dice: str = "1d6"):
    try:
        rolls, limit = map(int, dice.lower().split("d"))
    except Exception:
        return await ctx.send("⚠️ Format must be NdN (e.g. 2d6).")
    results = [random.randint(1, limit) for _ in range(rolls)]
    await ctx.send(f"🎲 You rolled: {', '.join(map(str, results))}")

# ----------------------------------------
# HELP COMMAND
# ----------------------------------------
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🤖 Bot Command List", color=discord.Color.blue())
    embed.add_field(name="⚙️ General", value="`!ping`, `!flip`, `!roll`", inline=False)
    embed.add_field(name="🛡️ Staff Moderation", value="`!clear`, `!mute`, `!unmute`, `!warn`, `!warnings`, `!removewarn`", inline=False)
    embed.add_field(name="👥 Staff Management", value="`!addstaff`, `!removestaff`, `!stafflist`", inline=False)
    embed.add_field(name="👑 Owner Management", value="`!addowner`, `!removeowner`, `!ownerlist`, `!setstatus`, `!resetstatus`", inline=False)
    embed.set_footer(text="Only staff, admins, or owners can use restricted commands.")
    await ctx.send(embed=embed)

# ----------------------------------------
# RUN THE BOT
# ----------------------------------------
bot.run("")








