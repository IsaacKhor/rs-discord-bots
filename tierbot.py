#!/usr/bin/env python3

import discord
import discord.ext.commands as commands
import aiohttp
import json
import atexit

TIERS = ['low', 'high']

def list_tostr(lst, include_numbers=False):
	if len(lst) == 0:
		return 'None available'
	s = ''
	for i in range(len(lst)):
		if include_numbers:
			s += f'{i}: {lst[i]}'
		else:
			s += f'{lst[i]}\n'
	return s


class TierBot(object):
	# Lists are thread safe and if ppl remove and add at the same time
	# they're fucked anyways because I'm too lazy
	def __init__(self):
		self.low = []
		self.high = []

	def to_file(self, path):
		l = [self.low, self.high]
		with open(path, 'w') as f:
			json.dump(l, f)

	def from_file(self, path):
		with open(path, 'r') as f:
			try:
				l = json.load(f)
			except json.decoder.JSONDecodeError:
				l = []
		# Only continue loading if file is well-defined
		if len(l) == 2:
			self.low = l[0]
			self.high = l[1]

	def get_low_str(self):
		return list_tostr(self.low)

	def get_high_str(self):
		return list_tostr(self.high)

	def get_lst(self, tier):
		tier = tier.strip().lower()
		if tier == 'low':
			return self.low
		elif tier == 'high':
			return self.high
		else:
			return None

	def __str__(self):
		return str(self.low) + str(self.high)


conn = aiohttp.TCPConnector(ssl=False)
client = commands.Bot(
    command_prefix = ['$', '!'],
    case_insensitive = True,
    self_bot = False,
    connector = conn)
tierbot = TierBot()
SAVE_PATH = 'tiers.json'
tierbot.from_file(SAVE_PATH)

@atexit.register
def write_to_file():
	tierbot.to_file(SAVE_PATH)


@client.listen('on_ready')
async def on_ready():
    print('Logged is as {}'.format(client.user))


@client.listen('on_command_error')
async def on_command_error(ctx, err):
	if type(err) == discord.ext.commands.errors.CommandNotFound:
		return
	print(f'{type(err)}\n{str(err)}')

# Channel IDs
MESSAGE_CHANNEL = 770189011045974040
EDIT_CHANNEL = 790703022023376916

# Role IDs
ROLE_ADMIN = 771720121990643732
ROLE_EDITOR = 770192180936441867
ROLE_OWNER = 770191914279370753
EDIT_ROLES = [ROLE_ADMIN, ROLE_OWNER, ROLE_EDITOR]
ROLE_HIGH = 790701293353172993
ROLE_LOW = 790701649895096352


def process_txt(txt):
	if txt == '!high' or txt == '$high':
		return 'High tier names:\n' + list_tostr(tierbot.high)
	elif txt == '!low' or txt == '$low':
		return 'Low tier names:\n' + list_tostr(tierbot.low)
	else:
		return f'Invalid command: "{txt}". Please double check your spelling.'


@client.listen('on_message')
async def process_msg(msg):
	if msg.channel.id == MESSAGE_CHANNEL:
		txt = msg.content.strip().lower()
		ret = process_txt(txt)
		await msg.author.send(ret)
		await msg.delete()

		if any(r in EDIT_ROLES for r in msg.author.roles):
			await msg.delete()


@client.command(
	name='helpmsg',
	help='Prints out the pretty help message')
@commands.check_any(
	commands.has_role(ROLE_ADMIN),
	commands.has_role(ROLE_EDITOR),
	commands.has_role(ROLE_OWNER) )
async def helpmsg(ctx):
	await ctx.send(
f'''> Hello! Remember to enable DMs from server 
> members, as that's how the bot will send you 
> the name lists.
> 
> For more impormation, contact
> DM: Soph#9090 (Capital S)
> UID: 220055946506928128
> 
> Remember to verify the UID of the seller
> before any transaction. There have been multiple
> reports of scammers impersonating sellers and
> running with the money, so please make sure
> that you're contacting the right person.
> 
> __**Commands**__:
> **!low** - low tier names
> **!high** - high tier names
> 
> Once you type your command in this channel it
> will be automatically deleted and the bot will
> DM you with the response.
''')


def is_edit_channel(ctx):
	return ctx.channel.id == EDIT_CHANNEL


@client.command(
	name='adminlist',
	help='List but with numbers so admins know which to delete')
@commands.check_any(
	commands.has_role(ROLE_ADMIN),
	commands.has_role(ROLE_EDITOR),
	commands.has_role(ROLE_OWNER),
	commands.check(is_edit_channel))
async def adminlist(ctx):
	return f'High:\n{list_tostr(tierbot.high)}\n\nLow:{list_tostr(tierbot.low)}'


@client.command(
	name='add',
	help='Add to tier.\n<item> can be "all" to remove all items from that tier.')
@commands.check_any(
	commands.has_role(ROLE_ADMIN),
	commands.has_role(ROLE_EDITOR),
	commands.has_role(ROLE_OWNER),
	commands.check(is_edit_channel))
@commands.max_concurrency(1, wait=True)
async def add_to_tier(ctx, tier, *, items):
	lst = tierbot.get_lst(tier)
	if lst == None:
		await ctx.send(f'Invalid tier: {tier}')
		return

	for itm in items.split('\n'):
		lst.append(itm)

	await ctx.send(f'Successfully added the following to {tier}:\n{items}')


@client.command(
	name='rm',
	help='Remove entry from list')
@commands.check_any(
	commands.has_role(ROLE_ADMIN),
	commands.has_role(ROLE_EDITOR),
	commands.has_role(ROLE_OWNER),
	commands.check(is_edit_channel))
@commands.max_concurrency(1, wait=True)
async def remove_from_tier(ctx, tier, *, item):
	lst = tierbot.get_lst(tier)
	if lst == None:
		await ctx.send(f'Invalid tier: {tier}')
		return

	if item == 'all':
		lst.clear()
		await ctx.send(f'Removed all items from tier {tier}')
		return

	if item in lst:
		lst.remove(item)
		to_be_removed = item
	elif item.isnumeric():
		idx = int(item)
		if not (idx >= 0 and idx < len(lst)):
			await ctx.send(f'Invalid index: {idx}')
			return
		to_be_removed = lst[idx]
		del lst[idx]

	await ctx.send(f'Removed from {tier}: {to_be_removed}')


@client.command(name='debug', help='list debug info')
@commands.check_any(
	commands.has_role(ROLE_ADMIN),
	commands.has_role(ROLE_EDITOR),
	commands.has_role(ROLE_OWNER),
	commands.check(is_edit_channel))
async def get_state(ctx):
    await ctx.send(str(tierbot))


import sys
if len(sys.argv) < 2:
    print("Usage: ./tierbot.py <token>")

client.run(sys.argv[1])
