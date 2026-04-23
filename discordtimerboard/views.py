import datetime as dt
import logging

from django.apps import apps
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from . import app_settings

logger = logging.getLogger(__name__)


def _check_api_key(request) -> bool:
    api_key = app_settings.DISCORDTIMERBOARD_API_KEY
    if not api_key:
        return True
    provided = (
        request.headers.get("X-API-Key")
        or request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    )
    return provided == api_key


def _timer_to_dict(timer) -> dict:
    region = ""
    try:
        region = timer.eve_solar_system.eve_constellation.eve_region.name
    except AttributeError:
        pass

    system = timer.eve_solar_system.name if timer.eve_solar_system_id else ""
    structure_name = (timer.structure_name or "").strip()
    structure_type = timer.structure_type.name if timer.structure_type_id else ""
    owner = (timer.owner_name or "").strip().strip("[]")
    timer_type = timer.get_timer_type_display().upper() if timer.timer_type else ""

    notes_parts = []
    if owner:
        notes_parts.append(f"[{owner}]")
    if structure_type:
        notes_parts.append(f"[{structure_type}]")
    if timer_type and timer_type != "NONE":
        notes_parts.append(f"[{timer_type}]")
    notes = "".join(notes_parts)

    description = f"{system} - {structure_name} {notes}".strip()

    return {
        "timer_id": timer.pk,
        "time": timer.date.isoformat() if timer.date else None,
        "system": system,
        "region": region,
        "structure_name": structure_name,
        "description": description,
        "notes": notes,
    }


@require_GET
def timers_api(request):
    if not app_settings.DISCORDTIMERBOARD_API_ENABLED:
        return JsonResponse({"error": "API is disabled"}, status=404)

    if not _check_api_key(request):
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if not apps.is_installed("structuretimers"):
        return JsonResponse({"error": "aa-structuretimers is not installed"}, status=503)

    Timer = apps.get_model("structuretimers", "Timer")
    cutoff = timezone.now() - dt.timedelta(
        minutes=app_settings.DISCORDTIMERBOARD_PAST_GRACE_MINUTES
    )
    timers = (
        Timer.objects.select_related(
            "eve_solar_system__eve_constellation__eve_region",
            "structure_type",
        )
        .filter(date__isnull=False, date__gte=cutoff)
        .exclude(timer_type="MM")
        .order_by("date", "pk")
    )

    return JsonResponse({"timers": [_timer_to_dict(t) for t in timers]})
