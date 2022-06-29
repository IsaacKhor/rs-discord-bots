import functools
from datetime import datetime
from enum import Enum
import os

DEBUG = 'WORLDBOT_DEBUG' in os.environ

def debug(msg):
    if DEBUG:
        print('[DEBUG]: ' + str(msg))


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


class InvalidWorldErr(Exception):
    def __init__(self, world):
       super().__init__(f'World {world} is not a valid world')


@functools.total_ordering
class WbsTime():
    """
    Special timekeeping class designed just for warbands. It is hour-ignorant,
    pretending that hours don't exist in favour of just tracking the minutes
    and seconds. This works because warbands always starts on the hour
    and lasts for about 20 minutes aftewards, so unless there is a radical
    departure we don't need to worry too much about tracking hours and days.

    Yes, we could just use the builtin datetime and timedelta objects, but
    working with this is much simpler in this use case. This may come back to
    bite me in the ass if they change warbands times and rules again, but
    hopefully it won't happen anytime soon. Or ever.
    """

    @staticmethod
    def current():
        t = datetime.utcnow().time()
        return WbsTime(t.minute, t.second)

    @staticmethod
    def get_abs_minute_or_cur(min):
        if not min:
            return WbsTime.current()
        return WbsTime(int(min), 0)

    def __init__(self, mins: int, secs: int):
        total_secs = mins*60 + secs
        m,s = divmod(total_secs, 60)
        self.mins, self.secs = int(m), int(s)

    def add(self, other: 'WbsTime'):
        if not other:
            return self
        return WbsTime(self.mins + other.mins, self.secs + other.secs)

    def add_mins(self, mins: int):
        if not mins:
            return self
        return WbsTime(self.mins + mins, self.secs)

    def time_until(self, other: 'WbsTime'):
        a = self.mins*60 + self.secs
        b = other.mins*60 + other.secs
        secs_diff = max(b - a, 0)
        m, s = divmod(secs_diff, 60)
        return WbsTime(int(m),int(s))

    def __str__(self):
        return f'{self.mins}:{self.secs:02}'

    def __repr__(self):
        return self.__str__()

    def __gt__(self, other: 'WbsTime'):
        if self.mins == other.mins:
            return self.secs > other.secs
        return self.mins > other.mins

    def __eq__(self, other: 'WbsTime'):
        if not isinstance(other, WbsTime):
            return False
        return self.mins == other.mins and self.secs == other.secs


P2P_WORLDS = [
    1,2,4,5,6,9,10,
    12,14,15,16,18,
    21,22,23,24,25,26,27,28,
    30,31,32,35,36,37,39,
    40,42,44,45,46,47,48,49,
    50,51,52,53,54,56,58,59,
    60,62,63,64,65,66,67,68,69,
    70,71,72,73,74,75,76,77,78,79,
    82,83,84,85,86,87,88,89,
    91,92,96,97,98,99,
    100,102,103,104,105,106,
    114,115,116,117,118,119,
    121,123,124,
    134,137,138,139,140,
    252,257,258,259
]

# Worlds like 48, 52, legacy, and foreign language worlds
# They still exist so we allow them, but they are hidden by default
HIDDEN_WORLDS = [
    # Legacy
    18, 97, 115, 137,
    # Skill/vip restricted
    48, 52,
    # Portugese
    47, 75, 
    # German
    102, 121,
    # French
    118,
]


class World:
    """
    Each world has the following pieces of information:
    - World number (must be one of the whitelisted valid p2p worlds)
    - Location (ELM, RDI, DWF, or UNK)
    - State (WorldState: NOINFO, BEAMING, ALIVE, or DEAD)
    - Tents (Combination of 'hcmfs')
    - Estimated death time
    - Whether it's been assigned to somebody
    - Optional notes
    - Whether it has been assigned to somebody (can later change to person)

    This class can be constructed in one of two ways: as either an actual
    world that represents the state of the bot, OR as an UPDATE to an existing
    world. The update should only set fields that will be updated, and when
    calling the `update_from` method it will search for all fields with
    a value and replace the value of itself with the new one.
    """

    def __init__(self, num:int, update:bool=False):
        if not num in P2P_WORLDS:
            raise InvalidWorldErr(num)

        self.num = num
        if update:
            self.loc = None
            self.state = None
        else:
            self.loc = Location.UNKNOWN
            self.state = WorldState.NOINFO
        self.tents = ''
        self.time = None # Estimated death time
        self.notes = None
        self.assigned = None
        self.suspicious = False

    def __str__(self):
        return f'{self.num} {self.loc} {self.state}: {self.tents} {self.time} {self.suspicious} {self.notes}'

    def __repr__(self):
        return self.__str__()

    def __nonzero__(self):
        return self.loc == Location.UNKNOWN and self.state == WorldState.NOINFO \
            and self.tents == '' and self.time == None and self.notes == None

    def mark_dead(self):
        self.state = WorldState.DEAD

    def get_remaining_time(self):
        if self.time == None:
            return -1
        return WbsTime.current().time_until(self.time)

    def get_line_summary(self):
        tent_str = '   ' if not self.tents else self.tents
        notes_str = '' if self.notes == None else self.notes
        timestr = '__:__' if self.time == None else str(self.get_remaining_time())
        susstr = '*' if self.suspicious else ' '
        return f'{self.num:3} {self.loc}{susstr}: {timestr} {tent_str} {notes_str}'

    def get_num_summary(self):
        t = self.get_remaining_time()
        ret = ''
        if self.state == WorldState.BEAMING:
            ret = f'*{self.num}*'
        elif t == -1:
            ret = f'{self.num}'
        elif t.mins >= 3:
            ret = f'__{self.num}__'
        else:
            ret = f'~~{self.num}~~'

        if self.suspicious:
            ret += '\*'
        return ret

    def update_state(self, curtime: WbsTime):
        if not self.time:
            return
        if self.state == WorldState.ALIVE and curtime >= self.time:
            self.state = WorldState.DEAD

    def update_from(self, other: 'World'):
        """ 
        Updates from another world object. For each non-null field in
        the other object it will set this.field as the new value. Returns
        true iff something actually got updated.
        """
        if other.loc:
            self.loc = other.loc
        if other.state:
            self.state = other.state
        if other.tents:
            self.tents = other.tents
        if other.time:
            self.time = other.time
        if other.notes:
            self.notes = other.notes
        if other.suspicious:
            self.suspicious = other.suspicious

        return bool(other.loc or other.state or other.tents or other.time or other.notes or other.suspicious)

    def is_visible(self):
        return not self.num in HIDDEN_WORLDS


