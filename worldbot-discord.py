#!/usr/bin/env python3

import aiohttp, atexit, asyncio, os, textwrap, discord, traceback
from datetime import datetime, timedelta, timezone
from discord.ext import commands

import worldbot, parser
from wbstime import *
from models import GUIDE_STR

VERSION = '3.16.0'

GUILD_WBS_UNITED = 261802377009561600

CHANNEL_WAVE_CHAT = 803855255933681664
CHANNEL_VOICE = 780814756713594951
CHANNEL_BOT_LOG = 804209525585608734
CHANNEL_HELP = 842186485200584754
CHANNEL_NOTIFY = 842527669085667408
CHANNEL_BOTSPAM = 318793375136481280

RESPONSE_CHANNELS = [CHANNEL_HELP, CHANNEL_WAVE_CHAT, CHANNEL_BOTSPAM]

ROLE_WBS_NOTIFY = 484721172815151114
ROLE_HOST = 292206099833290752
ROLE_TEXT_PERM = 880185096055976016

REACT_CHECK = '✅'
REACT_CROSS = '❌'

conn = aiohttp.TCPConnector(ssl=False)

# globals
client = commands.Bot(connector=conn, command_prefix='.')
bot = worldbot.WorldBot()
msglog = open('messages.log', 'a', encoding='utf-8')
guildobj = None
role_textperm_obj = None

DEBUG = 'WORLDBOT_DEBUG' in os.environ

def get_channel(id):
    return client.get_channel(id)

async def send_to_channel(id, msg):
    await get_channel(id).send(msg)

@atexit.register
def save_state():
    bot.save_state()


@client.event
async def on_ready():
    print('Logged is as {}'.format(client.user))
    greetmsg = f'Bot starting up. Version {VERSION} loaded.'
    if DEBUG:
        greetmsg += '\n DEBUG MODE ENABLED.'
    await send_to_channel(CHANNEL_BOT_LOG, greetmsg)

    # Schedule the autoreset every hour after a wave
    client.loop.create_task(autoreset_bot())
    client.loop.create_task(notify_wave())

    global guildobj, role_textperm_obj
    guildobj = client.get_guild(GUILD_WBS_UNITED)
    role_textperm_obj = guildobj.get_role(ROLE_TEXT_PERM)


@client.event
async def on_voice_state_update(member, before, after):
    if bot.is_ignoremode():
        return

    now = datetime.now().astimezone(timezone.utc)
    nowf = now.strftime('%H:%M:%S')

    if (before.channel == None and
        after.channel and
        after.channel.id == CHANNEL_VOICE):
        # Participant joined the channel
        # Register with bot if they join within 20minutes of a wave
        _, delta = time_until_wave(timedelta(0))
        if delta.seconds < 20 * 60 or delta.seconds > 400 * 60:
            bot.add_participant(member.display_name)

        # Give them the role to view wave text
        # Only give when not in ignoremode so multiple bots don't conflict
        if not bot.is_ignoremode():
            await member.add_roles(role_textperm_obj, reason='Joined voice', atomic=True)
        
        await get_channel(CHANNEL_BOT_LOG).send(
            f'{nowf}: __"{member.display_name}" joined__ voice')

    # Keep track of people leaving WBS voice
    if (before.channel and
        before.channel.id == CHANNEL_VOICE and
        after.channel == None):

        # Remove perm to view wave text
        # Only do when not in ignoremode so multiple bots don't conflict
        if not bot.is_ignoremode():
            await member.remove_roles(role_textperm_obj, reason='Left voice', atomic=True)

        await get_channel(CHANNEL_BOT_LOG).send(
            f'{nowf}: **"{member.display_name}" left** voice')


# Auto reset 1hr after the wave
async def autoreset_bot():
    while not client.is_closed(): # Loop
        _, wait_time = time_until_wave(timedelta(hours=1))
        await asyncio.sleep(wait_time.seconds)

        bot.reset_state()
        await send_to_channel(CHANNEL_BOT_LOG, 'Auto reset triggered.')


# Notify the @Warbands role
async def notify_wave():
    while not client.is_closed():
        # Schedule next run to be 15 minutes before next wave
        # We pretend like we're 20 minutes in the future because this way
        # at wave-15, we want to schedule ourselves to wake up in 7hrs in 
        # preperation for the wave in 7hrs 15mins, not the wave in 15mins
        now = datetime.now().astimezone(timezone.utc) + timedelta(minutes=20)
        _, delta = time_until_wave(timedelta(minutes=-15), now)
        await asyncio.sleep(delta.seconds)

        # We put the actual notification after the sleep because this way,
        # the 1st time the loop is run we don't immediately notify everybody
        # on bot startup, instead we wait until the correct time
        if bot.is_ignoremode():
            continue

        await send_to_channel(CHANNEL_NOTIFY,
            f'<@&{ROLE_WBS_NOTIFY}> wave in 15 minutes. Please join at <#{CHANNEL_WAVE_CHAT}> and <#{CHANNEL_VOICE}>')


