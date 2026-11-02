
import math

from copy import deepcopy


def get_flash_effect(player):
    status = player.get("status") or {}
    duration = status.get("flash_duration")

    if isinstance(duration, bool):
        duration = None

    try:
        if duration is not None:
            duration = float(duration)
            if not math.isfinite(duration) or duration < 0:
                duration = None
    except (TypeError, ValueError, OverflowError):
        duration = None

    if duration is None:
        return {
            "status": "unknown",
            "remaining_duration": None,
        }

    return {
        "status": "observed_active" if duration > 0 else "observed_inactive",
        "remaining_duration": duration,
    }


def build_player_effects(
    players,
    *,
    tick,
    active_utility=None,
    recent_explosions=None,
):
    tick = int(tick)
    result_players = []

    for player in players:
        sample_tick = player.get("sample_tick")

        result_players.append({
            "steamid": player.get("steamid"),
            "sample_tick": sample_tick,
            "flash": get_flash_effect(player),
            "smoke_exposure": "not_evaluated",
            "fire_exposure": "not_evaluated",
            "he_damage": "not_evaluated",
        })

    return {
        "schema_version": "player_effects_v1",
        "tick": tick,
        "scope": "post_match_ground_truth",
        "players": result_players,
        "world_effects": deepcopy(active_utility),
        "recent_he_explosions": deepcopy(recent_explosions or []),
        "limitations": [
            "Flash status is based on sampled player state.",
            "Smoke and fire exposure are not evaluated.",
            "HE damage attribution is not evaluated.",
            "World effects are not automatically player knowledge.",
        ],
    }