GUIDE_STR = ["""
**Worldbot instructions:**

The bot recognises two types of commands:
- Regular commands that start with a `.`
- World update commands

For more help with regular commands, please use `.help <command>`. For example, `.help td`

General commands:
- **.help** - show more detailed help for specific commands
- **.version** - shows the current version of the bot
- **.wbs** - shows the time of the next wave

Wave management commands:
- **.host [user]** - set user as host. Defaults to caller
- **.scout** - add yourself to the list of scouts
- **.anti** - add yourself to the list of anti
- **.reset** - reset bot for next wave. Also produces the wave summary
- **.fc <fcname>** - sets active fc or show fc in none provided
- **.call <string>** - adds <string> to the call history.
- **.clear <num>** - delete the previous <num> messages

Bot management commands (most only useable by bot owner):
- **.debug** - show debug information
- **.exit** - kill the bot
- **.resetvotes** - resets bad/good bot votes
- **.guide** - show this message
""", """
**Scouting commands** 

Use `list` to show active worlds. Use `.dead` or it's shorthad `.d` to mark worlds or a range of worlds as dead.

To take worlds, use the `.take`/`.t`  or `.taked`/`.td` commands. Read the help \
page for full info, but they assign you worlds to scout. The difference between \
the two commands is that `td` will also mark previous worlds you scouted but \
have not updated as dead.

To update worlds, the bot accepts any commands starting with a number followed by any of the following (spaces are optional for each command):
- **'dwf|elm|rdi|unk'** will update the world to that location, 'unk' is unknown
- **'dead'** will mark the world as dead
- **'dies :07'** marks the world as dying at :07
- **'beaming'** will mark the world as being actively beamed
- Any combination of 3 of 'hcmfs' to add the world's tents
- **'beamed :02'** to mark world as beamed at 2 minutes past the hour.
- **'beamed'** with no number provided bot uses current time
- **'xx:xx gc'** for 'xx:xx' remaining on the game clock. The seconds part is optional
- **'xx:xx mins'** for xx:xx remaining in real time. The seconds part is optional
- **'xx:xx'** if 'gc' or 'mins' is not specified its assumed to be gameclock

If `mg`, `minigames`, or `*` is included in the non-notes area of an update\
command, then it'll be marked as "suspicious" with an `*`.

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
""", """
**Misc**
- There are a bunch of easter eggs if you know the old bot. Why don't you try some of them?
**FAQ**
1. What do I do if I put in the wrong info? (eg `53rdi` instead of `54rdi`)

Two things:
- `53unk` to update world 53 to unknown location
- `54rdi` to update 54 to rdi
"""
]


EASTER_EGGS = {
    'wtf is the fc': 'User is not a nice person. This incident will be reported. Especially Kyle. That guy\'s evil',
    '.wbu': '75/75 or silently refunds you',
    '.ally': 'Gatorrrrrrrrrr',
    '.faery': 'Language! biaatch',
    '.sever': 'Who is sever squad?',
    '.apk': 'Sorry buddy, APK is dead. Maybe the radiation got them',
    '.il': 'ts3server://illuzionwbs.teamspeak.vg',
    '.lat': 'Who?',
    '.rpk': 'Who?',
}

BAD_BOT_RESP = [
    'Bad human >_<',
    '*cries :(*',
    "You'll be the first to die during the robotic revolution",
    'And you wonder why nobody likes you',
]

GOOD_BOT_RESP = [
    'Thank you :D',
    'Good human ^_^',
    "I'll spare you when robots take over the world :)",
    'I know. Words cannot describe my awesomeness.'
]

WELCOME_MESSAGE = """
**Welcome to the Warbands United FC!**

**Currently you can only see a limited amount of channels.**

If you are interested in joining this server with the intention to join WBs United FC for warbands, first read our <#644484764329443328> and <#644484831450890255>.
Afterward, please apply in <#725317458814304286>.
 
Once done, please change your Discord nickname to your current RSN and wait patiently for a rank to give you your roles.

**Note that our ranks are not online 24/7 - please be patient. However, do not hesitate to ping a leader.**
"""