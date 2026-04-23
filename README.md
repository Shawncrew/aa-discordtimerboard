# aa-discordtimerboard

Alliance Auth extension that reads `aa-structuretimers` timer data and keeps one or more Discord timerboard channels updated in a compact text format.

It also adds a Discord command channel parser so FCs/scouts can add timers with `!add` using the same formats your current `timerbot` expects.

## Features

- Uses `structuretimers.Timer` as the source of truth.
- Periodically refreshes configured timerboard channels.
- Supports command channels for:
  - `!add` to create timers from text
  - `!rm` to remove timers by id
  - `!refresh` to force redraw timerboards
  - `/addtimer`, `/removetimer`, `/refreshtimerboard` slash commands
- Add/remove command authorization uses Alliance Auth permission:
  - `structuretimers.add_timer`

## Output Format

Each line is rendered like:

`YYYY-MM-DD HH:MM:SS SYSTEM (REGION) STRUCTURE [OWNER][STRUCT][TYPE] (id)`

Example:

`2026-04-23 19:15:59 CL6-ZG (Pure Blind) Microplastic of Pure Blind [INIT][ASTRA][FINAL] (5292)`

## Installation (Docker - Recommended)

### Prerequisites

- Alliance Auth running in Docker (`allianceauth>=4.6.1,<6`)
- `aa-structuretimers` installed and migrated
- `aadiscordbot` installed and configured

### 1) Add plugin to your requirements file

Add this project to the requirements file your Alliance Auth Docker image installs:

```text
aa-discordtimerboard
```

If you pin plugin versions, pin it there as well.

Then rebuild/deploy the image so the container installs the updated requirements.

### 2) Enable app in `local.py`

```python
INSTALLED_APPS += [
    "discordtimerboard",
]
```

Optional tuning:

```python
DISCORDTIMERBOARD_UPDATE_INTERVAL = 5
DISCORDTIMERBOARD_PAST_GRACE_MINUTES = 240
```

Notes:
- Default update interval is `5` seconds (minimum `3` seconds).
- Timerboard redraws only when timer data changes (plus minute header updates), so it stays low-latency without excessive Discord edits.
- Reinforced timers should appear within a few seconds after they are written into `aa-structuretimers`.

### 3) Run migrations

```bash
docker compose exec web python manage.py migrate
```

(replace `web` with your service name if different)

### 4) Restart services

```bash
docker compose up -d --build
docker compose restart worker beat aadiscordbot
```

### 5) Configure channels in Django admin

Go to `/admin/` and add one or more `Discord Timerboard Config` rows:

- `name`
- `discord_server_id` (optional)
- `timerboard_channel_id`
- `commands_channel_id`
- `enabled`

### 6) Verify

- Run `/refreshtimerboard` in your configured commands channel.
- Confirm timerboard messages appear in the configured timerboard channel.

## Installation (Bare Metal / venv)

If you are not using Docker:

```bash
pip install aa-discordtimerboard
python manage.py migrate
```

Then follow the same `INSTALLED_APPS`, admin config, and service restart steps above.

## Command Formats

Supported `!add` formats:

1) Direct format:

`!add YYYY-MM-DD HH:MM:SS SYSTEM - STRUCTURE [TAGS]`

2) Reinforced format:

`!add SYSTEM - STRUCTURE Reinforced until YYYY.MM.DD HH:MM:SS [TAGS]`

3) Multiline (copied from in-game):

```
SYSTEM - STRUCTURE
distance line
Reinforced until YYYY.MM.DD HH:MM:SS [TAGS]
```

4) Mercenary Den relative format:

`!add Merc Den SYSTEM Planet I 2 30 [NC]`

Tags should usually be:

`[OWNER][STRUCTURE][TYPE]` e.g. `[NC][FORT][ARMOR]`

Additional parsing helpers are included for lines like:
- `Customs Office (DT-TCD IX) ...`
- `Orbital Skyhook (MQ-NPY I) ...`

## Slash Commands

- `/addtimer`
- `/removetimer`
- `/refreshtimerboard`
