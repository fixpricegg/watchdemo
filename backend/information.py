import pandas as pd


def normalize_steamid(value):
    if value is None or pd.isna(value):
        return None

    try:
        return str(int(value))
    except (TypeError, ValueError):
        return None


def normalize_spotters(value):
    if value is None:
        return set()

    if hasattr(value, "tolist"):
        value = value.tolist()

    if not isinstance(value, (list, tuple, set)):
        return set()

    result = set()

    for steamid in value:
        normalized = normalize_steamid(steamid)

        if normalized is not None:
            result.add(normalized)

    return result


def normalize_number(value):
    if value is None or pd.isna(value):
        return None

    return float(value)

def attach_live_rounds(position_df, round_intervals):
    rounds_df = pd.DataFrame([
        {
            "round": int(match_round),
            "live_start_tick": int(live_start_tick),
            "live_end_tick": int(live_end_tick),
        }
        for (
            match_round,
            demo_round,
            live_start_tick,
            live_end_tick,
        )
        in round_intervals
    ])

    df = position_df.copy()

    df["tick"] = pd.to_numeric(
        df["tick"],
        errors="coerce",
    )

    df = df[
        df["tick"].notna()
    ].copy()

    df["tick"] = df["tick"].astype("int64")

    rounds_df["live_start_tick"] = (
        rounds_df["live_start_tick"]
        .astype("int64")
    )

    rounds_df["live_end_tick"] = (
        rounds_df["live_end_tick"]
        .astype("int64")
    )

    df = df.sort_values(
        "tick"
    ).reset_index(drop=True)

    rounds_df = rounds_df.sort_values(
        "live_start_tick"
    ).reset_index(drop=True)

    df = pd.merge_asof(
        df,
        rounds_df,
        left_on="tick",
        right_on="live_start_tick",
        direction="backward",
    )

    df = df[
        df["round"].notna()
        & (df["tick"] >= df["live_start_tick"])
        & (df["tick"] < df["live_end_tick"])
    ].copy()

    df["round"] = df["round"].astype(int)

    return df

def build_spot_events(
    position_df,
    round_intervals,
):
    required_columns = {
        "tick",
        "name",
        "steamid",
        "team_num",
        "X",
        "Y",
        "Z",
        "approximate_spotted_by",
    }

    missing_columns = required_columns - set(position_df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing columns for spot events: {sorted(missing_columns)}"
        )

    df = attach_live_rounds(
        position_df,
        round_intervals,
    )

    df = df[
        df["steamid"].notna()
        & df["tick"].notna()
    ]

    df = df.sort_values(
        ["steamid", "tick"]
    ).reset_index(drop=True)

    name_by_steamid = {}

    for _, row in df[
        ["steamid", "name"]
    ].drop_duplicates("steamid").iterrows():
        steamid = normalize_steamid(
            row["steamid"]
        )

        if steamid is None:
            continue

        name_by_steamid[steamid] = str(
            row["name"]
        )

    events = []

    for (
            target_steamid_raw,
            round_number,
    ), player_df in df.groupby(
        ["steamid", "round"],
        sort=False,
    ):
        target_steamid = normalize_steamid(
            target_steamid_raw
        )

        if target_steamid is None:
            continue

        previous_spotters = set()
        last_seen_by_spotter = {}

        for _, row in player_df.iterrows():
            tick = int(row["tick"])

            current_spotters = normalize_spotters(
                row["approximate_spotted_by"]
            )

            current_spotters.discard(
                target_steamid
            )

            started_spotters = (
                current_spotters
                - previous_spotters
            )

            ended_spotters = (
                previous_spotters
                - current_spotters
            )

            target_position = {
                "x": normalize_number(
                    row["X"]
                ),
                "y": normalize_number(
                    row["Y"]
                ),
                "z": normalize_number(
                    row["Z"]
                ),
            }

            for spotter_steamid in current_spotters:
                last_seen_by_spotter[
                    spotter_steamid
                ] = {
                    "tick": tick,
                    "position": target_position.copy(),
                }

            for spotter_steamid in started_spotters:
                events.append({
                    "type": "spot_start",
                    "round": int(round_number),
                    "tick": tick,

                    "spotter_steamid":
                        spotter_steamid,

                    "spotter_name":
                        name_by_steamid.get(
                            spotter_steamid
                        ),

                    "target_steamid":
                        target_steamid,

                    "target_name":
                        str(row["name"]),

                    "target_team": (
                        int(row["team_num"])
                        if not pd.isna(
                            row["team_num"]
                        )
                        else None
                    ),

                    "target_position":
                        target_position.copy(),
                })

            for spotter_steamid in ended_spotters:
                last_seen = (
                    last_seen_by_spotter.get(
                        spotter_steamid
                    )
                )

                events.append({
                    "type": "spot_end",
                    "round": int(round_number),
                    "tick": tick,

                    "spotter_steamid":
                        spotter_steamid,

                    "spotter_name":
                        name_by_steamid.get(
                            spotter_steamid
                        ),

                    "target_steamid":
                        target_steamid,

                    "target_name":
                        str(row["name"]),

                    "target_team": (
                        int(row["team_num"])
                        if not pd.isna(
                            row["team_num"]
                        )
                        else None
                    ),

                    "last_seen_tick": (
                        last_seen["tick"]
                        if last_seen
                        else None
                    ),

                    "last_seen_position": (
                        last_seen["position"]
                        if last_seen
                        else None
                    ),
                })

            previous_spotters = current_spotters

    events.sort(
        key=lambda event: (
            event["tick"],
            event["type"],
        )
    )

    return events

