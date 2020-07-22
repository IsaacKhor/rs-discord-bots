#!/usr/bin/env python3

import time, sys, string, re, datetime, functools
from enum import Enum, auto

class WorldState(Enum):
    UNCALLED = 'uncalled'
    BEAMING = 'beaming'
    ALIVE = 'active'
    DEAD = 'dead'

    def __str__(self):
        return self.value

class Location(Enum):
    DWF = 'dwf'
    ELM = 'elm'
    RDI = 'rdi'
    UNKNOWN = 'unk.'

    def __str__(self):
        return self.value

# Reimplement time because we only care about mins/secs
# and using python's datetime lib just makes things unneccesarily complicated
@functools.total_ordering
class WbsTime():
    @staticmethod
    def current():
        t = datetime.datetime.now().time()
        return WbsTime(t.minute, t.second)

    @staticmethod
    def get_abs_minute_or_cur(min):
        if not min:
            return WbsTime.current()
        return WbsTime(int(min), 0)

    def __init__(self, mins, secs):
        total_secs = mins*60 + secs
        m,s = divmod(total_secs, 60)
        self.mins, self.secs = int(m), int(s)

    def add(self, other):
        if not other:
            return self
        return WbsTime(self.mins + other.mins, self.secs + other.secs)

    def add_mins(self, mins):
        if not mins:
            return self
        return WbsTime(self.mins + mins, self.secs)

    def time_until(self, other):
        a = self.mins*60 + self.secs
        b = other.mins*60 + other.secs
        secs_diff = max(b - a, 0)
        m, s = divmod(secs_diff, 60)
        return WbsTime(int(m),int(s))

    def __str__(self):
        return f'{self.mins}:{self.secs:02}'

    def __repr__(self):
        return self.__str__()

    def __gt__(self, other):
        if self.mins == other.mins:
            return self.secs > other.secs
        return self.mins > other.mins

    def __eq__(self, other):
        if not isinstance(other, WbsTime):
            return False
        return self.mins == other.mins and self.secs == other.secs

class World():
    def __init__(self, num):
        self.num = num
        self.loc = Location.UNKNOWN
        self.state = WorldState.UNCALLED
        self.tents = None
        self.time = None # Estimated death time
        self.notes = None
        self.is_safe = True
        self.is_scouted = False

    def __str__(self):
        return '{} {} {} {} {} {} {} {}'.format(
            self.num, self.loc, self.state, self.tents, 
            self.time, self.notes, self.is_safe, self.is_scouted)

    def __repr__(self):
        return self.__str__()

    def get_summary(self):
        return f'{self.num} {self.loc} {self.tents} {self.get_remaining_time_str()} {self.notes}'

    def get_remaining_time(self):
        if not self.time:
            return -1
        return WbsTime.current().time_until(self.time)

    def get_remaining_time_str(self):
        t = self.get_remaining_time()
        if t == -1:
            return 'unknown'
        return str(t)

    def get_formatted_number(self):
        if self.state == WorldState.BEAMING:
            return f'*{self.num}*'

        t = self.get_remaining_time()
        if t == -1:
            return str(self.num)
        if t.mins >= 5:
            return '__{}__.'.format(self.num)
        return '~~{}~~'.format(self.num)

    def update_state(self, curtime):
        if not self.time:
            return
        if self.state == WorldState.ALIVE and curtime >= self.time:
            self.state = WorldState.DEAD

p2p_worlds = [1,2,4,5,6,9,10,12,14,15,16,21,22,23]
worlds_registry = dict()

def get_world(num):
    if num not in p2p_worlds:
        raise ValueError('{} world is not valid'.format(num))
    return worlds_registry[num]

def reset_worlds():
    global worlds_registry
    worlds_registry = dict()
    for num in p2p_worlds:
        worlds_registry[num] = World(num)

    return worlds_registry

def update_world(num, loc, state, tents, time, notes, is_safe, is_scouted):
    world = get_world(num)
    if loc:
        world.loc = loc
    if state:
        world.state = state
    if tents:
        world.tents = tents
    if time:
        world.time = time
    if notes:
        world.notes = notes
    if is_safe:
        world.is_safe = is_safe
    if is_scouted:
        world.is_scouted = is_scouted

# Summary output
output_format = """
**Uncalled**: {}

**Active** (unknown, *beaming*, __>5 mins__, ~~<5mins~~:
**DWF**: {}
**ELM**: {}
**RDI**: {}
**UNK**: {}

**Dead**: {}

**Summary of active worlds (world / location / tents / time remaining / remarks**
{}
"""
def current_status():
    worlds = worlds_registry.values()

    def get_active_for_loc(loc, joinchar):
        return joinchar.join([w.get_formatted_number() for w in worlds if w.loc == loc])

    uncalled_str = ','.join([str(w.num) for w in worlds if w.state == WorldState.UNCALLED])
    dead_str = ','.join([str(w.num) for w in worlds if w.state == WorldState.DEAD])

    active_dwfs = get_active_for_loc(Location.DWF, ',')
    active_elms = get_active_for_loc(Location.ELM, ',')
    active_rdis = get_active_for_loc(Location.RDI, ',')
    active_unks = get_active_for_loc(Location.UNKNOWN, ',')

    all_active = [w for w in worlds if w.state == WorldState.ALIVE]
    all_active = sorted(all_active, key=lambda w: w.time, reverse=True)
    all_active_str = '\n'.join(map(lambda w: w.get_summary(), all_active))

    return output_format.format(uncalled_str, active_dwfs, active_elms,
        active_rdis, active_unks, dead_str, all_active_str)

