import asyncio, discord, traceback, uuid
from io import TextIOWrapper
from datetime import datetime, timedelta, timezone
from discord.ext import commands

import parser
from wbstime import *
from config import *
from models import *


class WbuBot():
    def __init__(self, client: commands.Bot, msglog: TextIOWrapper, botlog: TextIOWrapper):
        self.client = client
        self.init = False
        self.msglog = msglog
        self.botlog = botlog
        self.uuid = str(uuid.uuid4())
        self.role_textperm_obj = None
        self.wave = WbsWave()
        self.ignoremode = False

        # Delay the rest of initialisation to first websocket connection
        client.event(self.on_ready)

    async def on_ready(self):
        # This function may be called more than once as the bot reconnects
        # Thus we have to keep track if we've been called before
        if self.init:
            await self.logr('Bot reconnected.')    
            return

        self.init = True
        self.log(f'Logged in as {self.client.user}')

        await self.logr(inspect.cleandoc(f"""
        Bot starting up. Version {VERSION} loaded.
        UUID: {self.uuid}.
        {'DEBUG MODE ENABLED' if DEBUG else ''}
        """))

        # Override message handler because sometimes we don't want to parse
        # stuff as a command
        self.client.event(self.on_message)

        # Create tasks for periodic features
        self.client.loop.create_task(self.autoreset_bot())
        self.client.loop.create_task(self.notify_wave())

        # Give/take away role when people join/leave voice
        self.role_textperm_obj = self.client.get_guild(GUILD_WBS_UNITED).get_role(ROLE_TEXT_PERM)
        self.client.add_listener(self.on_voice_state_update, 'on_voice_state_update')

        # Register other misc event listeners
        self.client.add_listener(self.on_err, 'on_command_error')
        self.client.add_listener(self.welcome_msg, 'on_member_join')

    # Logging
    # =======

    def log(self, msg: str):
        print(f'[LOG] {msg}')
        self.botlog.write(f'[LOG] {msg}')
    
    async def logr(self, msg: str):
        """ Log both locally and on #worldbot-logs """
        self.log(msg)
        await self.send_to_channel(CHANNEL_BOT_LOG, msg)
    
    # Utilities
    # =========

    async def send_to_channel(self, id: int, msg: str):
        await self.client.get_channel(id).send(msg)

    def reset_wave(self):
        self.wave = WbsWave()

    # Tasks
    # =====

    async def autoreset_bot(self):
        while not self.client.is_closed(): # Loop
            _, wait_time = time_to_next_wave()
            sleepsecs = wait_time.seconds + 60*60
            # Reset 1hr after wave
            await self.logr(f'Autoreset in {sleepsecs}')
            await asyncio.sleep(wait_time.seconds + 60*60)

            self.reset_wave()
            await self.logr('Auto reset triggered.')

    async def notify_wave(self):
        while not self.client.is_closed():
            # We put the actual notification after the sleep because this way,
            # the 1st time the loop is run we don't immediately notify everybody
            # on bot startup, instead we wait until the correct time
            _, wait_time = time_to_next_wave()
            sleepsecs = wait_time.seconds - 15*60
            await self.logr(f'Next wave reminder in {sleepsecs}.')
            await asyncio.sleep(sleepsecs)

            # Don't notify if we're in ignoremode
            if self.ignoremode:
                continue

            # Also include time of wave *after* the upcoming one for ease of access
            now = datetime.now().astimezone(timezone.utc)
            nextwave, _ = time_to_next_wave(now + timedelta(minutes=60))
            unixts = int(nextwave.timestamp())

            await self.send_to_channel(CHANNEL_NOTIFY,
                f'<@&{ROLE_WBS_NOTIFY}> wave in 15 minutes. Please join at <#{CHANNEL_WAVE_CHAT}> and <#{CHANNEL_VOICE}>\n' + 
                f'The following wave is <t:{unixts}:R> at <t:{unixts}:F>.')

            # Wait for 20 minutes so we start the loop again *after* the wave ends
            await asyncio.sleep(20 * 60)

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if self.ignoremode:
            return

        debug(f'{member}: before {before}, after {after}')
        nowf = datetime.now().astimezone(timezone.utc).strftime('%H:%M:%S')

        # Somebody joined CHANNEL_VOICE
        if (before.channel == None and
            after.channel and
            after.channel.id == CHANNEL_VOICE):
            # Give them the role to view wave text
            # Only give when not in ignoremode so multiple bots don't conflict
            if not self.ignoremode:
                await member.add_roles(self.role_textperm_obj, reason='Joined voice', atomic=True)

            await self.send_to_channel(CHANNEL_BOT_LOG,
                f'{nowf}: __"{member.display_name}" joined__ voice')

        # Somebody left CHANNEL_VOICE
        if (before.channel and
            before.channel.id == CHANNEL_VOICE and
            after.channel == None):

            # Remove perm to view wave text
            # Only do when not in ignoremode so multiple bots don't conflict
            if not self.ignoremode:
                await member.remove_roles(self.role_textperm_obj, reason='Left voice', atomic=True)

            await self.send_to_channel(CHANNEL_BOT_LOG,
                f'{nowf}: **"{member.display_name}" left** voice')


    async def on_message(self, msgobj: discord.Message):
        # Ignore bot messages to prevent infinite loops, including ourselves
        # Also ignore empty messages
        if msgobj.author.bot or not msgobj.content:
            return

        # discord.TextChannel means that it's a text channel in a guild, not DM
        # Only respond to messages in text channels that are the bot and the help
        istext = isinstance(msgobj.channel, discord.TextChannel)
        if istext and not (msgobj.channel.id in RESPONSE_CHANNELS):
            return

        # Log messages to a logfile
        self.msglog.write(f'{msgobj.author.display_name}: {msgobj.content}\n')
        debug(f'{msgobj.author.display_name}: {msgobj.content}')
        
        # Toggle ignoremode
        if self.ignoremode:
            if msgobj.content == '.ignoremode disable':
                self.ignoremode = False
                await msgobj.channel.send('Ignoremode disabled. Back to normal mode.')
            return

        rtype, msg = await parser.process_message(self.wave, msgobj)
        debug(f'Parser response: {repr(rtype)}, {msg}')

        if rtype == parser.ParserResp.CONTINUE_TO_COMMAND:
            await self.client.process_commands(msgobj)
        elif rtype == parser.ParserResp.RESPOND:
            await msgobj.channel.send(msg)
        elif rtype == parser.ParserResp.DISCARD:
            return

    async def on_err(self, ctx: commands.Context, err):
        if isinstance(err, commands.CommandNotFound) and ctx.channel.id == CHANNEL_BOTSPAM:
            return
        await ctx.message.add_reaction(REACT_CROSS)
        await self.logr(str(err))
        debug('\n'.join(traceback.format_exception(type(err), err, err.__traceback__)))


    # Send welcome message
    async def welcome_msg(self, mem: discord.Member):
        dmc = mem.dm_channel
        if not dmc:
            dmc = await mem.create_dm()

        await dmc.send(content=WELCOME_MESSAGE)
        await self.logr(f'Sent welcome message to: {mem.display_name}')