def enemy_team(team):
    if team == 2:
        return 3

    if team == 3:
        return 2

    return None

def build_team_observations(
    position_df,
    round_intervals,
):
    df = attach_live_rounds(
        position_df,
        round_intervals,
    )

    df = df[
        df["steamid"].notna()
        & df["tick"].notna()
    ].copy()

    observations = []

    for _, row in df.iterrows():
        spotters = normalize_spotters(
            row["approximate_spotted_by"]
        )

        if not spotters:
            continue

        if pd.isna(row["team_num"]):
            continue

        target_team = int(
            row["team_num"]
        )

        observer_team = enemy_team(
            target_team
        )

        if observer_team is None:
            continue

        target_steamid = normalize_steamid(
            row["steamid"]
        )

        if target_steamid is None:
            continue

        spotters.discard(
            target_steamid
        )

        if not spotters:
            continue

        observations.append({
            "round": int(
                row["round"]
            ),

            "tick": int(
                row["tick"]
            ),

            "observer_team":
                observer_team,

            "target_steamid":
                target_steamid,

            "target_name":
                str(row["name"]),

            "target_team":
                target_team,

            "position": {
                "x": normalize_number(
                    row["X"]
                ),
                "y": normalize_number(
                    row["Y"]
                ),
                "z": normalize_number(
                    row["Z"]
                ),
            },

            "spotters":
                sorted(spotters),
        })

    observations.sort(
        key=lambda item: (
            item["round"],
            item["tick"],
            item["target_steamid"],
        )
    )

    return observations


