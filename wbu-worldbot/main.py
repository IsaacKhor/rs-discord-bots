#!/usr/bin/env python3

import aiohttp, discord
import discord.ext.commands as discordbot
import commands, wbubot

def main(token: str):
    # Set up discord client
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    conn = aiohttp.TCPConnector(ssl=False)
    client = discordbot.Bot(connector=conn, command_prefix='.', intents=intents)

    msglog = open('messages.log', 'a', encoding='utf-8')
    botlog = open('bot.log', 'a', encoding='utf-8')

    bot = wbubot.WbuBot(client, msglog, botlog)
    commands.register_commands(client, bot)

    client.run(token)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: ./worldbot-discord.py <token>")
    main(sys.argv[1])
