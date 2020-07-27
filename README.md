# Worldbot, the TS and discord bot designed for Warbands

The bot has two possible frontends: TeamSpeak3 and Discord.

## Discord frontend

1. Clone the repo `git clone --recurse-submodules https://github.com/IsaacKhor/worldbot`
2. Create an app and a discord bot in Discord [here](https://discord.com/developers/applications)
3. Invite the bot to your server
4. Modify the script to specify which channels to listen
5. Run the script `./worldbot-discord.py <bot-token>`

The bot only requires the permission to read and send text messages (permission
number 3072). I would not recommend giving it more than that.

## TS3 frontend

1. Clone somewhere `git clone --recurse-submodules https://github.com/IsaacKhor/worldbot`
2. Install requirements (`blinker`, install with `pip3 install blinker`)
3. Configure the script with the correct parameters, they are at the top
   of the file and are fairly self-explanatory (host, port, username, password,
   etc.)
4. Run the script `./worldbot-ts3.py <password-for-serverquery-acc>`

The TS bot requires a ServerQuery account with permissions to receive and send
textmessages. I would not recommend giving it an admin account just in case
it messes something up.