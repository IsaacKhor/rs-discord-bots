#!/usr/bin/env python3

import discord
import discord.ext.commands as commands
import aiohttp
import json
import atexit

TIERS = ['low', 'med', 'high']

def list_tostr(lst):
	if len(lst) == 0:
		return 'None available'
	s = ''
	for i in range(len(lst)):
		s += f'{i}: {lst[i]}\n'
	return s


class TierBot(object):
	# Lists are thread safe and if ppl remove and add at the same time
	# they're fucked anyways because I'm too lazy
	def __init__(self):
		self.low = []
		self.med = []
		self.high = []

	def to_file(self, path):
		l = [self.low, self.med, self.high]
		with open(path, 'w') as f:
			json.dump(l, f)

	def from_file(self, path):
		with open(path, 'r') as f:
			try:
				l = json.load(f)
			except json.decoder.JSONDecodeError:
				l = []
		# Only continue loading if file is well-defined
		if len(l) == 3:
			self.low = l[0]
			self.med = l[1]
			self.high = l[2]

	def get_low_str(self):
		return list_tostr(self.low)

	def get_med_str(self):
		return list_tostr(self.med)

	def get_high_str(self):
		return list_tostr(self.high)

	def get_lst(self, tier):
		tier = tier.strip().lower()
		if tier == 'low':
			return self.low
		elif tier == 'med' or tier == 'mid':
			return self.med
		elif tier == 'high':
			return self.high
		else:
			return None

	def __str__(self):
		return str(self.low) + str(self.med) + str(self.high)


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
    await ctx.send(f'{type(err)}\n {str(err)}')

# Channel IDs
MESSAGE_CHANNEL = 770518655511429150
EDIT_CHANNEL = 790703022023376916

# Role IDs
ROLE_ADMIN = 771720121990643732
ROLE_EDITOR = 770192180936441867
ROLE_OWNER = 770191914279370753
EDIT_ROLES = [ROLE_ADMIN, ROLE_OWNER, ROLE_EDITOR]
ROLE_HIGH = 790701293353172993
ROLE_MED = 790701504402554940
ROLE_LOW = 790701649895096352


@client.listen('on_message')
async def process_msg(msg):
	if msg.channel.id == MESSAGE_CHANNEL or msg.channel.id == EDIT_CHANNEL:
		roles = msg.raw_role_mentions
		if ROLE_HIGH in roles:
			await msg.channel.send(tierbot.get_high_str())
		elif ROLE_MED in roles:
			await msg.channel.send(tierbot.get_med_str())
		elif ROLE_LOW in roles:
			await msg.channel.send(tierbot.get_low_str())


@client.command(
	name='add',
	help='Add to tier.\n<item> can be "all" to remove all items from that tier.')
@commands.check_any(
	commands.has_role(ROLE_ADMIN),
	commands.has_role(ROLE_EDITOR),
	commands.has_role(ROLE_OWNER) )
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
	commands.has_role(ROLE_OWNER) )
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


@client.command(
	name='high',
	aliases=['top'],
	help='High tier names')
async def list_high(ctx):
	await ctx.send(tierbot.get_high_str())


@client.command(
	name='med',
	aliases=['medium', 'mid'],
	help='Medium tier names')
async def list_high(ctx):
	await ctx.send(tierbot.get_med_str())


@client.command(
	name='low',
	help='Low tier names')
async def list_high(ctx):
	await ctx.send(tierbot.get_low_str())


@client.command(name='debug', help='list debug info')
async def get_state(ctx):
    await ctx.send(str(tierbot))


import sys
if len(sys.argv) < 2:
    print("Usage: ./tierbot.py <token>")

client.run(sys.argv[1])
