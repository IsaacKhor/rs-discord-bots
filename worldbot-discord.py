#!/usr/bin/env python3

from botcore import *
import discord

help_string = """
Worldbot instructions:

**Commands**:
- **list** - lists summary of current status
- **help** - show this help message
- **reset** - reset bot for next wave
- **debug** - show debug information
- ~~**remove <world>** - reset information for specified world~~ NOT IMPLEMENTED
  use '119unk' instead (for 119 unknown)

**Scouting commands** - The bot accepts any commands starting with a number
followed by any of the following (spaces are optional for each command):
- **'dwf|elm|rdi|unk'** will update the world to that location, 'unk' is unknown
- **'dead'** will mark the world as dead
- **'unsafe'** will mark the world as unsafe
- **'beaming'** will mark the world as being actively beamed
- Any combination of 3 of 'hcmfs' to add the world's tents
- **'beamed :02'** to mark world as beamed at 2 minutes past the hour.
- **'beamed'** with no number provided bot uses current time
- **'dies :07'** marks the world as dying at :07
- **'xx:xx gc'** for 'xx:xx' remaining on the game clock. The seconds part is optional
- **'xx:xx mins'** for xx:xx remaining in real time. The seconds part is optional
- **'xx:xx' if 'gc' or 'mins' is not specified its assumed to be gameclock

So for example:
- '119dwf 10gc' marks world as dying in 10\\*0.6=6 minutes
- '119 mhs 4mins' marks the world as dying in 4 minutes
- '28 dead'
- '84 beamed02 hcf clear', you can combine multiple commands
"""


client = discord.Client()
worldbot = WorldBot()

@client.event
async def on_ready():
    print('Logged is as {}'.format(client.user))

@client.event
async def on_command_error(err):
    print(type(err), err)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Commands:
    # - 'list': list summary of state
    # - 'help': show help
    # - 'reset': reset bot state
    # - 'debug': show debug info
    # - others

    cmd = message.content.strip()

    if cmd == 'help':
        await message.channel.send(help_string)
    elif cmd == 'list':
        await message.channel.send(worldbot.current_status())
    elif cmd == 'debug':
        await message.channel.send(str(worldbot.get_registry()))
    elif cmd == 'reset':
        reset_worlds()
        await message.channel.send('Worlds successfully reset')
    else:
        parse_command(cmd)

import sys
if len(sys.argv) < 2:
    print("Usage: ./worldbot-discord.py <token>")

client.run(sys.argv[1])
