import re, functools, pprint
import traceback, inspect, math, pytz, os, json
from datetime import datetime, timezone, timedelta
from enum import Enum

VERSION = '3.9.5'
NUM_PAT = re.compile(r'^(\d+)')
DEFAULT_FC = 'Wbs United'
P2P_WORLDS = [
1,2,4,5,6,9,10,12,14,15,16,18,
21,22,23,24,25,26,27,28,30,31,32,35,36,37,39,
40,42,44,45,46,47,48,49,50,51,52,53,54,56,58,59,
60,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,
82,83,84,85,86,87,88,89,91,92,96,97,98,99,
100,102,103,104,105,106,114,115,116,117,118,119,
121,123,124,134,137,138,139,140,
252,257,258,259]

EASTER_EGGS = {
    'wtf is the fc': 'User is not a nice person. This incident will be reported. Especially Kyle. That guy\'s evil',
    '!wbu': '75/75 or silently refunds you',
    '!ally': 'Gatorrrrrrrrrr',
    '!faery': 'Language! biaatch',
    '!sever': 'Who is sever squad?',
    '!apk': 'Sorry buddy, APK is dead. Maybe the radiation got them',
    '!il': 'ts3server://illuzionwbs.teamspeak.vg',
    '!lat': 'Who?',
    '!rpk': 'Who?',
    '!take': 'Not implemented. Feel free to scout whatever world you want',
    '.wbu': '75/75 or silently refunds you',
    '.ally': 'Gatorrrrrrrrrr',
    '.faery': 'Language! biaatch',
    '.sever': 'Who is sever squad?',
    '.apk': 'Sorry buddy, APK is dead. Maybe the radiation got them',
    '.il': 'ts3server://illuzionwbs.teamspeak.vg',
    '.lat': 'Who?',
    '.rpk': 'Who?',
    '.take': 'Not implemented. Feel free to scout whatever world you want'
}

HELP_STRING = ["""
**Worldbot instructions:**

**Commands**:
- **list** - lists summary of current status
- **.help** - show this help message
- **.debug** - show debug information
- **.version** - shows the current version of the bot
- **.wbs** - shows the time of the next wave
- **.ignoremode** - enter ignore mode. Ignores all messages.

**Wave management commands** - keep track of people
- **.host** - set yourself as host
- **.scout** - add yourself to the list of scouts
- **.anti** - add yourself to the list of anti
- **.reset** - reset bot for next wave. Also produces the wave summary
- **.fc <fcname>** - sets active fc
- **fc?** - shows current fc set by '.fc'
- **.call <world loc>** - adds <world loc> to the call history.
""", """
**Scouting commands** - The bot accepts any commands starting with a number
followed by any of the following (spaces are optional for each command):
- **'dwf|elm|rdi|unk'** will update the world to that location, 'unk' is unknown
- **'dead'** will mark the world as dead
- **'dies :07'** marks the world as dying at :07
- **'beaming'** will mark the world as being actively beamed
- Any combination of 3 of 'hcmfs' to add the world's tents
- **'beamed :02'** to mark world as beamed at 2 minutes past the hour.
- **'beamed'** with no number provided bot uses current time
- **'xx:xx gc'** for 'xx:xx' remaining on the game clock. The seconds part is optional
- **'xx:xx mins'** for xx:xx remaining in real time. The seconds part is optional
- **'xx:xxm'** m is short for mins
- **'xx:xx'** if 'gc' or 'mins' is not specified its assumed to be gameclock
""" , """
Examples:
- `119dwf 10gc` marks world as dying in 10\\*0.6=6 minutes
- `119 mhs 4:30mins` marks the world as dying in 4:30 minutes real time
- `119 mhs 4` marks the world as dying in 4:00 gameclock
- `28 dead`
- `84 beamed02 hcf clear`, you can combine multiple commands
- `.call 10 dwf hcf` will add '10 dwf hcf' to the call history

Further notes:
- Spaces are optional between different information to update a world. That
  means `10elmhcf7` is just as valid as `10 elm hcf 7`.
- For all time inputs the colon and seconds part is optional. For example,
  both '7' and '7:15' are both perfectly valid times, but not '715'.

**Misc**
- There are a bunch of easter eggs if you know the old bot. Why don't you try some of them?
""", """
**FAQ**
1. What do I do if I put in the wrong info? (eg `53rdi` instead of `54rdi`)

Two things:
- `53unk` to update world 53 to unknown location
- `54rdi` to update 54 to rdi
"""
]

