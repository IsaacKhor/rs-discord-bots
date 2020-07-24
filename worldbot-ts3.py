#!/usr/bin/env python3

import ts3, sys, atexit
import ts3.TS3Connection as ts3
import ts3.Events as Events
from botcore import *

if len(sys.argv) < 2:
    print("Usage: ./worldbot-ts3.py <tspass>")
    sys.exit()

HOST = 'localhost'
PORT = 10011
CHANNEL_ID = 2 # channel id where bot should watch for events
SID = 1
NICKNAME = 'worldbot'
# Bot needs an account with ServerQuery access
# It only needs the permission to send and read messages, specifically
# the ones required for 'sendtextmessage' and 'notifyserverregister'
# Please don't use an admin account for this, if the bot messes up the
# cleanup will not be fun
TSUSER = 'worldbot'
TSPASS = sys.argv[1]

help_string = """
Worldbot instructions:

[b]Commands[/b]:
- [b]list[/b] - lists summary of current status
- [b]help[/b] - show this help message
- [b]reset[/b] - reset bot for next wave
- [b]debug[/b] - show debug information

[b]Scouting commands[/b] - The bot accepts any commands starting with a number
followed by any of the following (spaces are optional for each command):
- [b]'dwf|elm|rdi|unk'[/b] will update the world to that location, 'unk' is unknown
- [b]'dead'[/b] will mark the world as dead
- [b]'unsafe'[/b] will mark the world as unsafe
- [b]'beaming'[/b] will mark the world as being actively beamed
- Any combination of 3 of 'hcmfs' to add the world's tents
- [b]'beamed :02'[/b] to mark world as beamed at 2 minutes past the hour.
- [b]'beamed'[/b] with no number provided bot uses current time
- [b]'dies :07'[/b] marks the world as dying at :07
- [b]'xx:xx gc'[/b] for 'xx:xx' remaining on the game clock. The seconds part is optional
- [b]'xx:xx mins'[/b] for xx:xx remaining in real time. The seconds part is optional
- [b]'xx:xx' if 'gc' or 'mins' is not specified its assumed to be gameclock

So for example:
- '119dwf 10gc' marks world as dying in 10\\*0.6=6 minutes
- '119 mhs 4mins' marks the world as dying in 4 minutes
- '28 dead'
- '84 beamed02 hcf clear', you can combine multiple commands
"""

worldbot = WorldBot(helpstr=help_string)
tsc = ts3.TS3Connection(HOST, PORT)
tsc.login(TSUSER, TSPASS)

@atexit.register
def logout_on_exit():
    print('Logging out')
    tsc.quit()

tsc.use(sid=SID)

client_info = tsc.whoami()
client_id = client_info['client_id']
client_nickname = client_info['client_nickname']
# TS remembers nickname from last login, and updating it to the same name
# will throw a nickname already is use error
if client_nickname != NICKNAME:
    tsc.clientupdate([f'client_nickname={NICKNAME}'])

tsc.clientmove(CHANNEL_ID, client_id)
tsc.start_keepalive_loop()

def on_textmsg(sender, **kw):
    event = kw['event']
    print(type(event), event, event.invoker_id, event.invoker_name)

    # Only respond to text message events
    if not type(event) == Events.TextMessageEvent:
        print('ERR: not text message event')
        return

    # Dont respond to our own messages
    if event.invoker_name == NICKNAME:
        return

    # Commands:
    # - 'list': list summary of state
    # - '.help': show help
    # - '.reset': reset bot state
    # - '.debug': show debug info
    # - others

    cmd = event.message.strip()
    retmsg = None
    try:
        if cmd == '.help':
            retmsg = worldbot.get_help_info()
        elif cmd == 'list':
            retmsg = worldbot.get_current_status()
        elif cmd == '.debug':
            retmsg = worldbot.get_debug_info()
        elif cmd == '.reset':
            worldbot.reset_worlds()
            retmsg = 'Worlds successfully reset'
        else:
            parse_update_command(cmd, worldbot)
    except Exception as e:
        retmsg = str(type(e)) + str(e)

    if retmsg:
        # Check where to send it
        targetmode = -1
        if event.targetmode == 'Private':
            targetmode = 1
        else:
            targetmode = 2
        tsc.sendtextmessage(targetmode=targetmode, target=event.invoker_id, msg=retmsg)



tsc.register_for_channel_messages(on_textmsg)
tsc.register_for_private_messages(on_textmsg)

