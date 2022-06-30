#!/usr/bin/env python3

import aiohttp, discord
from discord.ext import commands
from wbubot import WbuBot

def main(token: str):
    # Set up discord client
    intents = discord.Intents.default()
    intents.members = True
    conn = aiohttp.TCPConnector(ssl=False)
    client = commands.Bot(connector=conn, command_prefix='.', intents=intents)

    msglog = open('messages.log', 'a', encoding='utf-8')
    botlog = open('bot.log', 'a', encoding='utf-8')
    bot = WbuBot(client, msglog, botlog)
    bot.run(token)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: ./worldbot-discord.py <token>")
    main(sys.argv[1])
