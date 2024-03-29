#!/usr/bin/env python3

import sys
from datetime import datetime, time, timedelta
from bs4 import BeautifulSoup
import discord
import requests
import asyncio
import os
import logging
import viswax

CHANNEL_NOTIFY = 842527669085667408
CHANNEL_BOT_LOG = 804209525585608734

ROLE_CHAD = 856529519186673694

ROLE_VIS_WAX = 858911901492445184
ROLE_TMS = 676760858868711436
ROLE_YEWS = 859158679713742889
ROLE_GOEBIEBANDS = 483236107396317195


# Set up logging
loglv = os.environ.get('LOGLV') or 'INFO'
loglvn = getattr(logging, loglv.upper(), None)
logging.basicConfig(
    filename='wbunotify.log',
    level=loglvn,
    format='[%(asctime)s %(levelname)s]: %(message)s')

intents = discord.Intents.default()
client = discord.Client(intents=intents)
initialised = False


@client.event
async def on_ready():
    global initialised
    if initialised:
        logging.info(f'Bot reconnected')
        return

    logging.info(f'Logged is as {client.user}')
    # await send_to_channel(CHANNEL_NOTIFY, f'WBU Notifier connected')

    client.loop.create_task(create_specific_time_notif(
        name='Travelling Merchant',
        times=[time(hour=0, minute=3)],
        channel=CHANNEL_NOTIFY,
        msgfn=get_tms_from_template
    ))

    client.loop.create_task(create_specific_time_notif(
        name='Vis wax',
        times=[time(hour=0, minute=2)],
        channel=CHANNEL_NOTIFY,
        msgfn=get_viswax_pred_msg
    ))

    client.loop.create_task(create_specific_time_notif(
        name='Reset yews',
        times=[time(hour=23, minute=45)],
        channel=CHANNEL_NOTIFY,
        msgfn=lambda: f'<@&{ROLE_YEWS}> yews starting on world 48.'
    ))

    client.loop.create_task(create_specific_time_notif(
        name='140 yews',
        times=[time(hour=17, minute=40)],
        channel=CHANNEL_NOTIFY,
        msgfn=lambda: f'<@&{ROLE_YEWS}> yews starting on world 140.'
    ))

    client.loop.create_task(create_specific_time_notif(
        name='Goebiebands noon',
        times=[time(hour=11, minute=45)],
        channel=CHANNEL_NOTIFY,
        msgfn=lambda: f'<@&{ROLE_GOEBIEBANDS}> starting in 15 minutes.'
    ))

    # I can't figure out why it isn't doing it twice, so use the lazy solution
    client.loop.create_task(create_specific_time_notif(
        name='Goebiebands reset',
        times=[time(hour=23, minute=45)],
        channel=CHANNEL_NOTIFY,
        msgfn=lambda: f'<@&{ROLE_GOEBIEBANDS}> starting in 15 minutes.'
    ))

    initialised = True


@client.event
async def on_message(msg):
    pass


# Why we use asyncio sleeps instead of cron
# This is intended to be a drop-in bot that you can clone and run
# after changing the constants up top, so I don't want to add addiniotaly
# config steps with 'copy this into your cron' or 'run this script to
# copy shit into your cron.d'. This makes everything simple and
# self-contained

def secs_until_next(target):
    """
    Accepts a offset-naive time of day, and returns seconds until the next
    occurence of that time until now. Everything is assumed to be in UTC.
    """
    # Handle everything in offset-naive times
    assert (target.tzinfo == None)
    now = datetime.utcnow()
    if target > now.time():
        # Cant subtract two datetime.time objects
        # They have to be datetime objects to get a timedelta
        targetdt = datetime.combine(datetime.today(), target)
    else:
        tmr = datetime.today() + timedelta(days=1)
        targetdt = datetime.combine(tmr, target)
    return (targetdt - now).total_seconds()


async def send_to_channel(id, msg):
    await client.get_channel(id).send(msg)


def create_specific_time_notif(name, times, channel, msgfn):
    """
    Params:
    - times: list of `datetime.time` objects that will determine when
      the message will go out
    - channel: which channel to send the message
    - msgfn: message to call with time of day for the ping message
    """
    async def notiffn():
        while not client.is_closed():
            mindelta = 60 * 60 * 24
            logging.debug(f'Searching minimum time for {name}')
            for t in times:
                s = secs_until_next(t)
                logging.debug(f'{s} secs to {t}')
                mindelta = min(mindelta, s)
            logging.info(f'Notifying about {name} in {mindelta/60/60:5} hours')
            await asyncio.sleep(delay=mindelta)

            msg = msgfn()
            logging.info(f'Notifying about {name}')
            await send_to_channel(channel, msg)

            # Safety wait so it doesn't double-notify
            await asyncio.sleep(delay=60)

    return notiffn()


def get_tms_message():
    # Can switch to aiohttp if needed
    TMS_PARAMS = {'lang': 'en'}
    r = requests.get(TMS_ENDPOINT, params=TMS_PARAMS, headers=TMS_HEADERS)
    j = r.json()
    stock = ', '.join(j[1:])
    return f'<@&{ROLE_TMS}> stock today: {stock}'


USER_AGENT = 'wbu_notify_bot (contact@unknownpriors.com or @unknownpriors#9144)'
TMS_HEADERS = {'user-agent': USER_AGENT}
TMS_ENDPOINT = 'https://api.weirdgloop.org/runescape/tms/current'
TMS_TEMPLATE_ENDPOINT = 'https://runescape.wiki/api.php?format=json&action=parse&prop=text&disablelimitreport=1&text={{Travelling%20Merchant/api}}'


def get_tms_from_template():
    r = requests.get(TMS_TEMPLATE_ENDPOINT, headers=TMS_HEADERS)
    j = r.json().get('parse').get('text').get('*')
    b = BeautifulSoup(j, 'html.parser')
    spans = b.find_all('span', {'class': 'name'})
    names = [s.text for s in spans]
    stock = ', '.join(names)
    return f'<@&{ROLE_TMS}> stock today: {stock}'


def get_viswax_pred_msg() -> str:
    msg = viswax.slot_messages()
    return f'<@&{ROLE_VIS_WAX} predicted runes for today:\n{msg}'


if len(sys.argv) < 2:
    print("Usage: ./wbunotify.py <token>")
client.run(sys.argv[1])