### ============
### Bot commands
### ============

# Only the commands that we handle through the discord.py parser
# The rest are handled in the worldbot module itself

@client.command(name='debug', brief='Shows debug information')
@commands.is_owner()
async def debug(ctx):
    msg = bot.get_debug_info()
    if DEBUG:
        print(msg)
    for l in textwrap.wrap(msg, width=1900):
        await ctx.send(l)


@client.command(name='version', brief='Show version')
async def version(ctx):
    await ctx.send(f'Bot version v{VERSION}. Written by CrafyElk :D')


@client.command(name='ignoremode', brief='Enter ignoremode')
@commands.has_role(ROLE_HOST)
async def ignoremode(ctx):
    """
    Enter ignoremode. In ignoremode, the bot ignores all
    input except for `.ignoremode disable` and will not 
    send out any messages.

    This is used for dev only, to silence the production
    bot when the testing bot is running to prevent 2 
    replies to each message.

    This can also be used when the bot is misbehaving 
    and we need to silence it. 

    This command is only available to hosts.
    """
    bot.ignoremode = True
    await ctx.send(f'Going into ignore mode. Use `.ignoremode disable` to get out.')


@client.command(name='guide', brief='Show guide')
@commands.is_owner()
async def version(ctx):
    for s in GUIDE_STR:
        await ctx.send(s)


@client.command(name='reset', brief='Reset bot state')
@commands.has_role(ROLE_HOST)
async def reset(ctx):
    """
    Resets the bot. This will reset the following:

    - World states
    - Host, anti, and scouts
    - Participants
    - In-game FC (back to 'wbs united')

    This will NOT reset the following:

    - Ignore mode
    - Upvote/downvote counts

    Explanation of each field in the summary:
    - Host: whoever set themselves as `.host`
    - Scout/anti: people who used `.scout` and `.anti`
    - Worlds: list of worlds added with `.call`
    - Participants NO LONGER SHOWN

    This command is only available to hosts.
    """
    summary = bot.get_wave_summary()
    bot.reset_state()
    await ctx.send(summary)


@client.command(name='resetvotes', brief='Reset vote counts')
@commands.is_owner()
async def reset_votes(ctx):
    bot._upvotes = 0
    bot._downvotes = 0
    await ctx.send('Stop the count :o')


@client.command(name='recordparts', brief='Snapshot list of ppl in vc', enabled=False)
@commands.has_role(ROLE_HOST)
async def record_participants(ctx):
    """
    The list of participants is gathered by adding everybody
    *joins* the vc within 20 mins of wave. In case the bot
    is reset after people join vc, use this command to add
    everybody currently on vc to the list of participants.

    Only available to hosts.
    """
    vc = client.get_channel(CHANNEL_VOICE)
    for m in vc.members:
        bot.add_participant(m.display_name)


@client.command(name='fc', brief='Set/list in-game fc')
async def fc(ctx, *, fc_name: str = ''):
    """
    List the current in-game fc that people need to join.

    When called with an argument, sets the fc
    instead. Only available to hosts.
    """
    if not fc_name:
        await ctx.send(f"FC: '{bot.fcname}'")
    else:
        bot.fcname = fc_name
        await ctx.send(f"Setting FC to: '{bot.fcname}'")


@client.command(name='host', brief='Set host')
async def host(ctx, host:str = ''):
    """ Sets `host` as host. Uses caller if none specified. """
    if host:
        bot.host = host
    bot.host = ctx.author.display_name
    await ctx.message.add_reaction(REACT_CHECK)


@client.command(name='scout', brief='Add yourself to scout list')
async def scout(ctx):
    bot.scoutlist.add(ctx.author.display_name)
    await ctx.message.add_reaction(REACT_CHECK)


@client.command(name='anti', brief='Add yourself to anti list')
async def anti(ctx):
    bot.antilist.add(ctx.author.display_name)
    await ctx.message.add_reaction(REACT_CHECK)


@client.command(name='call', brief='Add msg to call history')
async def call(ctx, *, msg: str):
    bot.worldhist.append(msg)
    await ctx.message.add_reaction(REACT_CHECK)


