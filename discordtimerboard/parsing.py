import datetime as dt
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from django.utils import timezone


@dataclass
class ParsedTimerInput:
    timer_time: dt.datetime
    system: str
    structure_name: str
    tags: List[str]


def _make_aware_utc(value: dt.datetime) -> dt.datetime:
    return timezone.make_aware(value, dt.timezone.utc)


def _parse_structure_line(structure_line: str) -> Optional[Tuple[str, str]]:
    line = structure_line.strip()

    # SYSTEM - STRUCTURE
    dash_match = re.match(r"^([A-Za-z0-9-]+)\s*-\s*(.+)$", line)
    if dash_match:
        return dash_match.group(1).strip(), dash_match.group(2).strip()

    # Customs Office (DT-TCD IX)
    customs_match = re.match(r"^Customs Office\s+\(([A-Za-z0-9-]+)\s+([IVX]+)\)", line, re.IGNORECASE)
    if customs_match:
        system = customs_match.group(1).strip()
        planet = customs_match.group(2).strip()
        return system, f"Customs Office Planet {planet}"

    # Orbital Skyhook (MQ-NPY I)
    skyhook_match = re.match(r"^Orbital Skyhook\s+\(([A-Za-z0-9-]+)\s+([IVX]+)\)", line, re.IGNORECASE)
    if skyhook_match:
        system = skyhook_match.group(1).strip()
        planet = skyhook_match.group(2).strip()
        return system, f"Orbital Skyhook Planet {planet}"

    # Generic "<name> (SYSTEM IV)" fallback
    generic_sys_match = re.search(r"\(([A-Za-z0-9-]+)\s+[IVX]+\)", line)
    if generic_sys_match:
        return generic_sys_match.group(1).strip(), line

    return None


# Matches: 2026-04-16 07:01 [Pure Blind] Y2-6EA - Y2-6EA Planet 1 [Orbital Skyhook][P3WN/NC][Final] (5:02) [#Auth]
_BULK_LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2})"   # datetime (no seconds)
    r"\s+\[[^\]]+\]"                         # [region] — ignored
    r"\s+(\S+)"                              # system
    r"\s+-\s+"                               # separator
    r"(.+?)"                                 # structure name (lazy)
    r"\s+(\[[^\]]+\])"                       # [struct_type]
    r"(\[[^\]]+\])"                          # [owner]
    r"(\[[^\]]+\])"                          # [timer_type]
    r"\s+\([^)]+\)"                          # (remaining) — ignored
    r"(?:\s+\[[^\]]+\])?"                    # optional trailing [#tag] — ignored
    r"\s*$",
    re.IGNORECASE,
)


def parse_bulk_line(line: str) -> Optional[ParsedTimerInput]:
    """Parse one line of the bulk timer format."""
    m = _BULK_LINE_RE.match(line.strip())
    if not m:
        return None
    dt_str, system, structure_name, struct_bracket, owner_bracket, type_bracket = (
        m.group(1), m.group(2), m.group(3),
        m.group(4), m.group(5), m.group(6),
    )
    try:
        when = dt.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    struct_tag = struct_bracket.strip("[]")
    owner_tag = owner_bracket.strip("[]")
    timer_tag = type_bracket.strip("[]")
    return ParsedTimerInput(
        timer_time=_make_aware_utc(when),
        system=system.strip(),
        structure_name=structure_name.strip(),
        tags=[owner_tag, struct_tag, timer_tag],
    )


def parse_bulk_input(text: str) -> list:
    """Parse multiple lines, returning list of (line_num, raw_line, ParsedTimerInput|None)."""
    results = []
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        results.append((i, line, parse_bulk_line(line)))
    return results


