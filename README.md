# Worldbot, the TS and discord bot designed for Warbands

1. Clone somewhere `git clone https://github.com/IsaacKhor/worldbot`
2. Configure the script with the correct parameters, they are at the top
   of the file and are fairly self-explanatory (host, port, etc)
3. Start a TS3 client instance with the ClientQuery plugin running
4. Make sure bot is in the required channel, bot will not move there itself
5. Run the script `./worldbot-ts3client.py <api-token-for-clientquery-plugin>`

The bot works by communicating with the ClientQuery plugin of the TS3
client, which lets it programatically control the client and respond
to messages.

Worldbot instructions:

**Commands**:
- **list** - lists summary of current status
- **.help** - show this help message
- **.reset** - reset bot for next wave
- **.debug** - show debug information
- **.reload** - paste multiple lines from TS to re-parse. It will take
  input of the form listed below and re-parse it line-by-line.

```
.reload <00:00:00> 'username': 10 elm hcf
<00:00:00> 'username': 10 elm hcf
<00:00:00> 'username': 10 elm hcf
<00:00:00> 'username': 10 elm hcf
<00:00:00> 'username': 10 elm hcf
```

**Scouting commands** - The bot accepts any commands starting with a number
followed by any of the following (spaces are optional for each command):
- **'dwf|elm|rdi|unk'** will update the world to that location, 'unk' is unknown
- **'dead'** will mark the world as dead
- **'dies :07'** marks the world as dying at :07
- **'beaming'** will mark the world as being actively beamed
- Any combination of 3 of 'hcmfs' to add the world's tents
- **'beamed :02'** to mark world as beamed at 2 minutes past the hour.
- **'beamed'** with no number provided bot uses current time
- **'xx:xx gc'** for 'xx:xx' remaining on the game clock. The seconds part is optional
- **'xx:xx mins'** for xx:xx remaining in real time. The seconds part is optional
- **'xx:xxm'** m is short for mins
- **'xx:xx'** if 'gc' or 'mins' is not specified its assumed to be gameclock

So for example:
- '119dwf 10gc' marks world as dying in 10\\*0.6=6 minutes
- '119 mhs 4:30mins' marks the world as dying in 4:30 minutes
- '119 mhs 4m' marks the world as dying in 4 minutes
- '28 dead'
- '84 beamed02 hcf clear', you can combine multiple commands

Further notes:
- Spaces are optional between different information to update a world. That
  means '10elmhcf7m' is just as valid as '10 elm hcf 7m'.
- For all time inputs the colon and seconds part is optional. For example,
  both '7' and '7:15' are both perfectly valid times, but not '715'.

