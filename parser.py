import re, traceback, random
from worldbot import WorldBot

import discord
from models import *

NUM_PAT = re.compile(r'^(\d+)')

# Parsing utils
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
    while cmd:
        # Ignore whitespace between tokens
        cmd = cmd.lstrip()
        print(cmd)

        if cmd.startswith('mg') or cmd.startswith('minigames') or cmd.startswith('sus') or cmd.startswith('*'):
            cmd = remove_beginning('minigames', cmd)
            cmd = remove_beginning('sus', cmd)
            cmd = remove_beginning('mg', cmd)
            cmd = remove_beginning('*', cmd)
            update.suspicious = True
            continue

        elif cmd.startswith('dead'):
            update.state = WorldState.DEAD
            cmd = remove_beginning('dead', cmd)
            continue

        # Syntax: 'dies :05'
        elif cmd.startswith('dies'):
            cmd = remove_beginning('dies', cmd)
            num, cmd = get_beg_number(cmd)
            if not num:
                continue

            update.time = WbsTime(int(num), 0)
            update.state = WorldState.ALIVE
            continue

        elif cmd.startswith('beaming'):
            update.state = WorldState.BEAMING
            cmd = remove_beginning('beaming', cmd)
            continue

        elif is_tents(cmd[0:3]):
            update.tents = cmd[0:3]
            cmd = cmd[3:]
            continue

        # Tents could be shortened to 'hcs', 'hms', etc
        # Or they could be manually specified 'herb con mine' etc, or both
        elif is_location(cmd[0:3]):
            update.loc = convert_location(cmd[0:3])
            cmd = remove_beginning('elm', cmd)
            cmd = remove_beginning('rdi', cmd)
            cmd = remove_beginning('dwf', cmd)
            cmd = remove_beginning('unk', cmd)
            continue

        elif cmd.startswith('herblore') or cmd.startswith('herb'):
            cmd = remove_beginning('herblore', cmd)
            cmd = remove_beginning('herb', cmd)
            update.tents += 'h'
            continue

        elif cmd.startswith('construction') or cmd.startswith('cons') or cmd.startswith('con'):
            cmd = remove_beginning('construction', cmd)
            cmd = remove_beginning('cons', cmd)
            cmd = remove_beginning('con', cmd)
            update.tents += 'c'
            continue

        elif cmd.startswith('farming') or cmd.startswith('farm'):
            cmd = remove_beginning('farming', cmd)
            cmd = remove_beginning('farm', cmd)
            update.tents += 'f'
            continue

        elif cmd.startswith('mining') or cmd.startswith('mine') or cmd.startswith('min'):
            cmd = remove_beginning('mining', cmd)
            cmd = remove_beginning('mine', cmd)
            cmd = remove_beginning('min', cmd)
            update.tents += 'm'
            continue

        elif cmd.startswith('smithing') or cmd.startswith('smith'):
            cmd = remove_beginning('smithing', cmd)
            cmd = remove_beginning('smith', cmd)
            update.tents += 's'
            continue

        # Syntax: 'beamed :02', space, colon, and time all optional
        elif cmd.startswith('beamed'):
            cmd = remove_beginning('beamed', cmd)
            num, cmd = get_beg_number(cmd)

            update.time = WbsTime.get_abs_minute_or_cur(num).add_mins(10)
            update.state = WorldState.ALIVE
            time_found = True
            continue

        # Syntax: 'broken :02', same syntax as beamed
        elif cmd.startswith('broke'):
            cmd = remove_beginning('broken', cmd)
            cmd = remove_beginning('broke', cmd)
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
                cmd = remove_beginning('mins', cmd)
            else:
                cmd = remove_beginning('gc', cmd)
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


async def process_message(worldbot: WorldBot, msgobj: discord.Message, debug=False):
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
            
            resp = worldbot.get_current_status()
            msg = await msgobj.channel.send(resp)
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
            if debug:
                print(f'Found update command, got "{update}"')
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