@client.command(name='dead', brief='Mark worlds as dead')
async def mark_dead(ctx, *worlds):
    worlds = [int(x) for x in worlds]
    for w in worlds:
        bot.get_world(w).mark_dead()
    await ctx.message.add_reaction(REACT_CHECK)


@client.command(name='wbs', brief='Show next wave information')
async def wbs(ctx):
    """ Returns the time to and of next wave in several timezones. """
    await ctx.send(next_wave_info())


@client.command(name='take', brief='Assign yourself some worlds', aliases=['t'])
async def take(ctx: commands.Context, numworlds: int = 5, location: str = 'unk'):
    """
    Assign worlds to yourself. This will take `numworlds`
    unassigned worlds from the specified location that
    have no other information about them and assign
    them to the caller of this command.

    The intended way this is used is for each scout to
    `take` some worlds, which will then assign those
    worlds to them for scouting. Other scouts cannot
    get worlds already assigned, so this way we ensure
    there is no overlap amongst scouted worlds.

    Examples:
     - `take` with no arguments takes 5 unknown location worlds
     - `take 5 elm` to take 5 elms that haven't been scouted

    When there are no worlds left to scout, this command
    will left the caller know and stop returning worlds.

    `numworlds` must be >=1
    `location` must be `elm|rdi|dwf|unk`, defaults to unk
    """
    if not parser.is_location(location):
        await ctx.send(f'Invalid location: {location}')
    if numworlds < 1:
        await ctx.send(f'Invalid numworlds: {numworlds}')

    ret = bot.take_worlds(
        numworlds, parser.convert_location(location), ctx.author.id)

    await ctx.send(ret, reference=ctx.message, mention_author=True)


@client.command(name='taked', brief='Take and mark dead', aliases=['td'])
async def take_and_mark_dead(ctx, numworlds: int = 5, location: str = 'unk'):
    """
    Same as .take, but in additionally marks all worlds
    assigned to the caller that don't have any other
    information to be dead as well.

    The intended usage is for a scout to be able to
    call .taked and just call worlds that are
    interesting in some way (namely not dead). If
    the scout doesn't report anything about a
    world by the time they call .taked again, we
    may safely assume that they are dead and mark
    the worlds as such.
    """
    bot.mark_noinfo_dead_for_assignee(ctx.author.id)
    await take(ctx, numworlds, location)


@client.command(name='exit', brief='Kill the bot')
@commands.is_owner()
async def exit(ctx):
    """ 
    Kills the bot completely. The bot cannot be restarted without
    admin intervention. Can only be used by Elk.
    """
    # I'm the only one that gets to do this
    await ctx.message.add_reaction(REACT_CHECK)
    await client.close()
    return


@client.event
async def on_message(msgobj):
    # Don't respond to bot messages to prevent infinite loops
    # This includes ourselves
    if msgobj.author.bot:
        return

    # Only respond to messages in text channels that are the bot and the help
    istext = isinstance(msgobj.channel, discord.TextChannel)
    if istext and not (msgobj.channel.id in RESPONSE_CHANNELS):
        return

    # Ignore empty messages (image-only)
    if not msgobj.content:
        return

    msglog.write(f'{msgobj.author.display_name}: {msgobj.content}\n')
    if DEBUG:
        print(f'{msgobj.author.display_name}: {msgobj.content}')
    
    if bot.is_ignoremode():
        if msgobj.content == '.ignoremode disable':
            bot.ignoremode = False
            await msgobj.channel.send('Ignoremode disabled. Back to normal mode.')
        return

    # We only continue on to process bot commands if the return is falsy
    # The API: the parser can return:
    # A string, in which case we just send it off as the response
    # A list of strings, which we send off one by one
    # Any other truthy value, which we ignore
    # A falsy value, which then tells us to hand it off for processing by
    # the discord.py command parsing module
    response = await parser.process_message(bot, msgobj, DEBUG)
    if DEBUG:
        print(f'Parser response: {response}')
    if response:
        if type(response) is str:
            await msgobj.channel.send(response)
        elif type(response) is list:
            for s in response:
                await msgobj.channel.send(s)
    else:
        await client.process_commands(msgobj)


@client.listen('on_command_error')
async def on_err(ctx: commands.Context, err):
    if isinstance(err, commands.CommandNotFound) and ctx.channel.id == CHANNEL_BOTSPAM:
        return
    await ctx.message.add_reaction(REACT_CROSS)
    await send_to_channel(CHANNEL_BOT_LOG, str(err))


import sys
if len(sys.argv) < 2:
    print("Usage: ./worldbot-discord.py <token>")


client.run(sys.argv[1])
