#!/usr/bin/env python3

from botcore import *
import discord
import aiohttp

BOT_CHANNEL = 790404971220041748
WAVE_VOICE = 780814756713594951

CHANNELS = [BOT_CHANNEL]

help_string = """
Worldbot instructions:

**Commands**:
- **list** - lists summary of current status
- **.help** - show this help message
- **.reset** - reset bot for next wave
- **.debug** - show debug information
- **.clean** - cleanup bot's own messages

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
- **'xx:xx'** if 'gc' or 'mins' is not specified its assumed to be gameclock

So for example:
- '119dwf 10gc' marks world as dying in 10\\*0.6=6 minutes
- '119 mhs 4mins' marks the world as dying in 4 minutes
- '28 dead'
- '84 beamed02 hcf clear', you can combine multiple commands
"""

md_format_str = """
**Active** (unknown, *beaming*, __5 mins__, ~~<5mins~~):
**DWF**: {}
**ELM**: {}
**RDI**: {}
**UNK**: {}

**Dead**: {}

**Summary (world/location/tents/time rem./remarks)**
{}
"""

def fmt_summary_num(world):
    if world.state == WorldState.BEAMING:
        return '*{}*'.format(world.num)
    t = world.get_remaining_time()
    if t == -1:
        return str(world.num)
    if t.mins >= 5:
        return '__{}__'.format(world.num)
    return '~~{}~~'.format(world.num)


conn = aiohttp.TCPConnector(ssl=False)
client = discord.Client(connector=conn)
worldbot = WorldBot()

def get_botchannel():
    return client.get_channel(790404971220041748)


@client.event
async def on_ready():
    print('Logged is as {}'.format(client.user))
    await get_botchannel().send('Bot starting up')


@client.event
async def on_command_error(err):
    print(type(err), err)


@client.event
async def on_message(message):
    if message.author == client.user or not (message.channel.id in CHANNELS):
        return

    # Commands:
    # - 'list': list summary of state
    # - 'help': show help
    # - 'reset': reset bot state
    # - 'debug': show debug info
    # - others

    cmd = message.content.strip().lower()
    retmsg = None
    try:
        if cmd == '.help' or cmd == '.halp':
            retmsg = help_string
        elif cmd == 'list':
            worldbot.update_world_states()
            retmsg = worldbot.get_current_status(md_format_str, fmt_summary_num)
        elif cmd == '.debug':
            worldbot.update_world_states()
            retmsg = worldbot.get_debug_info()
        elif cmd == '.reset':
            worldbot.reset_worlds()
            retmsg = 'Worlds successfully reset'
        elif cmd == '.clean':
            await message.channel.purge(limit=100, 
                check=lambda m: m.author == client.user,
                bulk=True)
        else:
            parse_update_command(cmd, worldbot)
    except Exception as e:
        retmsg = str(type(e)) + str(e)

    if retmsg:
        # Channel can be either worldbot channel or DM channel
        await message.channel.send(retmsg)


@client.event
async def on_voice_state_update(member, before, after):
    print(f'{member.nick} before in {before.channel} after {after.channel}')

    # Keep track of people leaving WBS voice
    if (before.channel and 
        before.channel.id == 780814756713594951 and
        after.channel == None):
        print(f'User {member.nick} left voice')
        await get_botchannel().send(f'User {member.nick} left voice')


import sys
if len(sys.argv) < 2:
    print("Usage: ./worldbot-discord.py <token>")

client.run(sys.argv[1])