WBS_TIME_DB = {
    0: [2, 9, 16, 23],
    1: [6, 13, 20],
    2: [3, 10, 17],
    3: [0, 7, 14, 21],
    4: [4, 11, 18],
    5: [1, 8, 15, 22],
    6: [5, 12, 19],
}

def get_utctime():
    return datetime.now().astimezone(timezone.utc)

def get_next_wave_datetime(current):
    cur = current.astimezone(timezone.utc)
    day = cur.weekday()
    waves_today = WBS_TIME_DB[day]

    next_wave = None

    # Find the hour after the current one
    for wh in waves_today:
        actual_dt = cur.replace(hour=wh, minute=0, second=0, microsecond=0)
        if actual_dt > cur:
            return actual_dt

    # Next wave is tomorrow since we didn't find an hour
    if next_wave == None:
        tmr_weekday = (day + 1) % 7
        hr = WBS_TIME_DB[tmr_weekday][0]

        tomorrow = cur + timedelta(days=1)
        return tomorrow.replace(hour=hr, minute=0, second=0, microsecond=0)


def next_wave_info():
    cur = get_utctime()
    next_wave = get_next_wave_datetime(cur)

    deltasecs = (next_wave - cur).seconds
    deltahr = math.floor(deltasecs / 3600.0)
    deltamins = math.floor((deltasecs % 3600) / 60.0)

    TIME_FORMAT = '%H:00'
    n = next_wave

    def intz(time, zonename):
        return time.astimezone(pytz.timezone(zonename)).strftime(TIME_FORMAT)

    return inspect.cleandoc(
        f"""
        {deltahr}:{deltamins:02} until the next wave.

        Next wave is at:
        {intz(n, 'US/Eastern')} in US/Eastern
        {intz(n, 'US/Central')} in US/Central
        {intz(n, 'US/Pacific')} in US/Pacific
        {intz(n, 'Europe/Paris')} in EU/Central
        {intz(n, 'Europe/Sofia')} in EU/Eastern
        {intz(n, 'Europe/London')} in UK
        {intz(n, 'Singapore')} in UTC+8
        {intz(n, 'Australia/Melbourne')} in Australia/Eastern
        """)


class WorldState(Enum):
    NOINFO = 'uncalled'
    BEAMING = 'beaming'
    ALIVE = 'active'
    DEAD = 'dead'

    def __str__(self):
        return self.value

class Location(Enum):
    DWF = 'dwf'
    ELM = 'elm'
    RDI = 'rdi'
    UNKNOWN = 'unk'

    def __str__(self):
        return self.value

class Targetmode(Enum):
    PUBLIC = 'public'
    PRIVATE = 'private'

    def __str__(self):
        return self.value

class InvalidWorldErr(Exception):
    def __init__(self, world):
       super().__init__(f'World {world} is not a valid world')

# Reimplement time because we only care about mins/secs
# and using python's datetime lib just makes things unneccesarily complicated
@functools.total_ordering
class WbsTime():
    @staticmethod
    def current():
        t = datetime.utcnow().time()
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
        self.state = WorldState.NOINFO
        self.tents = None
        self.time = None # Estimated death time
        self.notes = None

    def __str__(self):
        return f'{self.num} {self.loc} {self.state}: {self.tents} {self.time} {self.notes}'

    def __repr__(self):
        return self.__str__()

    def __nonzero__(self):
        return self.loc == Location.UNKNOWN and self.state == WorldState.NOINFO \
            and self.tents == None and self.time == None and self.notes == None

    def get_remaining_time(self):
        if self.time == None:
            return -1
        return WbsTime.current().time_until(self.time)

    def get_line_summary(self):
        tent_str = '' if self.tents == None else self.tents
        notes_str = '' if self.notes == None else self.notes
        timestr = 'unknown' if self.time == None else str(self.get_remaining_time())
        return f'{self.num} {self.loc}:\t{timestr}\t{tent_str}\t{notes_str}'

    def get_num_summary(self):
        t = self.get_remaining_time()
        if self.state == WorldState.BEAMING:
            return f'*{self.num}*'
        elif t == -1:
            return f'{self.num}'
        elif t.mins >= 3:
            return f'__{self.num}__'
        else:
            return f'~~{self.num}~~'

    def update_state(self, curtime):
        if not self.time:
            return
        if self.state == WorldState.ALIVE and curtime >= self.time:
            self.state = WorldState.DEAD

    def should_show(self):
        # Show all worlds instead of hiding away worlds with no info
        # Discussion held 24 jun 2021, scouts wanted easy access to a list
        # of worlds for which we have no info instead of having to manually
        # check. This way it's apparent which worlds are available
        # for scouting
        return True
        # return not (self.state == WorldState.NOINFO and
        #         self.loc == Location.UNKNOWN and
        #         self.tents == None and
        #         self.time == None and
        #         self.notes == None)


