
import math


def _valid_number(value):
    if isinstance(value, bool):
        return None

    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    if not math.isfinite(value) or value < 0:
        return None

    return value


def assess_player_constraints(snapshot, *, tick=None, max_age_ticks=16):
    result = {
        "status": "unknown",
        "sample_tick": None,
        "age_ticks": None,
        "limitations": [],
        "unknown_fields": [],
        "evidence": {},
        "shooting_feasibility": "not_established",
    }

    if snapshot is None:
        result["limitations"].append("player_state_unavailable")
        return result

    sample_tick = snapshot.get("sample_tick")
    result["sample_tick"] = sample_tick

    if tick is not None:
        try:
            age = int(tick) - int(sample_tick)
        except (TypeError, ValueError, OverflowError):
            result["limitations"].append("sample_tick_unknown")
            return result

        result["age_ticks"] = age

        if not 0 <= age <= max_age_ticks:
            result["limitations"].append("stale_player_state")
            return result

    status = snapshot.get("status") or {}
    weapon = snapshot.get("weapon") or {}

    alive = status.get("is_alive")
    flash = _valid_number(status.get("flash_duration"))
    reloading = weapon.get("is_reloading")
    ammo = _valid_number(weapon.get("clip_ammo"))

    result["evidence"] = {
        "is_alive": alive,
        "flash_duration": flash,
        "is_reloading": reloading,
        "clip_ammo": ammo,
        "active_weapon": weapon.get("active"),
    }

    if alive is False:
        result["status"] = "unavailable"
        result["limitations"].append("player_dead")
        return result

    if alive is not True:
        result["unknown_fields"].append("is_alive")

    if flash is None:
        result["unknown_fields"].append("flash_duration")
    elif flash > 0:
        result["limitations"].append("flash_effect_observed")

    if not isinstance(reloading, bool):
        result["unknown_fields"].append("is_reloading")
    elif reloading:
        result["limitations"].append("reloading")

    if ammo is None:
        result["unknown_fields"].append("clip_ammo")
    elif ammo == 0:
        result["limitations"].append("magazine_empty")

    if weapon.get("active") is None:
        result["unknown_fields"].append("active_weapon")

    if result["limitations"]:
        result["status"] = "limitations_observed"
    elif result["unknown_fields"]:
        result["status"] = "partial"
    else:
        result["status"] = "no_observed_limitation"

    return result
