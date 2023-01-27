# Worldbot

v4.0.3

- Add message_content intent (how did it not break until now?)
- Add newlines to logs
- Fix `.clear` command to updated `discord.py` message history API

v4.0.2

- Fix missing message handler registration
- Add `.instance` command
- Fix error when using `list` but previous message does not exist

v4.0.1

- Fix regression where members don't have their roles taken away upon leaving VC

v4.0.0

- Merge rsbots repo into this repo
- Move worldbot into its own directory
- Major refactor
- Fix bug where bot reconnection registered multiple periodic tasks
- Remove bad/good bot feature
- Add UUID field to bot and display it on startup
- Remove friendlybot workaround

v3.23.2

- Minor welcome message change

v3.23.1

- Update to new discord intents API requirement
- Add feature to send welcome messages to new members

v3.23.0

- Add temporary workaround to delete ticket creation messages for friendlybot

v3.22.0
- `list` embed now displays in one horizontal line per location (fields are no longer inline) 

v3.21.1
- New `.dead/.d` option: you can now specify ranges (ie `.d 1-100`)
- `list` now return an embed
- Final fix to minigames worlds to work with new list
- `.clear` now works in more channels
- `.guide` now also returns an embed