import asyncio
import random
from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import os

# === Your credentials ===
api_id = 29010066
api_hash = '2e0d5a624f4eb3991826a9abe13c78b7'
string_session = '1BVtsOKEBu4Bw7rn5KoPXsA2VLOHqanw5MgQQIv7UlrY5fWE-3TQHGbjb_dxB_qzzqH9IWdtWegKUXvZwAylWqHsTBLB7j_-hXslw6SPGvWcOaUGyGs3sKjvAnT8cJw4BCSF8PJ2RgVCDucuRWESBj7gq-9VNc_-7LqBz3ryjIRQYL5nESJKS7pm3F1BIILm2Abtl76K47P2oJxrLP8oQBydZKIQAfDDtbr02bNcSMOPhCJilOgmqUIoZLxne9HzBIQK2bIupZDeIe2IQljyCWtVi7JzBAUp2KlyuOnFUJr-PJZHMRjOpmGZgufCaPTR2js_hgqPkHDd-Td3SecC51XfYLsvepWk='
OWNER_ID = 7425304864

client = TelegramClient(StringSession(string_session), api_id, api_hash)

# === Settings ===
GROUPS_FILE = "groups.txt"
active_groups = set()
reply_message = "Join our new movie group\nSearch and download all movies via @rexiebotcat.\nOld group inactive — join now."
delete_after = 35
IGNORE_WORDS = ['ok', 'thanks', '👍', '🙏', 'hi', 'hello']
rate_limiter = asyncio.Semaphore(1)
last_replied = {}
last_sent_time = 0

# === Persistent Storage ===
def save_groups():
    with open(GROUPS_FILE, "w") as f:
        for gid in active_groups:
            f.write(f"{gid}\n")

def load_groups():
    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "r") as f:
            for line in f:
                gid = line.strip()
                if gid:
                    active_groups.add(int(gid))

# === Check if command is from Saved Messages ===
def is_saved_messages(event):
    return event.chat_id == OWNER_ID and event.is_private

@client.on(events.NewMessage(pattern=r'^/add\s+(-?\d+)$'))
async def add_group(event):
    if not is_saved_messages(event):
        return
    group_id = int(event.pattern_match.group(1))
    active_groups.add(group_id)
    save_groups()
    await event.reply(f"✅ Group `{group_id}` added.")

@client.on(events.NewMessage(pattern=r'^/remove\s+(-?\d+)$'))
async def remove_group(event):
    if not is_saved_messages(event):
        return
    group_id = int(event.pattern_match.group(1))
    if group_id in active_groups:
        active_groups.remove(group_id)
        save_groups()
        await event.reply(f"❌ Group `{group_id}` removed.")
    else:
        await event.reply("⚠️ Group not found.")

@client.on(events.NewMessage(pattern=r'^/groupinfo$'))
async def show_group_info(event):
    if not is_saved_messages(event):
        return
    if not active_groups:
        await event.reply("📭 No groups configured.")
        return
    msg = "📋 Groups:\n"
    for gid in active_groups:
        msg += f"• `{gid}`\n"
    msg += f"\n🗨️ Message: `{reply_message}`"
    msg += f"\n⏳ Delete after: {delete_after} sec"
    await event.reply(msg)

@client.on(events.NewMessage(pattern=r'^/setmsg\s+([\s\S]+)'))
async def set_reply_message(event):
    if not is_saved_messages(event):
        return
    global reply_message
    reply_message = event.pattern_match.group(1)
    await event.reply("✅ Reply message updated.")

@client.on(events.NewMessage(pattern=r'^/setdel\s+(\d+)$'))
async def set_delete_time(event):
    if not is_saved_messages(event):
        return
    global delete_after
    delete_after = int(event.pattern_match.group(1))
    await event.reply(f"⏲️ Auto-delete time set to {delete_after} seconds.")

@client.on(events.NewMessage(pattern=r'^/viewmsg$'))
async def view_reply_message(event):
    if not is_saved_messages(event):
        return
    await event.reply(f"📝 Current Reply Message:\n\n{reply_message}")

# === Auto-reply Handler – Only to Users in Group ===
@client.on(events.NewMessage(incoming=True))
async def auto_reply(event):
    global last_sent_time

    if not event.is_group:
        return

    if event.chat_id not in active_groups:
        print(f"[DEBUG] Ignored message from group {event.chat_id} (not in active_groups)")
        return

    try:
        sender = await event.get_sender()
    except:
        return  # Skip if sender info not available

    if not sender or sender.bot or sender.id == OWNER_ID or not reply_message:
        return

    text = event.raw_text.strip().lower()
    if not text or text in IGNORE_WORDS:
        return

    user_id = sender.id
    now = asyncio.get_event_loop().time()

    if user_id in last_replied and now - last_replied[user_id] < 60:
        return
    if now - last_sent_time < 7:
        return

    last_replied[user_id] = now
    last_sent_time = now

    try:
        async with rate_limiter:
            reply = await event.reply(reply_message)
            await asyncio.sleep(delete_after)
            await reply.delete()
            await asyncio.sleep(random.randint(2, 4))
    except Exception as e:
        print(f"⚠️ Error replying: {e}")

# === UptimeRobot Web Server ===
async def handle(request):
    return web.Response(text="✅ UserBot is alive!")

async def run_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)  # Render-compatible port
    await site.start()

# === Combined Start ===
async def main():
    load_groups()
    await client.start()
    print("🤖 UserBot is running with anti-ban logic...")
    await asyncio.gather(
        client.run_until_disconnected(),
        run_server()
    )

asyncio.run(main())
