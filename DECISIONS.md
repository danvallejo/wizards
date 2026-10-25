# Decisions made

## Language / Framework
Went with Python / SQLLite because it's a simple framework and had the least number of moving parts. I prefer to use the simplest technology that I of course have used in the past.

## 30 person max
Each template has a configurable max rather than a hardcode because this one of the things that could change in the future.

## Duplicate registrations
I went based on a name and didn't use email as an identifier because I thought maybe a single person could play multiple roles in a single game. Using email could limit that feature unless they used different emails which might be combersome for a player.

## Event location for ics file
Use a STORE_LOCATION as a configurable default with the ability to override it. This would cover offsite gaming or one-off situations. This gives you a little more flexibility and doesn't force you to enter the location each time a game is set up.

## Event timezone
Use a STORE_TZ as a configurable default with the ability to override it. All times will be stored in UTC in the database. The duration is stored in minutes so it's easy to change/store.

## min-players and play format
Template properties are used for formats (organizer picks one and is validated server-side), max_capacity, and min_players (is displayed but not enforced). min_players is not enforced because maybe you want to start the game regardless of the number, again flexibility.

## Url for QR code
Use a BASE_URL as a configurable default with the ability to override it. If it is not set, default to http://<autodetectIP>:8000 so at least there's a default.

## Creating Past events
This is a new system and maybe you want to be able to show previous events to show that you are an active store. This is a way to seed your system.

## How much verification for the 3h test
I asked for basic tests across the entire system to timebox it.

## Commits
I authorized it to do commits as needed.

## Use codex to review work
Yes before each commit. Two AIs are better than one to check each others work.

## Games
What if a game is removed? Snapshot the name of the game into the event.

## DST Time Gap
Just reject it. It happens two nights a year. We can fix that later if needed.

# AI Framework
## Tools
Used claude code with /old-coder plugin. I didn't use PDLC-os because I was worried that brainstorming would have taken up the entire time by answering the storming portion of the lifecycle.

Prompt:

``/old-coder Senior_Software_Engineer_—_Take-Home.md contains the spec to implement. look for any gaps in the spec or assumptions include conflicting information. ask me if anything is unclear, one question at a time.``
