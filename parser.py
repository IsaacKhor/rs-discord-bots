import re, traceback, random
from worldbot import WorldBot

import discord
from models import *

NUM_PAT = re.compile(r'^(\d+)')
RANGE_PAT = re.compile(r'^(\d+)-(\d+)')
TOK_BOUNDS = ' :'

# Parsing utils
def advance_tok(s):
    return s.lstrip(TOK_BOUNDS)

def is_location(tok):
    return tok in ['dwf', 'elm', 'rdi', 'unk']

def is_tents(tok):
    return len(tok) == 3 and all(c in 'mhcsf' for c in tok)

def get_beg_number(s):
    num, string = match_beginning(NUM_PAT, s)
    if num:
        num = int(num)
    return num, string

def match_range(s):
    m = re.match(RANGE_PAT, s)
    if not m:
        return None, s

    lower, upper = m.groups()
    rest = advance_tok(re.sub(RANGE_PAT, '', s))
    return (int(lower), int(upper)), rest

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

def can_consume(s: str, *toks):
    for t in toks:
        if s.startswith(t):
            return True
    return False

def consume(s: str, *toks):
    for t in toks:
        if s.startswith(t):
            return s[len(t):].lstrip(' :')
    return s
    

def parse_update_command(msg):
    """
    Converts a message into a world update command. If the string is not
    an update command return null, otherwise return the world update object.
    """
    msg = msg.strip().lower()

    # Try to match number at beginning of string
    world_num, msg = get_beg_number(msg)
    if not world_num:
        return None

    # Build the world update object
    update = World(world_num, update=True)

    cmd = msg
    time_found = False
    debug(f'Parsing: {cmd}')
    while cmd:
        debug(f'Remaining: "{cmd}"')
        # Ignore whitespace between tokens
        cmd = cmd.lstrip()
        # print(cmd)

        if can_consume(cmd, 'mg', 'minigames', 'mini', 'sus', '*'):
            cmd = consume(cmd, 'mg', 'minigames', 'mini', 'sus', '*')
            update.suspicious = True
            continue

        elif can_consume(cmd, 'dead'):
            cmd = consume(cmd, 'dead')
            update.state = WorldState.DEAD
            continue

        # Syntax: 'dies :05'
        elif can_consume(cmd, 'dies'):
            cmd = consume(cmd, 'dies')
            num, cmd = get_beg_number(cmd)
            if not num:
                continue

            update.time = WbsTime(int(num), 0)
            update.state = WorldState.ALIVE
            continue

        elif cmd.startswith('beaming'):
            update.state = WorldState.BEAMING
            cmd = consume(cmd, 'beaming')
            continue

        elif is_tents(cmd[0:3]):
            update.tents = cmd[0:3]
            cmd = cmd[3:]
            continue

        elif is_location(cmd[0:3]):
            update.loc = convert_location(cmd[0:3])
            cmd = consume(cmd, 'elm', 'rdi', 'dwf', 'unk')
            continue

        # Syntax: 'beamed :02', space, colon, and time all optional
        elif cmd.startswith('beamed'):
            cmd = consume(cmd, 'beamed')
            num, cmd = get_beg_number(cmd)

            update.time = WbsTime.get_abs_minute_or_cur(num).add_mins(10)
            update.state = WorldState.ALIVE
            time_found = True
            continue

        # Syntax: 'broken :02', same syntax as beamed
        elif can_consume(cmd, 'broken', 'broke'):
            cmd = consume(cmd, 'broken', 'broke')
            num, cmd = get_beg_number(cmd)

            update.time = WbsTime.get_abs_minute_or_cur(num).add_mins(5)
            update.state = WorldState.ALIVE
            time_found = True
            continue

        # Syntax: 'xx:xx gc', the seconds and gc part optional
        # Uses gameclock by default. To override use 'mins' postfix
        # Don't use isnumeric because it accepts wierd unicode codepoints
        # We only want to parse the time once, so if a scout includes
        # numbers in their comments about a world we don't re-parse
        # that as the new time
        elif cmd[0] in '0123456789' and not time_found:
            mins, cmd = get_beg_number(cmd)
            secs, cmd = get_beg_number(cmd)
            secs = secs if secs else 0

            if cmd.startswith('mins'):
                cmd = consume(cmd, 'mins')
            else:
                cmd = consume(cmd, 'gc')
                ticks = mins*60 + secs
                total_secs = ticks*0.6
                mins, secs = divmod(total_secs, 60)

            update.time = WbsTime.current().add(WbsTime(int(mins), int(secs)))
            update.state = WorldState.ALIVE
            time_found = True
            continue

        # Everything after first unrecognised token are notes
        else:
            update.notes = cmd
            break

    return update


async def process_message(worldbot: WorldBot, msgobj: discord.Message):
    """
    The API: the parser can return:
    A string, in which case we just send it off as the response
    A list of strings, which we send off one by one
    Any other truthy value, which we ignore
    A falsy value, which then tells us to hand it off for processing by
    the discord.py command parsing module
    """
    try:
        cmd = msgobj.content.strip().lower()

        if cmd == 'list':
            """
            The `list` command does the following:
            - Update world times
            - Delete the output of the previoust `list` command
            - Output the world state summary
            - Delete the invocation of `list` itself
            """
            worldbot.update_world_states()

            if worldbot.prevlistmsg:
                await worldbot.prevlistmsg.delete()
            
            em = discord.Embed(color=0xeeeeee)
            worldbot.fill_worldlist_embed(em)
            msg = await msgobj.channel.send(embed=em)
            worldbot.prevlistmsg = msg

            await msgobj.delete()
            return True

        elif 'fc' in cmd and '?' in cmd:
            return f'Using FC: "{worldbot.fcname}"'

        elif 'good bot' in cmd or 'goodbot' in cmd:
            worldbot._upvotes += 1
            ret = random.choice(GOOD_BOT_RESP)
            return f'{ret}\n{worldbot.get_votes_summary()}'

        elif 'bad bot' in cmd or 'badbot' in cmd:
            # reserved for drizzin XD
            if msgobj.author.id == 493792070956220426:
                return f'Fuck you'

            worldbot._downvotes += 1
            ret = random.choice(BAD_BOT_RESP)
            return f'{ret}\n{worldbot.get_votes_summary()}'

        # Implement original worldbot commands
        elif 'cpkwinsagain' in cmd:
            return msgobj.author.display_name + ' you should STFU!'

        elif cmd[0] in '0123456789':
            update = parse_update_command(msgobj.content)
            ret = worldbot.update_world(update)
            debug(f'Found update command, got "{update}"')
            # Falsy return if nothing actually got updated
            return ret

        else:
            for k,v in EASTER_EGGS.items():
                if k in cmd:
                    return v

    except InvalidWorldErr as e:
        return str(e)

    except Exception as e:
        traceback.print_exc()
        return 'Error: ' + str(e) + '\n' + traceback.format_exc()