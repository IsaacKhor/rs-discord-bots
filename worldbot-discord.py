#!/usr/bin/env python3

import aiohttp, atexit, asyncio, os, textwrap
from datetime import datetime, timedelta, timezone
from discord.ext import commands
import discord

import worldbot, parser
from wbstime import *

VERSION = '3.10.0'

WBS_UNITED_ID = 261802377009561600

CHANNEL_WAVE_CHAT = 803855255933681664
CHANNEL_VOICE = 780814756713594951
CHANNEL_BOT_LOG = 804209525585608734
CHANNEL_HELP = 842186485200584754
CHANNEL_NOTIFY = 842527669085667408

ROLE_WBS_NOTIFY = 484721172815151114

conn = aiohttp.TCPConnector(ssl=False)
client = commands.Bot(connector=conn, command_prefix='.')
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
    greetmsg = f'Bot starting up. Version {VERSION} loaded.'
    if DEBUG:
        greetmsg += '\n DEBUG MODE ENABLED.'
    await send_to_channel(CHANNEL_BOT_LOG, greetmsg)

    # Schedule the autoreset every hour after a wave
    client.loop.create_task(autoreset_bot())
    client.loop.create_task(notify_wave())


@client.event
async def on_voice_state_update(member, before, after):
    if bot.is_ignoremode():
        return

    now = datetime.now().astimezone(timezone.utc)
    nowf = now.strftime('%H:%M:%S')

    if (before.channel == None and
        after.channel and
        after.channel.id == CHANNEL_VOICE):
        # Participant joined the channel
        # Register with bot if they join within 20minutes of a wave
        _, delta = time_until_wave(timedelta(0))
        if delta.seconds < 20 * 60 or delta.seconds > 400 * 60:
            bot.add_participant(member.display_name)
        
        await get_channel(CHANNEL_BOT_LOG).send(
            f'{nowf}: __"{member.display_name}" joined__ voice')

    # Keep track of people leaving WBS voice
    if (before.channel and
        before.channel.id == CHANNEL_VOICE and
        after.channel == None):
        await get_channel(CHANNEL_BOT_LOG).send(
            f'{nowf}: **"{member.display_name}" left** voice')


# Auto reset 1hr after the wave
async def autoreset_bot():
    while not client.is_closed(): # Loop
        _, wait_time = time_until_wave(timedelta(hours=1))
        await asyncio.sleep(wait_time.seconds)

        bot.reset_state()
        await send_to_channel(CHANNEL_BOT_LOG, 'Auto reset triggered.')


# Notify the @Warbands role
async def notify_wave():
    while not client.is_closed():
        # Schedule next run to be 15 minutes before next wave
        # We pretend like we're 20 minutes in the future because this way
        # at wave-15, we want to schedule ourselves to wake up in 7hrs in 
        # preperation for the wave in 7hrs 15mins, not the wave in 15mins
        now = datetime.now().astimezone(timezone.utc) + timedelta(minutes=20)
        _, delta = time_until_wave(timedelta(minutes=-15), now)
        await asyncio.sleep(delta.seconds)

        # We put the actual notification after the slee because this way,
        # the 1st time the loop is run we don't immediately notify everybody
        # on bot startup, instead we wait until the correct time
        if bot.is_ignoremode():
            await send_to_channel(CHANNEL_BOT_LOG, 'Not notifying due to ignore mode')
            continue

        await send_to_channel(CHANNEL_NOTIFY,
            f'<@&{ROLE_WBS_NOTIFY}> wave in 15 minutes. Please join at <#{CHANNEL_WAVE_CHAT}> and <#{CHANNEL_VOICE}>')


### ============
### Bot commands
### ============

# Only the commands that we handle through the discord.py parser
# The rest are handled in the worldbot module itself

@client.command(name='debug', brief='Shows debug information')
async def debug(ctx):
    msg = bot.get_debug_info()
    if DEBUG:
        print(msg)
    for l in textwrap.wrap(msg, width=1900):
        await ctx.send(l)


@client.command(name='version', brief='Show version')
async def version(ctx):
    await ctx.send(f'Bot version v{VERSION}. Written by CrafyElk :D')


@client.command(name='reset', brief='Reset bot state')
async def reset(ctx):
    summary = bot.get_wave_summary()
    bot.reset_state()
    await ctx.send(summary)


@client.command(name='fc', brief='Set new in-game fc')
async def fc(ctx, fc_name: str):
    bot.fcnanme = fc_name
    await ctx.send(f'Setting FC to: {bot.fcnanme}')


@client.command(name='host', brief='Set host')
async def host(ctx, host:str = ''):
    """ Sets `host` as host. Uses caller if none specified. """
    if host:
        bot.host = host
    bot.host = ctx.author.display_name
    await ctx.send(f'Setting host to: {bot.host}')


@client.command(name='scout', brief='Add yourself to scout list')
async def scout(ctx):
    bot.scoutlist.add(ctx.author.display_name)
    await ctx.send(f'Adding {ctx.author.display_name} to scout list')


@client.command(name='anti', brief='Add yourself to anti list')
async def anti(ctx):
    bot.antilist.add(ctx.author.display_name)
    await ctx.send(f'Adding {ctx.author.display_name} to anti list')


@client.command(name='call', brief='Add msg to call history')
async def call(ctx, *, msg: str):
    bot.worldhist.append(msg)
    await ctx.send(f'Adding {msg} to call history')


@client.command(name='wbs', brief='Show next wave information')
async def wbs(ctx):
    """ Returns the time to and of next wave in several timezones. """
    await ctx.send(next_wave_info())


@client.command(name='take', brief='Assign yourself some worlds')
async def take(ctx, numworlds: int = 3, location: str = 'unk'):
    """
    Grabs `numworlds` unassigned worlds of location `location` 
    with no information except location available and marks them
    as assigned. The intended workflow is for a scout to 
    `take 5 unk` to assign themselves 5 worlds of unknown 
    location and then scout those worlds, to prevent
    scouts from scouting the same worlds.

    `numworlds` must be >=1
    `location` must be `elm|rdi|dwf|unk`, defaults to unk
    """
    if not parser.is_location(location):
        await ctx.send(f'Invalid location: {location}')
    if numworlds < 1:
        await ctx.send(f'Invalid numworlds: {numworlds}')
    ret = bot.take_worlds(numworlds, parser.convert_location(location))
    await ctx.send(ret, reference=ctx.message, mention_author=True)


@client.event
async def on_message(msgobj):
    # Don't respond to bot messages to prevent infinite loops
    # This includes ourselves
    if msgobj.author.bot:
        return

    # Only respond to messages in text channels that are the bot and the help
    istext = isinstance(msgobj.channel, discord.TextChannel)
    if istext and not (msgobj.channel.id in [CHANNEL_WAVE_CHAT, CHANNEL_HELP]):
        return

    msglog.write(f'{msgobj.author.display_name}: {msgobj.content}\n')
    if DEBUG:
        print(f'{msgobj.author.display_name}: {msgobj.content}')

    # We only continue on to process bot commands if the return is falsy
    response = parser.process_message(bot, msgobj, DEBUG)
    if DEBUG:
        print(f'Parser response: {response}')
    if response:
        if type(response) is str:
            await msgobj.channel.send(response)
        elif type(response) is list:
            for s in response:
                await msgobj.channel.send(s)
    else:
        print('Passing off to discord.py')
        await client.process_commands(msgobj)


import sys
if len(sys.argv) < 2:
    print("Usage: ./worldbot-discord.py <token>")


client.run(sys.argv[1])