# Commands supported:
# - 119dwf hcf beamed :02 clear
#   - the "dwf" is optional as long as it's previously stated
# - 119 rdi hcf 10:00gc clear
#   - space between world and location optional
# - 119 hcf dies :17 clear
#   - will treat as dying at :17 exactly
# - 119 dead
#   - marks words as dead
# Notes:
# - MUST begin with numbers, followed by optional space
# - In any order and amount: location, tents, "beamed :xx", "dies :xx", 
#   "xx:xx gc", "dead", "unsafe", "safe", "beaming"
# - Everything else goes into "notes"
# - The finite state automaton almost writes itself

num_pat = re.compile(r'^(\d+)')

def get_beg_number(s):
    num, string = match_beginning(num_pat, s)
    if num:
        num = int(num)
    return num, string

def match_beginning(pat, s):
    m = re.match(pat, s)
    if not m:
        return None, s
    else:
        return m.group(), s[m.span()[1]:].lstrip(' :')

def convert_location(tok):
    if tok == 'rdi':
        return Location.RDI
    if tok == 'elm':
        return Location.ELM
    if tok == 'dwf':
        return Location.DWF
    return Location.UNKNOWN

def parse_command(s):
    def is_location(tok):
        return tok in ['dwf', 'elm', 'rdi', 'unk']

    def is_tents(tok):
        return len(tok) == 3 and all(c in 'mhcsf' for c in tok)

    def remove_beginning(item, tok):
        if tok.startswith(item):
            return tok[len(item):].lstrip(' :')
        return tok

    s = s.strip().lower()

    # Try to match number at beginning of string
    m = re.match(num_pat, s)
    if not m:
        return
    world_num = int(m.group())

    # Consume the world number and optional whitespace
    s = s[m.span()[1]:].lstrip()

    # Determine updates (possible: location, state, tents, time, notes)
    loc, state, tents, time, notes, is_safe, is_scouted = None,None,None,None,None,None,None

    cmd = s
    while cmd:
        # print('[DEBUG] parsing "{}", 0:3 is "{}"'.format(cmd, cmd[0:3]))
        if cmd.startswith('dead'):
            state = WorldState.DEAD
            is_scouted = True
            cmd = remove_beginning('dead', cmd)
            continue
        elif cmd.startswith('unsafe'):
            is_safe = False
            is_scouted = True
            cmd = remove_beginning('unsafe', cmd)
            continue
        elif cmd.startswith('beaming'):
            state = WorldState.BEAMING
            cmd = remove_beginning('beaming', cmd)
            continue
        elif is_tents(cmd[0:3]):
            tents = cmd[0:3]
            is_scouted = True
            cmd = cmd[3:].lstrip()
            continue
        elif is_location(cmd[0:3]):
            loc = convert_location(cmd[0:3])
            cmd = cmd[3:].lstrip()
            continue

        # Syntax: 'beamed :02', space, colon, and time all optional
        elif cmd.startswith('beamed'):
            cmd = remove_beginning('beamed', cmd)
            num, cmd = get_beg_number(cmd)

            time = WbsTime.get_abs_minute_or_cur(num).add_mins(10)
            state = WorldState.ALIVE
            is_scouted = True
            continue

        # Syntax: 'broken :02', same syntax as beamed
        elif cmd.startswith('broken'):
            cmd = remove_beginning('broken', cmd)
            num, cmd = get_beg_number(cmd)

            time = WbsTime.get_abs_minute_or_cur(num).add_mins(5)
            state = WorldState.ALIVE
            is_scouted = True
            continue

        # Syntax: 'dies :05'
        elif cmd.startswith('dies'):
            cmd = remove_beginning('dies', cmd)
            num, cmd = get_beg_number(cmd)
            if not num:
                continue

            time = WbsTime(int(num), 0)
            state = WorldState.ALIVE
            is_scouted = True
            continue

        # Syntax: 'xx:xx gc', the seconds and gc part optional
        # Uses gameclock by default. To override use 'mins' postfix
        elif cmd[0].isnumeric():
            mins, cmd = get_beg_number(cmd)
            secs, cmd = get_beg_number(cmd)
            secs = secs if secs else 0

            if cmd.startswith('mins'):
                cmd = remove_beginning('mins', cmd)
            else:
                cmd = remove_beginning('gc', cmd)
                ticks = mins*60 + secs
                total_secs = ticks*0.6
                mins, secs = divmod(total_secs, 60)

            time = WbsTime.current().add(WbsTime(int(mins), int(secs)))
            state = WorldState.ALIVE
            is_scouted = True
            continue

        # Everything after first unrecognised token are notes
        else:
            notes = cmd
            cmd = ''

    print('[LOG]: updating {}/{}/{}/{}/{}/{}/{}/{}'.format(
        world_num, loc, state, tents, time, notes, is_safe, is_scouted))
    update_world(world_num, loc, state, tents, time, notes, is_safe, is_scouted)

# Testing script
reset_worlds()
# parse_command('22 dwf')
# parse_command('22 hcf 9:20')
# parse_command('4rdi beamed :03')
# parse_command('6 dead')

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

import discord

client = discord.Client()

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
        await message.channel.send(current_status())
    elif cmd == 'debug':
        await message.channel.send(str(worlds_registry))
    elif cmd == 'reset':
        reset_worlds()
        await message.channel.send('Worlds successfully reset')
    else:
        parse_command(cmd)

import sys
if len(sys.argv) < 2:
    print("Usage: ./worldbot.py <token>")

client.run(sys.argv[1])
