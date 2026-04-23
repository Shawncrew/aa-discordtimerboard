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
- Per-channel command access control:
  - optional required Discord role IDs
  - optional requirement for AA permission `structuretimers.add_timer`

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

3) Configure channels (either DB-backed in admin, or static fallback in `local.py`).

### Option A: DB-backed (recommended)

Run migrations:

```bash
python manage.py migrate
```

Then add one or more `Discord Timerboard Config` rows in Django admin.

Each config also supports:
- `required_role_ids`: comma-separated Discord role IDs (optional)
- `require_structuretimers_add_perm`: toggle AA permission enforcement for add/remove

### Option B: static settings fallback

```python
DISCORDTIMERBOARD_SERVERS = {
    "main": {
        "timerboard": 123456789012345678,
        "commands": 234567890123456789,
        "required_role_ids": "111111111111111111,222222222222222222",
        "require_structuretimers_add_perm": True,
    },
}
```

4) (Optional) Tune refresh behavior:

```python
DISCORDTIMERBOARD_UPDATE_INTERVAL = 60
DISCORDTIMERBOARD_PAST_GRACE_MINUTES = 240
```

5) Restart services (web, worker, beat, aadiscordbot).

6) Sync slash commands in Discord (if your bot requires manual sync/restart for command registration).

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
