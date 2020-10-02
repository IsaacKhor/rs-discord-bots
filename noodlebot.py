#!/usr/bin/env python3

import discord
import discord.ext.commands as commands
import aiohttp
import random
import math
import re

PRIV_CHANNEL = ['scout-channel', 'crashing-of-the-bands']
CHANNELS = PRIV_CHANNEL + ['botspam']

HELP_STRING = """
Noodlebot help:

**Commands**:
- **.help** - what you're looking at right now
- **.w [world numbers]** - marks one or more worlds as alive (have a wyrm)
- **.rm [world numbers]** - marks one or more worlds as dead (no wyrm)
- **.clear** - marks all worlds as dead
- **.debug** - print internal state
- **.list** - list all active worlds
- **.rollnew** - mark current world as dead and set current to new random world
- **.reroll** - set current to new random world
- **.cur** - outputs current world
"""

P2P_WORLDS = [
1,2,4,5,6,9,10,12,14,15,16,
21,22,23,24,25,26,27,28,30,31,32,35,36,37,39,
40,42,44,45,46,47,48,49,50,51,52,53,54,56,58,59,
60,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,
82,83,84,85,86,87,88,89,91,92,96,97,98,99,
100,102,103,104,105,106,114,115,116,117,118,119,
121,123,124,134,137,138,139,140]

class InvalidChannelErr(commands.CommandError):
    pass


def is_restricted_channel(ctx):
    return type(ctx.channel) == discord.TextChannel and ctx.channel.name in PRIV_CHANNEL


async def restricted_channel_check(ctx):
    if is_restricted_channel(ctx):
        return True
    else:
        raise InvalidChannelErr()


class NoodleBot(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self._worlds = set()
        self._active_world = -1
        self._history = list()

    def get_current(self):
        return self._active_world

    def set_current(self, world):
        self._active_world = world

    def get_random_active(self):
        if self.worlds_remaining() == 0:
            return -1
        return random.sample(self._worlds, 1)[0]

    def get_active(self):
        return list(self._worlds)

    def set_active(self, *worlds):
        new_worlds = set(worlds).difference(self._worlds)
        self._worlds.update(worlds)
        return new_worlds

    def set_dead(self, *worlds):
        removed_worlds = self._worlds.intersection(set(worlds))
        for w in worlds:
            self._worlds.discard(w)
        return removed_worlds

    def get_history(self):
        return self._history

    def add_to_history(self, world):
        self._history.append(world)

    def worlds_remaining(self):
        return len(self._worlds)

    def get_abbrev_state(self):
        worlds = [str(x) for x in sorted(self._worlds)]
        if len(worlds) == 0:
            return 'No worlds available :('
        return f'{len(worlds)} worlds available. Current: {self._active_world}\n' + ', '.join(worlds)

    def __str__(self):
        return f'Worlds: {self._worlds}\nActive: {self._active_world}\nHistory: {self._history}'


conn = aiohttp.TCPConnector(ssl=False)
client = commands.Bot(
    command_prefix = ['.', '/'],
    case_insensitive = True,
    self_bot = False,
    connector = conn)
noodlebot = NoodleBot()
msglog = open('messages.log', 'a')


@client.event
async def on_ready():
    print('Logged is as {}'.format(client.user))


@client.event
async def on_command_error(ctx, err):
    if isinstance(err, InvalidChannelErr):
        await ctx.send("ERROR: this command cannot be used in this channel")
    elif isinstance(err, commands.errors.CommandNotFound):
        return
    else:
        await ctx.send(f'{type(err)}\n {str(err)}')


@client.command(
    name='w',
    aliases=['alive', 'world', 'add'],
    help='marks given worlds as alive')
async def mark_alive(ctx, *, worlds):
    toks = re.split('\n| |,|;', worlds)
    wl = [int(x) for x in toks if x.isnumeric()]
    invalid_worlds = [x for x in wl if x not in P2P_WORLDS]

    if len(invalid_worlds) > 0:
        await ctx.send(f'These worlds are not valid: {invalid_worlds}. Action aborted and no worlds added.')
        return

    added = noodlebot.set_active(*wl)
    msg = f'Successfully added {added}'
    if is_restricted_channel(ctx):
        msg += '\n' + noodlebot.get_abbrev_state()

    await ctx.send(msg)


@client.command(
    name='rm',
    aliases=['dead', 'remove'],
    help='marks given worlds as dead')
async def mark_dead(ctx, *, worlds):
    toks = re.split('\n| |,|;', worlds)
    wl = [int(x) for x in toks if x.isnumeric()]
    removed = noodlebot.set_dead(*wl)

    msg = f'Successfully removed {removed} from list'
    if is_restricted_channel(ctx):
        msg += '\n' + noodlebot.get_abbrev_state()

    await ctx.send(msg)


@client.command(name='clear', help='reset bot state')
@commands.check(restricted_channel_check)
async def clear_all_worlds(ctx, *worlds):
    noodlebot.reset()
    await ctx.send('Bot state successfully reset')


@client.command(name='debug', help='list debug info')
@commands.check(restricted_channel_check)
async def get_state(ctx):
    await ctx.send(str(noodlebot))


@client.command(name='list', help='list active worlds')
@commands.check(restricted_channel_check)
async def list_active_worlds(ctx):
    await ctx.send(noodlebot.get_abbrev_state())


@client.command(name='rollnew', help='mark old active world as dead and roll a new one')
@commands.check(restricted_channel_check)
async def mark_and_roll(ctx):
    old_world = noodlebot.get_current()
    noodlebot.set_dead(old_world)
    new_world = noodlebot.get_random_active()
    noodlebot.add_to_history(old_world)

    if new_world == -1:
        await ctx.send('No more worlds. Wave over :(')
        return

    noodlebot.set_current(new_world)
    await ctx.send(f'Next world: {new_world}. Marked {old_world} as dead\n' + noodlebot.get_abbrev_state())


@client.command(name='reroll', help='set active world to new random')
@commands.check(restricted_channel_check)
async def roll_new_world(ctx):
    new_world = noodlebot.get_random_active()
    noodlebot.set_current(new_world)

    if new_world == -1:
        await ctx.send('No more worlds :(')
    else:
        await ctx.send(f'Next world: {new_world}\n' + noodlebot.get_abbrev_state())


@client.command(
    name='cur',
    aliases=['current'],
    help='get current active world and number of worlds remaining')
async def get_current_world(ctx):
    await ctx.send(f'Current world: {noodlebot.get_current()}. {noodlebot.worlds_remaining()} worlds remaining.')


@client.command(name='split', help='split world list for scouts')
async def split_world_list(ctx, chunks:int):
    msg = f'Splitting worldlist into {chunks} chunks\n'
    size = math.ceil(len(P2P_WORLDS)/chunks)

    j = 0
    for i in range(0, len(P2P_WORLDS), size):
        j+=1
        msg += f'{j}: {P2P_WORLDS[i:i+size]}\n'

    await ctx.send(msg)


@client.command(name='pet', help='pet the noodle')
async def pet(ctx):
    await ctx.send('*pets noodle*')


@client.check
async def valid_channels(ctx):
    is_dm = type(ctx.channel) == discord.DMChannel
    is_valid_textchannel = type(ctx.channel) == discord.TextChannel and ctx.channel.name in CHANNELS
    return is_dm or is_valid_textchannel


import sys
if len(sys.argv) < 2:
    print("Usage: ./noodlebot.py <token>")

client.run(sys.argv[1])