def parse_add_input(input_text: str, now_utc: Optional[dt.datetime] = None) -> Optional[ParsedTimerInput]:
    text = input_text.strip()

    # Format 4: Merc Den <systemName> <planet...> <hours> <minutes> [TAG]
    merc_den = re.match(
        r"^Merc\s+Den\s+([A-Za-z0-9-]+)\s+(.+?)\s+(\d+)\s+(\d+)(?:\s+(\[[^\]]+\]))?\s*$",
        text,
        re.IGNORECASE,
    )
    if merc_den:
        system = merc_den.group(1).strip()
        planet = merc_den.group(2).strip()
        hours = int(merc_den.group(3))
        minutes = int(merc_den.group(4))
        owner_tag = merc_den.group(5).strip("[]") if merc_den.group(5) else "NC"
        base_now = now_utc or timezone.now()
        if timezone.is_naive(base_now):
            base_now = _make_aware_utc(base_now)
        timer_time = base_now + dt.timedelta(hours=hours, minutes=minutes)
        return ParsedTimerInput(
            timer_time=timer_time,
            system=system,
            structure_name=f"Mercenary Den {planet}",
            tags=[owner_tag, "MERCENARY DEN", "FINAL"],
        )

    # Format 1a: timerboard output format (copy-paste from timerboard channel)
    # e.g. 2026-04-23 19:15:59 CL6-ZG (Pure Blind) Microplastic [INIT][ASTRA][FINAL] (5292)
    # System name may be wrapped in a Discord markdown link: [CL6-ZG](<url>)
    # Region is optional (some timers have no region resolved).
    # Trailing (id) is optional.
    timerboard_line = re.match(
        r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+"
        r"(?:\[([A-Za-z0-9-]+)\]\(<[^>]+>\)|([A-Za-z0-9-]+))"  # [SYSTEM](<url>) or SYSTEM
        r"(?:\s+\([^)]+\))?"                                     # optional (Region)
        r"\s+(.+?)"                                              # structure name + tags
        r"(?:\s+\(\d+\))?\s*$",                                  # optional trailing (id)
        text,
    )
    if timerboard_line:
        when = dt.datetime.strptime(timerboard_line.group(1), "%Y-%m-%d %H:%M:%S")
        system = (timerboard_line.group(2) or timerboard_line.group(3)).strip()
        rest = timerboard_line.group(4).strip()
        tags = re.findall(r"\[([^\]]+)\]", rest)
        structure_name = re.sub(r"\s*(\[[^\]]+\])+\s*$", "", rest).strip()
        if system and structure_name:
            return ParsedTimerInput(
                timer_time=_make_aware_utc(when),
                system=system,
                structure_name=structure_name,
                tags=tags,
            )

    # Format 1b: direct timestamp line with dash separator
    direct = re.match(
        r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+([A-Za-z0-9-]+)\s*-\s*(.+)$",
        text,
    )
    if direct:
        when = dt.datetime.strptime(direct.group(1), "%Y-%m-%d %H:%M:%S")
        rest = direct.group(3).strip()
        tags = re.findall(r"\[([^\]]+)\]", rest)
        structure_name = re.sub(r"\s*(\[[^\]]+\])+\s*$", "", rest).strip()
        return ParsedTimerInput(
            timer_time=_make_aware_utc(when),
            system=direct.group(2).strip(),
            structure_name=structure_name,
            tags=tags,
        )

    # Format 2/3 reinforced variants
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    reinforced_line = next(
        (x for x in lines if "Reinforced until" in x or "Anchoring until" in x),
        None,
    )
    if reinforced_line:
        time_match = re.search(
            r"(?:Reinforced|Anchoring) until (\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})",
            reinforced_line,
        )
        if not time_match:
            return None
        when = dt.datetime.strptime(time_match.group(1), "%Y.%m.%d %H:%M:%S")
        tags = re.findall(r"\[([^\]]+)\]", reinforced_line)

        source_line = lines[0]
        parsed = _parse_structure_line(source_line)
        if not parsed:
            return None
        system, structure_name = parsed
        return ParsedTimerInput(
            timer_time=_make_aware_utc(when),
            system=system,
            structure_name=structure_name,
            tags=tags,
        )

    # Single-line reinforced fallback
    single = re.search(
        r"^(.+?)\s+(?:Reinforced|Anchoring)\s+until\s+(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})(?:\s+(.*))?$",
        text,
        re.IGNORECASE,
    )
    if single:
        prefix = single.group(1).strip()
        time_raw = single.group(2).strip()
        tag_raw = single.group(3) or ""
        parsed = _parse_structure_line(prefix)
        if not parsed:
            return None
        when = dt.datetime.strptime(time_raw, "%Y.%m.%d %H:%M:%S")
        tags = re.findall(r"\[([^\]]+)\]", tag_raw)
        return ParsedTimerInput(
            timer_time=_make_aware_utc(when),
            system=parsed[0],
            structure_name=parsed[1],
            tags=tags,
        )

    return None
