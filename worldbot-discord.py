#!/usr/bin/env python3

import discord
import aiohttp
import worldbot

BOT_CHANNEL = 803855255933681664
VOICE_CHANNEL = 780814756713594951 
BOT_LOG = 804209525585608734

conn = aiohttp.TCPConnector(ssl=False)
client = discord.Client(connector = conn)
bot = worldbot.WorldBot()
msglog = open('messages.log', 'a', encoding='utf-8')

def get_channel(id):
    return client.get_channel(id)

@client.event
async def on_ready():
    print('Logged is as {}'.format(client.user))
    await get_channel(BOT_LOG).send(f'Bot starting up.\nVersion {worldbot.VERSION} loaded.')

@client.event
async def on_message(msgobj):
    ispublic = isinstance(msgobj.channel, discord.TextChannel)

    if ispublic and msgobj.channel.id != BOT_CHANNEL:
        return

    text = msgobj.content
    author = msgobj.author.display_name

    msglog.write(f'{author}: {text}\n')

    response = bot.on_notify_msg(text, ispublic, author)
    if response:
        await msgobj.channel.send(response)

@client.event
async def on_voice_state_update(member, before, after):
    if (before.channel == None and
        after.channel and
        after.channel.id == VOICE_CHANNEL):
        await get_channel(BOT_LOG).send(
            f'User __"{member.display_name}" joined__ voice')
    # Keep track of people leaving WBS voice
    if (before.channel and
        before.channel.id == VOICE_CHANNEL and
        after.channel == None):
        await get_channel(BOT_LOG).send(
            f'User **"{member.display_name}" left** voice')

import sys
if len(sys.argv) < 2:
    print("Usage: ./worldbot-discord.py <token>")

client.run(sys.argv[1])