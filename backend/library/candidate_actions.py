
"""Decision-safe candidate action generation for WatchDemo.

Candidate generation is not decision evaluation.
No future ticks, enemy ground truth, or outcome labels are accepted.
"""

from copy import deepcopy
from math import isfinite, sqrt


SCHEMA_VERSION = "candidate_actions_v1"

UTILITY_TYPES = (
    "flashbang",
    "smokegrenade",
    "hegrenade",
    "molotov",
    "incgrenade",
)


def _position(value):
    if not isinstance(value, dict):
        return None

    try:
        coords = {
            axis: float(value[axis])
            for axis in ("x", "y", "z")
        }
    except (KeyError, TypeError, ValueError):
        return None

    if not all(isfinite(v) for v in coords.values()):
        return None

    return coords


def _distance(a, b):
    return sqrt(sum(
        (a[axis] - b[axis]) ** 2
        for axis in ("x", "y", "z")
    ))


def _candidate(
    action_id,
    action_type,
    *,
    feasibility,
    reason,
    parameters=None,
    evidence=None,
    limitations=None,
):
    return {
        "id": action_id,
        "type": action_type,
        "feasibility": feasibility,
        "reason": reason,
        "parameters": parameters or {},
        "evidence": evidence or [],
        "limitations": limitations or [],
        "score": None,
        "rank": None,
        "evaluation_status": "not_evaluated",
    }


def build_candidate_actions(
    decision_context,
    *,
    team_players,
    max_state_age_ticks=16,
):
    """Generate action candidates using information available at tick.

    Available: action is locally supported by observed state.
    Requires_validation: tactical or navigational feasibility is unknown.

    No candidate is automatically a recommendation.
    """
    tick = int(decision_context["tick"])
    perspective = decision_context["perspective"]
    player_id = str(perspective["steamid"])

    if max_state_age_ticks < 0:
        raise ValueError("max_state_age_ticks must be nonnegative")

    actor = next(
        (
            p for p in team_players
            if str(p.get("steamid")) == player_id
        ),
        None,
    )

    if actor is None:
        return []

    sample_tick = actor.get("sample_tick")

    if sample_tick is None:
        return []

    sample_tick = int(sample_tick)

    if not 0 <= tick - sample_tick <= max_state_age_ticks:
        return []

    status = actor.get("status") or {}

    # An explicit dead state blocks action generation.
    if status.get("is_alive") is not True:
        return []

    actor_position = _position(actor.get("position"))

    if actor_position is None:
        return []

    actions = [
        _candidate(
            "hold_position",
            "hold_position",
            feasibility="available",
            reason="Player has a current, valid position.",
            parameters={
                "position": deepcopy(actor_position),
                "horizon_ticks": None,
            },
            evidence=[
                {
                    "type": "player_position",
                    "source_tick": sample_tick,
                }
            ],
            limitations=[
                "Position may not be safe.",
                "No tactical value has been evaluated.",
                "Future survival is unknown.",
            ],
        )
    ]

    # Consider regrouping only with a currently observed,
    # alive teammate. This is not a validated route.
    teammates = []

    for teammate in team_players:
        teammate_id = str(teammate.get("steamid"))

        if teammate_id == player_id:
            continue

        teammate_tick = teammate.get("sample_tick")

        if teammate_tick is None:
            continue

        teammate_tick = int(teammate_tick)

        if not 0 <= tick - teammate_tick <= max_state_age_ticks:
            continue

        teammate_status = teammate.get("status") or {}

        if teammate_status.get("is_alive") is not True:
            continue

        teammate_position = _position(teammate.get("position"))

        if teammate_position is None:
            continue

        teammates.append((
            _distance(actor_position, teammate_position),
            teammate_id,
            teammate_tick,
            teammate_position,
        ))

    if teammates:
        teammates.sort(key=lambda entry: (entry[0], entry[1]))
        distance, teammate_id, teammate_tick, target = teammates[0]

        actions.append(
            _candidate(
                "regroup_with_teammate",
                "regroup",
                feasibility="requires_validation",
                reason="A living teammate has a recent known position.",
                parameters={
                    "target_steamid": teammate_id,
                    "target_position": deepcopy(target),
                    "straight_line_distance": round(distance, 2),
                    "route": None,
                },
                evidence=[
                    {
                        "type": "teammate_position",
                        "source_tick": teammate_tick,
                        "steamid": teammate_id,
                    }
                ],
                limitations=[
                    "Straight-line distance is not path distance.",
                    "Traversability has not been validated.",
                    "Enemy exposure has not been evaluated.",
                    "Target movement after this tick is unknown.",
                ],
            )
        )

    utility = decision_context.get("player_utility") or {}

    if utility.get("status") == "observed":
        counts = utility.get("counts") or {}

        for utility_type in UTILITY_TYPES:
            try:
                count = int(counts.get(utility_type, 0))
            except (TypeError, ValueError, OverflowError):
                count = 0

            if count <= 0:
                continue

            actions.append(
                _candidate(
                    f"consider_{utility_type}",
                    "use_utility",
                    feasibility="requires_validation",
                    reason="The utility type is present in the observed inventory.",
                    parameters={
                        "utility_type": utility_type,
                        "available_count": count,
                        "target": None,
                        "trajectory": None,
                    },
                    evidence=[
                        {
                            "type": "player_inventory",
                            "source_tick": sample_tick,
                        }
                    ],
                    limitations=[
                        "No throw trajectory has been validated.",
                        "Utility effectiveness is unknown.",
                        "Player animation and throw readiness are unverified.",
                    ],
                )
            )

    return actions
