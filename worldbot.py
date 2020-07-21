#!/usr/bin/env python3

import time

# Bot state
p2p_worlds = [1,2,4,5,6,9,10,12,14,15,16,21,22,23]
worlds_state = dict()

class World:
    def __init__(self, num, loc, tents, time, remarks):
        self.num = None
        self.loc = None
        self.tents = None
        self.time = None
        self.remarks = None
        self.is_safe = True
        self.unsafe_reason = ''
        self.scouted = False
        self.set_vars(num, loc, tents, time, remarks)

    def __str__(self):
        return '{} {} {} {} {}'.format(
            self.world, self.loc, self.tents, self.time, self.remarks)

    def set_tents(self, tents):
        if not all(c in 'mhcsf' for c in tents):
            raise ValueError('{} are not valid tents'.format(tents))
        self.tents = tents

    def set_vars(self, num=None, loc=None, tents=None, time=None, remarks=None):
        if num:
            if num not in p2p_worlds:
                raise ValueError('{} is invalid or blacklisted'.format(world))
            self.num = num
        if loc:
            if loc.lower() not in ['dwf', 'elm', 'rdi']:
                raise ValueError('{} is not a valid loc (elm, dwf, rdi)'.format(loc))
            self.loc = loc
        if tents:
            if len(tents) != 3 and not all(c in 'mchsf' for c in tents):
                raise ValueError('{} are not valid tents'.format(tents))
            self.tents = tents
        if time:
            self.time = time
        if remarks:
            self.remarks = remarks

    def beam(self, tents, time=None, remarks=None):
        self.set_vars(tents=tents, time=time, remarks=remarks)
        self.scouted = True

    def mins_remaining(self):
        return 'TODO mins'

def create_world(num, loc, tents=None, time=None, remarks=None):
    # TODO: validate time

    worlds_state[num] = World(num, loc, tents, time, remarks)

def get_uncalled_worlds(ws):
    return [str(w) for w in p2p_worlds if w not in ws.keys()]

# Commands, seperated out for testing without going through discord
def set_world_state(num:int, loc, tents, time, remarks):
    if not worlds_state.get(num):
        create_world(num, loc, tents, time, remarks)

    ws = worlds_state[num]
    if loc or tents or time or remarks:
        ws.scouted = True

def call_world(num:int, loc):
    create_world(num, loc)

def list_uncalled():
    msg = 'Uncalled worlds: ' + ','.join(get_uncalled_worlds(worlds_state)) + '\n\n'
    return msg

def current_status():
    def get_filtered_worlds(scouted, loc, f):
        return [f(w) for w in worlds_state.values() if w.scouted == scouted and w.loc == loc]
    def get_summary_msg(world):
        return '{} {} {} {}'.format(world.num, world.tents, world.mins_remaining(), world.remarks)
    def get_world_num(world):
        return str(world.num)

    unscouted_dwfs = get_filtered_worlds(False, 'dwf', get_world_num)
    unscouted_elms = get_filtered_worlds(False, 'elm', get_world_num)
    unscouted_rdis = get_filtered_worlds(False, 'rdi', get_world_num)
    summary_dwfs = get_filtered_worlds(True, 'dwf', get_summary_msg)
    summary_elms = get_filtered_worlds(True, 'elm', get_summary_msg)
    summary_rdis = get_filtered_worlds(True, 'rdi', get_summary_msg)

    output = 'Uncalled worlds: ' + ','.join(get_uncalled_worlds(worlds_state)) + '\n\n'
    output += 'Unscouted:\n'
    output += 'dwf: ' + ','.join(unscouted_dwfs) + '\n'
    output += 'elm: ' + ','.join(unscouted_elms) + '\n'
    output += 'rdi: ' + ','.join(unscouted_rdis) + '\n\n'
    output += 'Scouted:\n'
    output += 'dwf:\n' + '\n'.join(summary_dwfs) + '\n'
    output += 'elm:\n' + '\n'.join(summary_elms) + '\n'
    output += 'rdi:\n' + '\n'.join(summary_rdis) + '\n'

    return output

def mark_beamed(num:int, loc, tents, time=None, remarks=None):
    if not worlds_state.get(num):
        create_world(num, loc, tents, time, remarks)

    worlds_state[num].beam(tents, time, remarks)
    return

def restore_state():
    worlds_state = dict()
    return

def wipe_world_info(num:int):
    if worlds_state.get(num):
        del worlds_state[num]

import discord
from discord.ext import commands

bot = commands.Bot(command_prefix='.')

# Only operate on specific channel
@bot.check
async def only_listen_in_channel(ctx):
    return ctx.message.channel.id == 735132015782920293 and ctx.message.author is not bot.user

@bot.listen('on_ready')
async def on_ready():
    print('Logged is as {}'.format(bot.user))

@bot.listen('on_command_error')
async def on_command_error(ctx, err):
    print(ctx, type(err), err)

@bot.command(name='w')
async def command_call_world(ctx, num:int, loc):
    call_world(num, loc)

@bot.command(name='list')
async def command_list_worlds(ctx):
    await ctx.send(current_status())

@bot.command(name='beamed')
async def command_beam_world(ctx, num:int, loc, tents, time=None, remarks=None):
    mark_beamed(num, loc, tents, time, remarks)

@bot.command(name='u')
async def command_list_uncalled(ctx):
    await ctx.send(list_uncalled())

@bot.command(name='remove')
async def command_del_world(ctx, num:int):
    wipe_world_info(num)

@bot.command(name='debug')
async def command_debug(ctx):
    await ctx.send(worlds_state)

import sys
if len(sys.argv) < 2:
    print("Usage: ./worldbot.py <token>")

bot.run(sys.argv[1])
