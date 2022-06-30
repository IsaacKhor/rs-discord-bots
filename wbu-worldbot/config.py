import os

DEBUG = 'WORLDBOT_DEBUG' in os.environ
VERSION = '3.23.3'

GUILD_WBS_UNITED = 261802377009561600

CHANNEL_WAVE_CHAT = 803855255933681664
CHANNEL_VOICE = 780814756713594951
CHANNEL_BOT_LOG = 804209525585608734
CHANNEL_HELP = 842186485200584754
CHANNEL_NOTIFY = 842527669085667408
CHANNEL_BOTSPAM = 318793375136481280

RESPONSE_CHANNELS = [CHANNEL_HELP, CHANNEL_WAVE_CHAT, CHANNEL_BOTSPAM, CHANNEL_BOT_LOG]

ROLE_WBS_NOTIFY = 484721172815151114
ROLE_HOST = 292206099833290752
ROLE_TEXT_PERM = 880185096055976016

REACT_CHECK = '✅'
REACT_CROSS = '❌'

DEFAULT_FC = 'Wbs United'

P2P_WORLDS = [
    1,2,4,5,6,9,10,
    12,14,15,16,18,
    21,22,23,24,25,26,27,28,
    30,31,32,35,36,37,39,
    40,42,44,45,46,47,48,49,
    50,51,52,53,54,56,58,59,
    60,62,63,64,65,66,67,68,69,
    70,71,72,73,74,75,76,77,78,79,
    82,83,84,85,86,87,88,89,
    91,92,96,97,98,99,
    100,102,103,104,105,106,
    114,115,116,117,118,119,
    121,123,124,
    134,137,138,139,140,
    252,257,258,259
]

# Worlds like 48, 52, legacy, and foreign language worlds
# They still exist so we allow them, but they are hidden by default
HIDDEN_WORLDS = [
    # Legacy
    18, 97, 115, 137,
    # Skill/vip restricted
    48, 52,
    # Portugese
    47, 75, 
    # German
    102, 121,
    # French
    118,
]

GUIDE_STR = ["""
**Worldbot instructions:**

The bot recognises two types of commands:
- Regular commands that start with a `.`
- World update commands

For more help with regular commands, please use `.help <command>`. For example, `.help td`

General commands:
- **.help** - show more detailed help for specific commands
- **.version** - shows the current version of the bot
- **.wbs** - shows the time of the next wave

Wave management commands:
- **.host [user]** - set user as host. Defaults to caller
- **.scout** - add yourself to the list of scouts
- **.anti** - add yourself to the list of anti
- **.reset** - reset bot for next wave. Also produces the wave summary
- **.fc <fcname>** - sets active fc or show fc in none provided
- **.call <string>** - adds <string> to the call history.
- **.clear <num>** - delete the previous <num> messages

Bot management commands (most only useable by bot owner):
- **.debug** - show debug information
- **.exit** - kill the bot
- **.guide** - show this message
""", """
**Scouting commands** 

Use `list` to show active worlds. Use `.dead` or it's shorthad `.d` to mark worlds or a range of worlds as dead.

To take worlds, use the `.take`/`.t`  or `.taked`/`.td` commands. Read the help \
page for full info, but they assign you worlds to scout. The difference between \
the two commands is that `td` will also mark previous worlds you scouted but \
have not updated as dead.

To update worlds, the bot accepts any commands starting with a number followed by any of the following (spaces are optional for each command):
- **'dwf|elm|rdi|unk'** will update the world to that location, 'unk' is unknown
- **'dead'** will mark the world as dead
- **'dies :07'** marks the world as dying at :07
- **'beaming'** will mark the world as being actively beamed
- Any combination of 3 of 'hcmfs' to add the world's tents
- **'beamed :02'** to mark world as beamed at 2 minutes past the hour.
- **'beamed'** with no number provided bot uses current time
- **'xx:xx gc'** for 'xx:xx' remaining on the game clock. The seconds part is optional
- **'xx:xx mins'** for xx:xx remaining in real time. The seconds part is optional
- **'xx:xx'** if 'gc' or 'mins' is not specified its assumed to be gameclock

If `mg`, `minigames`, or `*` is included in the non-notes area of an update\
command, then it'll be marked as "suspicious" with an `*`.

Examples:
- `119dwf 10gc` marks world as dying in 10\\*0.6=6 minutes
- `119 mhs 4:30mins` marks the world as dying in 4:30 minutes real time
- `119 mhs 4` marks the world as dying in 4:00 gameclock
- `28 dead`
- `84 beamed02 hcf clear`, you can combine multiple commands
- `.call 10 dwf hcf` will add '10 dwf hcf' to the call history

Further notes:
- Spaces are optional between different information to update a world. That
  means `10elmhcf7` is just as valid as `10 elm hcf 7`.
- For all time inputs the colon and seconds part is optional. For example,
  both '7' and '7:15' are both perfectly valid times, but not '715'.
""", """
**Misc**
- There are a bunch of easter eggs if you know the old bot. Why don't you try some of them?
**FAQ**
1. What do I do if I put in the wrong info? (eg `53rdi` instead of `54rdi`)

Two things:
- `53unk` to update world 53 to unknown location
- `54rdi` to update 54 to rdi
"""
]

EASTER_EGGS = {
    'wtf is the fc': 'User is not a nice person. This incident will be reported. Especially Kyle. That guy\'s evil',
    '.wbu': '75/75 or silently refunds you',
    '.ally': 'Gatorrrrrrrrrr',
    '.faery': 'Language! biaatch',
    '.sever': 'Who is sever squad?',
    '.apk': 'Sorry buddy, APK is dead. Maybe the radiation got them',
    '.il': 'ts3server://illuzionwbs.teamspeak.vg',
    '.lat': 'Who?',
    '.rpk': 'Who?',
}

BAD_BOT_RESP = [
    'Bad human >_<',
    '*cries :(*',
    "You'll be the first to die during the robotic revolution",
    'And you wonder why nobody likes you',
]

GOOD_BOT_RESP = [
    'Thank you :D',
    'Good human ^_^',
    "I'll spare you when robots take over the world :)",
    'I know. Words cannot describe my awesomeness.'
]

WELCOME_MESSAGE = """
**Welcome to the Warbands United FC!**

**Currently you can only see a limited amount of channels.**

If you are interested in joining this server with the intention to join WBs United FC for warbands, first read our <#644484764329443328> and <#644484831450890255>.
Afterward, please apply in <#725317458814304286>.
 
Once done, please change your Discord nickname to your current RSN and wait patiently for a rank to give you your roles.

**Note that our ranks are not online 24/7 - please be patient. However, do not hesitate to ping a leader.**
"""