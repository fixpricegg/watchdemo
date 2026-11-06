
import math


def assess_trade_readiness(snapshot):
    result = {
        "status": "unknown",
        "reasons": [],
        "evidence": {},
    }

    if snapshot is None:
        result["reasons"].append("player_state_unavailable")
        return result

    status = snapshot.get("status") or {}
    weapon = snapshot.get("weapon") or {}

    alive = status.get("is_alive")
    flash = status.get("flash_duration")
    reloading = weapon.get("is_reloading")
    ammo = weapon.get("clip_ammo")

    result["evidence"] = {
        "is_alive": alive,
        "flash_duration": flash,
        "is_reloading": reloading,
        "clip_ammo": ammo,
    }

    if alive is False:
        result["status"] = "unavailable"
        result["reasons"].append("player_dead")
        return result

    if alive is not True:
        result["reasons"].append("alive_state_unknown")
        return result

    if flash is not None:
        try:
            flash = float(flash)
            if not math.isfinite(flash) or flash < 0:
                flash = None
        except (TypeError, ValueError, OverflowError):
            flash = None

    if flash is not None and flash > 0:
        result["reasons"].append("flash_effect_active")

    if reloading is True:
        result["reasons"].append("reloading")

    if ammo is not None:
        try:
            ammo = int(ammo)
            if ammo == 0:
                result["reasons"].append("magazine_empty")
        except (TypeError, ValueError, OverflowError):
            pass

    if result["reasons"]:
        result["status"] = "limited"
    else:
        result["status"] = "no_observed_limitation"

    return result
