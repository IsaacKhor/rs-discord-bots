#!/usr/bin/env python3

import traceback
from worldbot import *
import ts3shim

if len(sys.argv) < 2:
    print("Usage: ./worldbot-ts3.py <tspass>")
    sys.exit()

HOST = 'localhost'
PORT = 25639
CHANNEL_ID = 2
NICKNAME = 'Worldbot'
CLIENTQUERY_API_KEY = sys.argv[1]
RESET_PASSWORD = 'pewpew'

conn = ts3shim.ClientqueryConn(host=HOST, port=PORT, apikey=CLIENTQUERY_API_KEY)
worldbot = WorldBot()

ORIGINAL_EASTER_EGGS = {
    '!wbu': '75/75 or silently refunds you',
    '!ally': 'Gatorrrrrrrrrr',
    '!faery': 'Language! biaatch',
    '!sever': 'Who is sever squad?',
    '!apk': 'Sorry buddy, APK is dead. Maybe the radiation got them',
    '!il': 'ts3server://illuzionwbs.teamspeak.vg',
    '!lat': 'Who?',
    '!rpk': 'Who?',
    '!take': 'Not implemented. Feel free to scout whatever world you want'
}


def on_notify_msg(msg):
    # print(msg)
    # Dont respond to our own messages
    if msg.invokername == NICKNAME:
        return

    try:
        cmd = msg.msg.strip().lower()
        retmsg = None
        if cmd == '.help':
            return worldbot.get_help_info()
        elif cmd == 'list':
            worldbot.update_world_states()
            return worldbot.get_current_status()
        elif cmd == '.debug':
            worldbot.update_world_states()
            return worldbot.get_debug_info()

        elif cmd.startswith('.reset'):
            # Ensure permissions
            if msg.targetmode != ts3shim.TARGETMODE_PRIVATE:
                return 'You can only reset in PMs with the correct password'

            toks = [s.strip() for s in cmd.split(' ')]
            if len(toks) < 2:
                return 'Password required'

            password = toks[1]
            if password != RESET_PASSWORD:
                return 'Invalid password'

            worldbot.reset_worlds()
            return 'Worlds successfully reset'

        # Bot crashed, have to restart
        elif cmd.startswith('.reload'):
            cmd = cmd[len('.reload '):]
            lns = cmd.split('\n')
            for l in lns:
                i = l.find(':', 10)
                l = l[i+2:]
                if l[0].isnumeric():
                    parse_update_command(l, worldbot)

        # Implement original worldbot commands
        elif 'cpkwinsagain' in cmd:
            return  msg.invokername + ' you should STFU!'

        else:
            for k,v in ORIGINAL_EASTER_EGGS.items():
                if k in cmd:
                    return v
            parse_update_command(cmd, worldbot)

    except Exception as e:
        traceback.print_exc()
        return 'Error: ' + str(e)


conn.set_msg_handler(on_notify_msg)
conn.start_process_messages()