SAVEFILE = './worldbot-state.json'
DEFAULT = {
    'upvotes': 0,
    'downvotes': 0,
}

class WorldBot:
    def __init__(self):
        self.reset_state()
        self.load_state()

    def reset_state(self):
        self._fcname = DEFAULT_FC
        self._host = ''
        self._antilist = set()
        self._scoutlist = set()
        self._worldhist = list()

        self._ignoremode = False
        self._registry = dict()

        for num in P2P_WORLDS:
            self._registry[num] = World(num)

    def is_ignoremode(self):
        return self._ignoremode

    def load_state(self):
        # Make sure file exists
        if not os.path.exists(SAVEFILE):
            with open(SAVEFILE, 'w') as f:
                json.dump(DEFAULT, f)

        with open(SAVEFILE, 'r') as f:
            try:
                m = json.load(f)
            except json.decoder.JSONDecodeError:
                m = DEFAULT

        self._upvotes = m['upvotes']
        self._downvotes = m['upvotes']

    def save_state(self):
        m = {'upvotes': self._upvotes, 'downvotes': self._downvotes}
        with open(SAVEFILE, 'w') as f:
            json.dump(m, f)

    def get_worlds_with_info(self):
        return [w for w in self._registry if w]

    def get_votes_summary(self):
        return f'Upvotes: {self._upvotes}, Downvotes: {self._downvotes}'

    def get_world(self, num):
        if num not in P2P_WORLDS:
            raise InvalidWorldErr(num)
        return self._registry[num]

    def get_worlds(self):
        return self._registry.values()

        for num in P2P_WORLDS:
            self._registry[num] = World(num)


    # Return true iff we actually update something
    def update_world(self, num, loc, state, tents, time, notes):
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

        if loc or state or tents or time or notes:
            return True

        return False

    def get_active_for_loc(self, loc):
        return ','.join([w.get_num_summary() for w in self.get_worlds()
            if w.loc == loc and w.should_show() and w.state != WorldState.DEAD])

    # Summary output
    def get_current_status(self):
        worlds = self.get_worlds()

        dead_str = ','.join([str(w.num) for w in worlds if w.state == WorldState.DEAD])
        active_dwfs = self.get_active_for_loc(Location.DWF)
        active_elms = self.get_active_for_loc(Location.ELM)
        active_rdis = self.get_active_for_loc(Location.RDI)
        active_unks = self.get_active_for_loc(Location.UNKNOWN)

        all_active = [w for w in worlds if w.state == WorldState.ALIVE]
        all_active = sorted(all_active, key=lambda w: w.time, reverse=True)
        all_active_str = '\n'.join([w.get_line_summary() for w in all_active])


        ret = inspect.cleandoc(f"""
        **Active** (unknown, *beaming*, __>3 mins__, ~~<3mins~~):
        **DWF**: {active_dwfs}
        **ELM**: {active_elms}
        **RDI**: {active_rdis}
        **UNK**: {active_unks}
        **Dead**: {dead_str}
        """)

        if all_active_str:
            ret += f'\n\n{all_active_str}'

        return ret

    def get_wave_summary(self):
        antistr = ', '.join(sorted(self._antilist))
        scoutstr = ', '.join(sorted(self._scoutlist))
        callhist = ', '.join(self._worldhist)
        ret = f"""
        Host: {self._host}
        Scouts: {scoutstr}
        Anti: {antistr}
        Worlds: {callhist}
        """
        return inspect.cleandoc(ret)

    def get_debug_info(self):
        return pprint.pformat(self._registry)

    def get_help_info(self):
        return HELP_STRING

    def is_registry_empty(self):
        return not any(w for w in self._registry.values())

    def update_world_states(self):
        curtime = WbsTime.current()
        for w in self.get_worlds():
            w.update_state(curtime)

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

    def parse_update_command(self, s):
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
        loc, state, tents, time, notes, = None,None,None,None,None

        cmd = s
        while cmd:
            if cmd.startswith('dead'):
                state = WorldState.DEAD
                cmd = remove_beginning('dead', cmd)
                continue

            # Syntax: 'dies :05'
            elif cmd.startswith('dies'):
                cmd = remove_beginning('dies', cmd)
                num, cmd = get_beg_number(cmd)
                if not num:
                    continue

                time = WbsTime(int(num), 0)
                state = WorldState.ALIVE
                continue

            elif cmd.startswith('beaming'):
                state = WorldState.BEAMING
                cmd = remove_beginning('beaming', cmd)
                continue

            elif is_tents(cmd[0:3]):
                tents = cmd[0:3]
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
                continue

            # Syntax: 'broken :02', same syntax as beamed
            elif cmd.startswith('broke'):
                cmd = remove_beginning('broken', cmd)
                cmd = remove_beginning('broke', cmd)
                num, cmd = get_beg_number(cmd)

                time = WbsTime.get_abs_minute_or_cur(num).add_mins(5)
                state = WorldState.ALIVE
                continue

            # Syntax: 'xx:xx gc', the seconds and gc part optional
            # Uses gameclock by default. To override use 'mins' postfix
            # Don't use isnumeric because it accepts wierd unicode codepoints
            elif cmd[0] in '0123456789':
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
                continue

            # Everything after first unrecognised token are notes
            else:
                notes = cmd
                cmd = ''

        # print(f'Updating: {world_num}, {loc}, {state}, {tents}, {time}, {notes}')
        return self.update_world(world_num, loc, state, tents, time, notes)

    def process_command(self, msgtxt, author, msgobj):
        try:
            cmd = msgtxt.strip().lower()

            # If we're in ignore mode, just ignore everything
            # except for the command letting us out of it
            if self._ignoremode:
                if cmd == '.ignoremode disable':
                    self._ignoremode = False
                    return f'Returning to normal mode'
                return

            if cmd.startswith('.ignoremode'):
                self._ignoremode = True
                return f'Going into ignore mode. Use `.ignoremode disable` to get out.'

            elif cmd == '.help':
                return self.get_help_info()

            elif cmd == 'list':
                self.update_world_states()
                return self.get_current_status()

            elif cmd == '.debug':
                self.update_world_states()
                return self.get_debug_info()

            elif cmd.startswith('.version'):
                return f'Bot version v{VERSION}. Written by CraftyElk :D'

            elif cmd.startswith('.reset'):
                summary = self.get_wave_summary()
                self.reset_state()
                return summary

            elif 'fc' in cmd and '?' in cmd:
                return f'Using FC: "{self._fcname}"'

            # Automated fc query
            elif cmd.startswith('.fc'):
                fcname = cmd[len('.fc '):].strip()
                if len(fcname) == 0:
                    return 'Please specify a valid FC name'
                else:
                    self._fcname = fcname
                    return f'Setting FC to: "{fcname}"'

            elif cmd.startswith('.host'):
                self._host = author
                return f'Setting host to: {author}'

            elif cmd.startswith('.anti'):
                self._antilist.add(author)
                return f'Adding {author} to anti list'

            elif cmd.startswith('.scout'):
                self._scoutlist.add(author)
                return f'Adding {author} to scout list'

            elif cmd.startswith('.call'):
                call = cmd[len('.call'):].strip()
                self._worldhist.append(call)
                return f'Adding "{call}" to call history'

            elif cmd.startswith('.wbs'):
                return next_wave_info()

            elif 'good bot' in cmd or 'goodbot' in cmd:
                self._upvotes += 1
                return f'Thank you :D\n{self.get_votes_summary()}'

            elif 'bad bot' in cmd or 'badbot' in cmd:
                # reserved for drizzin XD
                if msgobj.author.id == 493792070956220426:
                    return f'Fuck you'

                self._downvotes += 1
                return f':( *cries*\n{self.get_votes_summary()}'

            # Implement original worldbot commands
            elif 'cpkwinsagain' in cmd:
                return author + ' you should STFU!'

            else:
                for k,v in EASTER_EGGS.items():
                    if k in cmd:
                        return v

                self.parse_update_command(cmd)

        except InvalidWorldErr as e:
            return str(e)

        except Exception as e:
            traceback.print_exc()
            return 'Error: ' + str(e) + '\n' + traceback.format_exc()

    def on_notify_msg(self, msgtxt, author, msgobj):
        return self.process_command(msgtxt, author, msgobj)

