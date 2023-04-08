#!/usr/bin/env python3

import random
import discord
import discord.abc
import sys
import os
import logging
import datetime

loglv = os.environ.get('LOGLV') or 'INFO'
loglvn = getattr(logging, loglv.upper(), None)
logging.basicConfig(
    # filename='bot4tincture.log',
    level=loglv,
    format='[%(asctime)s %(levelname)s]: %(message)s')

intents = discord.Intents.all()
client = discord.Client(intents=intents)
initialised = False

WHITELIST_GUILDS = [838256437267923015, 747501916107309246, 997443976305070090]

members_cache = None
members_cache_guild = None


@client.event
async def on_ready():
    global initialised
    if initialised:
        logging.info(f'Bot reconnected')
        return

    logging.info('Bot ready')


async def get_or_make_wh(ch: discord.TextChannel) -> discord.Webhook:
    whs = await ch.webhooks()
    for w in whs:
        if w.name == 'aprfools-swap':
            return w

    logging.info(f'Creating webhook for channel {ch}')
    return await ch.create_webhook(name='aprfools-swap')


async def get_rand_guild_mem(guild: discord.Guild) -> discord.Member:
    # return guild.get_member(194588895332139008)
    global members_cache
    global members_cache_guild

    #logging.info(f'Current cache: {members_cache}, guild {members_cache_guild}')

    if members_cache == None or guild.id != members_cache_guild:
        logging.info(f'Fetching members cache for guild {guild}')
        mems = [x async for x in guild.fetch_members(limit=100)]
        members_cache = mems
        members_cache_guild = guild.id

    return random.choice(members_cache)


@client.event
async def on_message(msg: discord.Message):
    # ignore bot messages and dms
    if msg.author.bot or not msg.guild:
        return

    # special commands
    if msg.content == '.disableslowmode':
        for c in msg.guild.text_channels:
            await c.edit(slowmode_delay=0)

    # only on apr fools
    dt = datetime.datetime.now()
    if dt > datetime.datetime(2023, 4, 2, 3, 0):
        return

    logging.debug(f'Found message {msg}')

    # text channels only
    if msg.channel.type != discord.ChannelType.text:
        return

    # whitelist specific guilds
    if not msg.guild.id in WHITELIST_GUILDS:
        return

    # if not msg.channel.id in WHITELIST_CHANS:
    #     return

    wh = await get_or_make_wh(msg.channel)
    target_mem = await get_rand_guild_mem(msg.guild)

    logging.debug(f'Target avatar {target_mem.display_avatar}')
    tofs = [await x.to_file() for x in msg.attachments]

    await wh.send(
        content=msg.content or '<empty message>',
        username=target_mem.display_name,
        avatar_url=target_mem.display_avatar.url,
        embeds=msg.embeds,
        files=tofs,
        allowed_mentions=discord.AllowedMentions.none(),
    )

    await msg.delete()
    return

if len(sys.argv) < 2:
    print("Usage: ./wbunotify.py <token>")
client.run(sys.argv[1])

