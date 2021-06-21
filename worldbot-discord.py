#!/usr/bin/env python3

import discord, aiohttp, atexit, asyncio, os
from datetime import datetime, timedelta, timezone
import worldbot

WBS_UNITED_ID = 261802377009561600

BOT_CHANNEL = 803855255933681664
VOICE_CHANNEL = 780814756713594951
BOT_LOG = 804209525585608734
HELP_CHANNEL = 842186485200584754
NOTIFY_CHANNEL = 842527669085667408
NOTIFY_ROLE = 484721172815151114

conn = aiohttp.TCPConnector(ssl=False)
client = discord.Client(connector = conn)
bot = worldbot.WorldBot()
msglog = open('messages.log', 'a', encoding='utf-8')

DEBUG = 'WORLDBOT_DEBUG' in os.environ

def get_channel(id):
    return client.get_channel(id)

async def send_to_channel(id, msg):
    await get_channel(id).send(msg)

@atexit.register
def save_state():
    bot.save_state()

@client.event
async def on_ready():
    print('Logged is as {}'.format(client.user))
    greetmsg = f'Bot starting up.\nVersion {worldbot.VERSION} loaded.'
    if DEBUG:
        greetmsg += '\n DEBUG MODE ENABLED.'
    await send_to_channel(BOT_LOG, greetmsg)

    # Schedule the autoreset every hour after a wave
    client.loop.create_task(autoreset_bot())
    client.loop.create_task(notify_wave())


@client.event
async def on_message(msgobj):
    # Don't respond to our own messages
    if msgobj.author == client.user or msgobj.author.display_name == 'worldbot':
        return

    # Only respond to messages in text channels that are the bot and the help
    istext = isinstance(msgobj.channel, discord.TextChannel)
    if istext and not (msgobj.channel.id in [BOT_CHANNEL, HELP_CHANNEL]):
        return

    text = msgobj.content
    author = msgobj.author.display_name
    msglog.write(f'{author}: {text}\n')

    response = bot.on_notify_msg(text, author)
    if response:
        if type(response) is str:
            await msgobj.channel.send(response)
        elif type(response) is list:
            for s in response:
                await msgobj.channel.send(response)


@client.event
async def on_voice_state_update(member, before, after):
    if bot.is_ignoremode():
        return

    now = datetime.now().astimezone(timezone.utc)
    nowf = now.strftime('%H:%M:%S')

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


# Gets the time of next wave and timedelta until that time. Must include
# an offset. Optionally incrlude effectivenow to calculate the time of the
# next wave based on that time instead of the actual current time.
# Offset is the timedelta between the actual time of the next wave plus
# that offset
# Returns the exact time being scheduled, and the timedelta until that time
def time_until_wave(offset, effectivenow=None):
    now = datetime.now().astimezone(timezone.utc)
    if not effectivenow:
        effectivenow = datetime.now().astimezone(timezone.utc)
    next_wave = worldbot.get_next_wave_datetime(effectivenow)
    offset_time = next_wave + offset
    return offset_time, offset_time - now


# Auto reset 1hr after the wave
async def autoreset_bot():
    while not client.is_closed(): # Loop
        next_autoreset, wait_time = time_until_wave(timedelta(hours=1))
        msg = f'Autoreset scheduled for {next_autoreset.isoformat()}, {str(wait_time)} from now.'
        await get_channel(BOT_LOG).send(msg)
        await asyncio.sleep(wait_time.seconds)

        bot.reset_state()
        await send_to_channel(BOT_LOG, 'Auto reset triggered.')


# Notify the @Warbands role
async def notify_wave():
    while not client.is_closed():
        # Schedule next run to be 15 minutes before next wave
        # We pretend like we're 20 minutes in the future because this way
        # at wave-15, we want to schedule ourselves to wake up in 7hrs in 
        # preperation for the wave in 7hrs 15mins, not the wave in 15mins
        now = datetime.now().astimezone(timezone.utc) + timedelta(minutes=20)
        ntime, delta = time_until_wave(timedelta(minutes=-15), now)
        msg = f'Wave notification scheduled for {ntime.isoformat()}, {str(delta)} ({delta.seconds}) from now'

        waitsecs = delta.seconds
        if waitsecs < 60 or waitsecs > (7 * 60 * 60):
            waitsecs = (60 * 60 * 7) - 3
            msg += f'\nWARN: Bot got confused, waiting for 7hrs.'
            msg += f'\nINFO: scheduling for {str(ntime)}, calculating based on {str(now)}, delta is {delta.seconds}'

        await get_channel(BOT_LOG).send(msg)
        await asyncio.sleep(delta.seconds)

        # We put the actual notification after the slee because this way,
        # the 1st time the loop is run we don't immediately notify everybody
        # on bot startup, instead we wait until the correct time
        if bot.is_ignoremode():
            await send_to_channel(BOT_LOG, 'Not notifying due to ignore mode')
            continue
        await send_to_channel(NOTIFY_CHANNEL,
            f'<@&{NOTIFY_ROLE}> wave in 15 minutes. Please join the voice call at <#803855255933681664>.')


import sys
if len(sys.argv) < 2:
    print("Usage: ./worldbot-discord.py <token>")


client.run(sys.argv[1])
