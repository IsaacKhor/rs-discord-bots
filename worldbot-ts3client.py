#!/usr/bin/env python3

import traceback, os, importlib, sys
import worldbot
import ts3shim

if len(sys.argv) < 2:
    print("Usage: ./worldbot-ts3.py <tspass>")
    sys.exit()

HOST = 'localhost'
PORT = 25639
CHANNEL_ID = 2
NICKNAME = 'Worldbot'
CLIENTQUERY_API_KEY = sys.argv[1]

VERSION = '1.0.0'

def pull_and_reload():
    # Pull from github
    os.system('git pull')
    global worldbot
    global ts3shim
    worldbot = importlib.reload(worldbot)
    ts3shim = importlib.reload(ts3shim)

conn = ts3shim.ClientqueryConn(host=HOST, port=PORT, apikey=CLIENTQUERY_API_KEY)
botcore = worldbot.WorldBot()

def on_notify_msg(msg):
    global botcore
    global conn
    if msg.invokername == NICKNAME:
        return

    if (msg.msg.startswith('.redeploy') and
        msg.targetmode == ts3shim.TARGETMODE_PRIVATE and
        msg.msg.lower().strip() == '.redeploy secretredeploypassword'):
        pull_and_reload()
        botcore = worldbot.WorldBot()
        conn = ts3shim.ClientqueryConn(host=HOST, port=POST, apikey=CLIENTQUERY_API_KEY)
        return 'Redeploy successful'

    if (msg.msg.startswith('.exit') and
        msg.targetmode == ts3shim.TARGETMODE_PRIVATE and
        msg.msg.lower().strip() == '.exit stopandexitprettyplz'):
        exit()

    if msg.msg.startswith('.version'):
        return 'Current bot version: ' + VERSION + '. Written by CraftyElk :D'

    return botcore.on_notify_msg(msg.msg, msg.targetmode, msg.invokerid, msg.invokername)

conn.set_msg_handler(on_notify_msg)
conn.start_process_messages()
