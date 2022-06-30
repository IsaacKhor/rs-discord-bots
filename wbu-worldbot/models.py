import functools, inspect, pprint
from datetime import datetime
from enum import Enum, auto
from typing import List
import discord

from config import *

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


class WbsWave:
    def __init__(self):
        self.fcname = DEFAULT_FC
        self.host = ''
        self.antilist = set()
        self.scoutlist = set()
        self.worldhist = list()
        self.participants = set()

        # Previous `list` message object
        # We keep this around so we can delete it whenever somebody
        # calls `list` again to reduce spam
        self.prevlistmsg = None

        self._registry = dict()

        for num in P2P_WORLDS:
            self._registry[num] = World(num)

    def get_debug_info(self):
        return inspect.cleandoc(f"""
        Host: {self.host}
        Antilist: {self.antilist}
        Scoutlist: {self.scoutlist}
        World history: {self.worldhist}
        Participants: {self.participants}
        Registry: {pprint.pformat(self._registry)}
        """)

    def is_ignoremode(self):
        return self.ignoremode

    def get_worlds_with_info(self):
        return [w for w in self._registry if w]

    def get_world(self, num):
        if num not in P2P_WORLDS:
            raise InvalidWorldErr(num)
        return self._registry[num]

    def get_worlds(self):
        return self._registry.values()

    # Return true iff we actually update something
    def update_world(self, update):
        world = self.get_world(update.num)
        return world.update_from(update)

    def get_active_for_loc(self, loc):
        return ','.join([w.get_num_summary() for w in self.get_worlds()
            if w.loc == loc and w.is_visible() and w.state != WorldState.DEAD])

    # Summary output
    def fill_worldlist_embed(self, embed: discord.Embed):
        """ Returns a KV map for discord embeds """
        worlds = self.get_worlds()

        # dead_str = ','.join([str(w.num) for w in worlds if w.state == WorldState.DEAD])
        active_dwfs = self.get_active_for_loc(Location.DWF)
        active_elms = self.get_active_for_loc(Location.ELM)
        active_rdis = self.get_active_for_loc(Location.RDI)
        active_unks = self.get_active_for_loc(Location.UNKNOWN)

        all_active = [w for w in worlds if w.state == WorldState.ALIVE]
        all_active = sorted(all_active, key=lambda w: w.time, reverse=True)
        all_active_str = '\n'.join([w.get_line_summary() for w in all_active])

        if active_dwfs:
            embed.add_field(name='DWF', value=active_dwfs, inline=False)
        if active_elms:
            embed.add_field(name='ELM', value=active_elms, inline=False)
        if active_rdis:
            embed.add_field(name='RDI', value=active_rdis, inline=False)
        if active_unks:
            embed.add_field(name='Unknown', value=active_unks, inline=False)
        if all_active_str:
            all_active_str = f'```\n{all_active_str}\n```'
            embed.add_field(name='Active', value=all_active_str, inline=False)

        return embed

    def get_wave_summary(self):
        antistr = ', '.join(sorted(self.antilist))
        scoutstr = ', '.join(sorted(self.scoutlist))
        callhist = ', '.join(self.worldhist)
        ret = f"""
        Host: {self.host}
        Scouts: {scoutstr}
        Anti: {antistr}
        Worlds: {callhist}
        """
        #Participants: {', '.join(sorted(self.participants))}

        return inspect.cleandoc(ret)

    def is_registry_empty(self):
        return not any(w for w in self._registry.values())

    def update_world_states(self):
        curtime = WbsTime.current()
        for w in self.get_worlds():
            w.update_state(curtime)

    def add_participant(self, display_name):
        self.participants.add(display_name)

    def mark_noinfo_dead_for_assignee(self, authorid: int):
        worlds = [w for w in self.get_worlds() if w.assigned == authorid and w.state == WorldState.NOINFO]
        for w in worlds:
            w.mark_dead()
        pass

    def take_worlds(self, numworlds: int, loc: str, authorid: int):
        worlds = [w for w in self.get_worlds() 
            if w.loc == loc 
            and w.state == WorldState.NOINFO
            and w.assigned == None
            and w.is_visible()]

        assigning = worlds[:numworlds]
        for w in assigning:
            w.assigned = authorid

        ret = ', '.join([str(w.num) for w in assigning])
        if len(assigning) < numworlds:
            ret += '. No more worlds available.'

        return ret
