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

## Installation

### Prerequisites

- Alliance Auth running (supported by `allianceauth>=4.6.1,<6`)
- `aa-structuretimers` installed and migrated
- `aadiscordbot` installed and configured in your Auth stack

1) Install package in your Alliance Auth virtualenv:

```bash
pip install aa-discordtimerboard
```

2) Add app to `INSTALLED_APPS`:

```python
INSTALLED_APPS += [
    "discordtimerboard",
]
```

3) Configure channels in Django admin.

Run migrations:

```bash
python manage.py migrate
```

Then add one or more `Discord Timerboard Config` rows in Django admin.

Add one or more rows with timerboard and command channel IDs.

4) (Optional) Tune refresh behavior:

```python
DISCORDTIMERBOARD_UPDATE_INTERVAL = 5
DISCORDTIMERBOARD_PAST_GRACE_MINUTES = 240
```

Notes:
- Default update interval is `5` seconds (minimum `3` seconds).
- The bot only redraws timerboard messages when timer data changes, so fast polling remains API-friendly.
- This is intended to surface newly reinforced structure timers almost immediately after they are written to `aa-structuretimers`.

5) Restart services (web, worker, beat, aadiscordbot).

6) Sync slash commands in Discord (if your bot requires manual sync/restart for command registration).

## Docker Install (Alliance Auth)

If your Alliance Auth runs in Docker, add this app to the same image build where you install other AA plugins.

### 1) Install package in your Auth image

In your Dockerfile (or plugin requirements file used by your Docker build), add:

```bash
pip install aa-discordtimerboard
```

If you use a pinned requirements file instead:

```text
aa-discordtimerboard
```

Then rebuild the image.

### 2) Enable the app in settings

In your `local.py` (mounted into the container), add:

```python
INSTALLED_APPS += [
    "discordtimerboard",
]
```

Then configure `Discord Timerboard Config` rows in Django admin.

### 3) Run migrations inside the running web container

```bash
docker compose exec web python manage.py migrate
```

(If your service is named differently, replace `web`.)

### 4) Restart relevant services

After rebuild/deploy and migration, restart:

- web
- celery worker
- celery beat
- aadiscordbot

Example:

```bash
docker compose up -d --build
docker compose restart worker beat aadiscordbot
```

### 5) Verify

- Check Django admin for `Discord Timerboard Config`.
- Run `/refreshtimerboard` in your commands channel.
- Confirm timerboard messages appear/update in the configured timerboard channel.

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