def build_team_spot_windows(spot_events):
    events = sorted(
        spot_events,
        key=lambda event: (
            event["round"],
            event["tick"],
            0 if event["type"] == "spot_start" else 1,
        )
    )

    states = {}
    windows = []

    for event in events:
        target_team = event.get(
            "target_team"
        )

        observer_team = enemy_team(
            target_team
        )

        if observer_team is None:
            continue

        key = (
            event["round"],
            observer_team,
            event["target_steamid"],
        )

        if key not in states:
            states[key] = {
                "active_spotters": set(),
                "start_tick": None,
                "last_seen_tick": None,
                "last_seen_position": None,
                "target_name":
                    event["target_name"],
                "target_team":
                    target_team,
            }

        state = states[key]

        spotter = event[
            "spotter_steamid"
        ]

        if event["type"] == "spot_start":
            if not state["active_spotters"]:
                state["start_tick"] = (
                    event["tick"]
                )

            state[
                "active_spotters"
            ].add(spotter)

            state["last_seen_tick"] = (
                event["tick"]
            )

            state["last_seen_position"] = (
                event["target_position"]
            )

        elif event["type"] == "spot_end":
            state[
                "active_spotters"
            ].discard(spotter)

            if (
                event.get(
                    "last_seen_tick"
                )
                is not None
            ):
                state["last_seen_tick"] = (
                    event["last_seen_tick"]
                )

                state[
                    "last_seen_position"
                ] = event[
                    "last_seen_position"
                ]

            if (
                not state["active_spotters"]
                and state["start_tick"]
                is not None
            ):
                windows.append({
                    "round":
                        event["round"],

                    "observer_team":
                        observer_team,

                    "target_steamid":
                        event[
                            "target_steamid"
                        ],

                    "target_name":
                        state[
                            "target_name"
                        ],

                    "start_tick":
                        state[
                            "start_tick"
                        ],

                    "end_tick":
                        event["tick"],

                    "last_seen_tick":
                        state[
                            "last_seen_tick"
                        ],

                    "last_seen_position":
                        state[
                            "last_seen_position"
                        ],
                })

                state["start_tick"] = None
                state["last_seen_tick"] = None
                state[
                    "last_seen_position"
                ] = None

    return windows

def get_team_knowledge_at_tick(
    observations,
    round_number,
    observer_team,
    tick,
):
    relevant = [
        observation
        for observation in observations
        if (
            observation["round"]
            == round_number

            and observation[
                "observer_team"
            ]
            == observer_team

            and observation["tick"]
            <= tick
        )
    ]

    latest_by_target = {}

    for observation in relevant:
        target_steamid = observation[
            "target_steamid"
        ]

        previous = latest_by_target.get(
            target_steamid
        )

        if (
            previous is None
            or observation["tick"]
            > previous["tick"]
        ):
            latest_by_target[
                target_steamid
            ] = observation

    knowledge = []

    for observation in (
        latest_by_target.values()
    ):
        age_ticks = (
            tick
            - observation["tick"]
        )

        status = (
            "currently_spotted"
            if age_ticks == 0
            else "last_known"
        )

        knowledge.append({
            "target_steamid":
                observation[
                    "target_steamid"
                ],

            "target_name":
                observation[
                    "target_name"
                ],

            "status":
                status,

            "last_seen_tick":
                observation["tick"],

            "age_ticks":
                int(age_ticks),

            "age_seconds":
                round(
                    age_ticks / 64,
                    2,
                ),

            "last_seen_position":
                observation[
                    "position"
                ],

            "last_seen_by":
                observation[
                    "spotters"
                ],
        })

    knowledge.sort(
        key=lambda item: (
            item["age_ticks"],
            item["target_name"],
        )
    )

    return knowledge

def get_team_visual_state_at_tick(
    observations,
    team_spot_windows,
    round_number,
    observer_team,
    tick,
):
    knowledge = get_team_knowledge_at_tick(
        observations,
        round_number,
        observer_team,
        tick,
    )

    active_targets = set()

    for window in team_spot_windows:
        if (
            window["round"] == round_number
            and window["observer_team"] == observer_team
            and window["start_tick"] <= tick < window["end_tick"]
        ):
            active_targets.add(
                window["target_steamid"]
            )

    for item in knowledge:
        if item["target_steamid"] in active_targets:
            item["status"] = "currently_spotted"
            item["age_ticks"] = 0
            item["age_seconds"] = 0.0
        else:
            item["status"] = "last_known"

    return knowledge