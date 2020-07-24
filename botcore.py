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
            return f'[i]{self.num}[/i]'

        t = self.get_remaining_time()
        if t == -1:
            return str(self.num)
        if t.mins >= 5:
            return '[u]{}[/u]'.format(self.num)
        return '[color=red]{}[/color]'.format(self.num)

    def update_state(self, curtime):
        if not self.time:
            return
        if self.state == WorldState.ALIVE and curtime >= self.time:
            self.state = WorldState.DEAD


P2P_WORLDS = [1,2,4,5,6,9,10,12,14,15,16,21,22,23]

class WorldBot:
    def __init__(self, helpstr='TODO: helpstring'):
        self._registry = None
        self._helpstr = helpstr
        self.reset_worlds()

    def get_world(self, num):
        if num not in P2P_WORLDS:
            raise ValueError('{} world is not valid'.format(num))
        return self._registry[num]

    def get_worlds(self):
        return self._registry.values()

    def reset_worlds(self):
        self._registry = dict()
        for num in P2P_WORLDS:
            self._registry[num] = World(num)

        return self._registry

    def update_world(self, num, loc, state, tents, time, notes, is_safe, is_scouted):
        world = self.get_world(num)
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
    def get_current_status(self, bbcode=True):
        bbcode_format = """
[b]Active[/b] (unknown, [i]beaming[/i], [u]>5 mins[/u], [color=red]<5mins[/color]:
[b]DWF[/b]: {}
[b]ELM[/b]: {}
[b]RDI[/b]: {}
[b]UNK[/b]: {}

[b]Dead[/b]: {}

[b]Summary of active worlds (world / location / tents / time remaining / remarks[/b]
{}
        """
        worlds = self.get_worlds()

        def get_active_for_loc(loc, joinchar):
            return joinchar.join([w.get_formatted_number() for w in worlds 
                if w.loc == loc and w.state != WorldState.DEAD])

        dead_str = ','.join([str(w.num) for w in worlds if w.state == WorldState.DEAD])
        active_dwfs = get_active_for_loc(Location.DWF, ',')
        active_elms = get_active_for_loc(Location.ELM, ',')
        active_rdis = get_active_for_loc(Location.RDI, ',')
        active_unks = get_active_for_loc(Location.UNKNOWN, ',')

        all_active = [w for w in worlds if w.state == WorldState.ALIVE]
        all_active = sorted(all_active, key=lambda w: w.time, reverse=True)
        all_active_str = '\n'.join(map(lambda w: w.get_summary(), all_active))

        return bbcode_format.format(active_dwfs, active_elms,
            active_rdis, active_unks, dead_str, all_active_str)

    def get_debug_info(self):
        return str(self._registry)

    def get_help_info(self):
        return self._helpstr

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

NUM_PAT = re.compile(r'^(\d+)')

def parse_update_command(s, botstate):
    def is_location(tok):
        return tok in ['dwf', 'elm', 'rdi', 'unk']

    def is_tents(tok):
        return len(tok) == 3 and all(c in 'mhcsf' for c in tok)

    def remove_beginning(item, tok):
        if tok.startswith(item):
            return tok[len(item):].lstrip(' :')
        return tok

    def get_beg_number(s):
        num, string = match_beginning(NUM_PAT, s)
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

    s = s.strip().lower()

    # Try to match number at beginning of string
    m = re.match(NUM_PAT, s)
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

    # print('[LOG]: updating {}/{}/{}/{}/{}/{}/{}/{}'.format(
    #     world_num, loc, state, tents, time, notes, is_safe, is_scouted))
    botstate.update_world(world_num, loc, state, tents, time, notes, 
        is_safe, is_scouted)
