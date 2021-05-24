#!/usr/bin/env python3

import discord, aiohttp, atexit, inspect, asyncio
import worldbot
from discord.ext import tasks
from datetime import datetime, timedelta, timezone

BOT_CHANNEL = 803855255933681664
VOICE_CHANNEL = 780814756713594951
BOT_LOG = 804209525585608734
HELP_CHANNEL = 842186485200584754

conn = aiohttp.TCPConnector(ssl=False)
client = discord.Client(connector = conn)
bot = worldbot.WorldBot()
msglog = open('messages.log', 'a', encoding='utf-8')

@atexit.register
def save_state():
    bot.save_state()

def get_channel(id):
    return client.get_channel(id)

@client.event
async def on_ready():
    print('Logged is as {}'.format(client.user))
    greetmsg = f'Bot starting up.\nVersion {worldbot.VERSION} loaded.'
    await get_channel(BOT_LOG).send(greetmsg)

    # Schedule the autoreset every hour after a wave
    client.loop.create_task(autoreset_bot())


@client.event
async def on_message(msgobj):
    # Don't respond to our own messages
    if msgobj.author == client.user or msgobj.author.display_name == 'worldbot':
        return

    ispublic = isinstance(msgobj.channel, discord.TextChannel)

    if ispublic and not (msgobj.channel.id in [BOT_CHANNEL, HELP_CHANNEL]):
        return

    text = msgobj.content
    author = msgobj.author.display_name

    msglog.write(f'{author}: {text}\n')

    response = bot.on_notify_msg(text, ispublic, author)
    if response:
        if type(response) is str:
            await msgobj.channel.send(response)
        elif type(response) is list:
            for s in response:
                await msgobj.channel.send(response)


@client.event
async def on_voice_state_update(member, before, after):
    now = datetime.now().astimezone(timezone.utc)
    nowf = now.strftime('%H-%M-%S')

    if (before.channel == None and
        after.channel and
        after.channel.id == VOICE_CHANNEL):
        await get_channel(BOT_LOG).send(
            f'{nowf}: __"{member.display_name}" joined__ voice')

    # Keep track of people leaving WBS voice
    if (before.channel and
        before.channel.id == VOICE_CHANNEL and
        after.channel == None):
        await get_channel(BOT_LOG).send(
            f'{nowf}: **"{member.display_name}" left** voice')


async def delay_to_nextwave():
    now = datetime.now().astimezone(timezone.utc)
    next_wave = worldbot.get_next_wave_datetime(now)
    next_autoreset = next_wave + timedelta(hours=1)

    wait_time = next_autoreset - now
    msg = f"Next wave is at {next_wave.isoformat()}. Next autoreset scheduled for " + \
          f"{next_autoreset.isoformat()}, which is {str(wait_time)} from now."

    await get_channel(BOT_LOG).send(inspect.cleandoc(msg))
    await asyncio.sleep(wait_time.seconds)

# Auto reset 1hr after the wave
async def autoreset_bot():
    if bot.is_registry_empty():
        summary = '\n' + bot.get_wave_summary()
    else:
        summary = ''

    bot.reset_state()
    msg = 'Auto reset triggered.' + summary
    await get_channel(BOT_LOG).send(msg)
    await get_channel(BOT_CHANNEL).send(msg)

    await delay_to_nextwave()

import sys
if len(sys.argv) < 2:
    print("Usage: ./worldbot-discord.py <token>")


client.run(sys.argv[1])
