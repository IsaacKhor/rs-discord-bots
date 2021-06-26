import pprint, inspect, os, json
from wbstime import *
from models import *

DEFAULT_FC = 'Wbs United'
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
        self.fcnanme = DEFAULT_FC
        self.host = ''
        self.antilist = set()
        self.scoutlist = set()
        self.worldhist = list()
        self.participants = set()

        self.ignoremode = False
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
        return f'Good humans: {self._upvotes}, bad humans: {self._downvotes}'

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
            ret += f'\n\n```\n{all_active_str}\n```'

        return ret

    def get_wave_summary(self):
        antistr = ', '.join(sorted(self.antilist))
        scoutstr = ', '.join(sorted(self.scoutlist))
        callhist = ', '.join(self.worldhist)
        ret = f"""
        Host: {self.host}
        Scouts: {scoutstr}
        Anti: {antistr}
        Worlds: {callhist}
        Participants: {', '.join(self.participants)}
        """
        return inspect.cleandoc(ret)

    def get_help_info(self):
        return HELP_STRING

    def is_registry_empty(self):
        return not any(w for w in self._registry.values())

    def update_world_states(self):
        curtime = WbsTime.current()
        for w in self.get_worlds():
            w.update_state(curtime)

    def add_participant(self, display_name):
        self.participants.add(display_name)

    def take_worlds(self, numworlds, loc):
        worlds = [w for w in self.get_worlds() 
            if w.loc == loc 
            and w.state == WorldState.NOINFO
            and w.assigned == False]

        assigning = worlds[:numworlds]
        for w in assigning:
            w.assigned = True
        
        return ', '.join([str(w.num) for w in assigning])
