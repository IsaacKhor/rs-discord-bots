import textwrap

import discord
from discord.ext import commands

from config import *
from models import *
from wbubot import WbuBot
import parser

def register_commands(client: commands.Bot, wbu: WbuBot):

	@client.command(name='debug', brief='Shows debug information')
	@commands.is_owner()
	async def debug_cmd(ctx):
		msg = wbu.wave.get_debug_info()
		debug(msg)
		for l in textwrap.wrap(msg, width=1900):
			await ctx.send(l)


	@client.command(name='version', brief='Show version')
	async def version(ctx):
		await ctx.send(f'Bot version v{VERSION}. Written by CraftyElk :D')

	@client.command(name='instance', brief='Show instance')
	@commands.is_owner()
	async def version(ctx):
		await ctx.send(f'Instance: {wbu.uuid}')

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
		wbu.ignoremode = True
		await ctx.send(f'Going into ignore mode. Use `.ignoremode disable` to get out.')


	@client.command(name='guide', brief='Show guide')
	@commands.is_owner()
	async def guide(ctx: commands.Context):
		for idx, s in enumerate(GUIDE_STR):
			emb = discord.Embed(title='Guide', description=s)
			emb.set_footer(text=f'Page {idx+1}/{len(GUIDE_STR)}')

			await ctx.send(embed=emb)
		await ctx.message.delete()


	@client.command(name='reset', brief='Reset bot state')
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
		summary = wbu.wave.get_wave_summary()
		wbu.reset_wave()
		await ctx.send(summary)


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
			wbu.wave.add_participant(m.display_name)


	@client.command(name='fc', brief='Set/list in-game fc')
	async def fc(ctx, *, fc_name: str = ''):
		"""
		List the current in-game fc that people need to join.

		When called with an argument, sets the fc
		instead. Only available to hosts.
		"""
		if not fc_name:
			await ctx.send(f"FC: '{wbu.wave.fcname}'")
		else:
			wbu.wave.fcname = fc_name
			await ctx.send(f"Setting FC to: '{wbu.wave.fcname}'")


	@client.command(name='host', brief='Set host')
	async def host(ctx, host:str = ''):
		""" Sets `host` as host. Uses caller if none specified. """
		if host:
			wbu.wave.host = host
		wbu.wave.host = ctx.author.display_name
		await ctx.message.add_reaction(REACT_CHECK)


	@client.command(name='scout', brief='Add yourself to scout list')
	async def scout(ctx):
		wbu.wave.scoutlist.add(ctx.author.display_name)
		await ctx.message.add_reaction(REACT_CHECK)


	@client.command(name='anti', brief='Add yourself to anti list')
	async def anti(ctx):
		wbu.wave.antilist.add(ctx.author.display_name)
		await ctx.message.add_reaction(REACT_CHECK)


	@client.command(name='call', brief='Add msg to call history')
	async def call(ctx, *, msg: str):
		wbu.wave.worldhist.append(msg)
		await ctx.message.add_reaction(REACT_CHECK)


	@client.command(name='dead', brief='Mark worlds as dead', aliases=['d'])
	async def mark_dead(ctx, *args):
		"""
		Mark some worlds as dead. If the 1st argument is a range (eg '1-10')
		then it will mark ALL worlds between those two numbers dead, inclusive
		of the endpoints.
		"""
		if not len(args) > 0:
			return

		# Support ranges for this command only
		worlds = []
		range, _ = parser.match_range(args[0])
		if range:
			lower, upper = range
			worlds = [x for x in P2P_WORLDS if x >= lower and x <= upper]
		else:
			worlds = [int(x) for x in args]

		for w in worlds:
			wbu.wave.get_world(w).mark_dead()
		await ctx.message.add_reaction(REACT_CHECK)


	# @client.command(name='wbs', brief='Show next wave information')
	# async def wbs(ctx):
	# 	""" Returns the time to and of next wave in several timezones. """
	# 	await ctx.send(next_wave_info())


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

		ret = wbu.wave.take_worlds(
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
		wbu.wave.mark_noinfo_dead_for_assignee(ctx.author.id)
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


	@client.command(name='clear', brief='Delete previous messages')
	@commands.has_role(ROLE_HOST)
	async def clear(ctx: commands.Context, num: int):
		"""
		Deletes the previous [num] messages from the channel. Will automatically
		add 1 to the [num] passed in so the user doesn't have to also count the
		`.clear x` command itself.

		Can only be used by hosts.
		"""
		messages = await ctx.channel.history(limit=num+1).flatten()
		await ctx.channel.delete_messages(messages)
		return