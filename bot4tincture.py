#!/usr/bin/env python3

import random
import discord
import requests
import asyncio
import os
import logging

loglv = os.environ.get('LOGLV') or 'INFO'
loglvn = getattr(logging, loglv.upper(), None)
logging.basicConfig(
    filename='bot4tincture.log',
    level=loglvn,
    format='[%(asctime)s %(levelname)s]: %(message)s')

intents = discord.Intents.default()
client = discord.Client(intents=intents)
initialised = False

GUILD_ID = 997443976305070090

members_cache = None


@client.event
async def on_ready():
    global initialised
    if initialised:
        logging.info(f'Bot reconnected')
        return


async def get_or_make_wh(ch: discord.abc.MessageableChannel) -> discord.Webhook:
    whs = await ch.webhooks()
    for w in whs:
        if w.name == 'aprfools-swap':
            return w

    return await ch.create_webhook('aprfools-swap')


async def get_rand_guild_mem(guild: discord.Guild) -> discord.Member:
    global members_cache

    if not members_cache:
        mems = [x async for x in guild.fetch_members(limit=100)]
        members_cache = mems

    return random.choice(members_cache)


@client.event
async def on_message(msg: discord.Message):
    # ignore bot messages and dms
    if msg.author.bot or not msg.guild or msg.guild.id != GUILD_ID:
        return

    wh = await get_or_make_wh(msg.channel)
    target_mem = await get_rand_guild_mem(msg.guild)

    await wh.send(
        content=msg.content,
        username=target_mem.display_name,
        avatar_url=target_mem.display_avatar.url,
        embeds=msg.embeds,
    )

    await msg.delete()
    return
