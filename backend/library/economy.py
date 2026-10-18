
def get_field(player, group, field):
    data = player.get(group, {})

    if not isinstance(data, dict):
        return None

    return data.get(field)


def build_team_economy(players, team_number):
    team_players = [
        player
        for player in players
        if player.get("team") == team_number
    ]

    total_balance = 0
    total_equipment = 0

    balance_known = 0
    equipment_known = 0
    alive_count = 0

    for player in team_players:
        alive = get_field(player, "status", "is_alive")

        if alive is True:
            alive_count += 1

        balance = get_field(player, "economy", "balance")

        if balance is not None:
            total_balance += balance
            balance_known += 1

        equipment = get_field(
            player,
            "economy",
            "current_equip_value",
        )

        if equipment is not None:
            total_equipment += equipment
            equipment_known += 1

    return {
        "team": team_number,
        "player_count": len(team_players),
        "alive_count": alive_count,

        "total_balance": (
            total_balance
            if balance_known == len(team_players)
            and team_players
            else None
        ),

        "total_equipment_value": (
            total_equipment
            if equipment_known == len(team_players)
            and team_players
            else None
        ),

        "players_with_balance": balance_known,
        "players_with_equipment_value": equipment_known,
    }


def build_round_economy(players):
    return {
        "T": build_team_economy(players, 2),
        "CT": build_team_economy(players, 3),
    }


WEAPON_CATEGORIES = {
    "ak-47": "rifle",
    "m4a4": "rifle",
    "m4a1-s": "rifle",
    "famas": "rifle",
    "galil ar": "rifle",
    "aug": "rifle",
    "sg 553": "rifle",

    "awp": "sniper",
    "ssg 08": "sniper",
    "scar-20": "sniper",
    "g3sg1": "sniper",

    "glock-18": "pistol",
    "usp-s": "pistol",
    "p2000": "pistol",
    "p250": "pistol",
    "five-seven": "pistol",
    "tec-9": "pistol",
    "cz75-auto": "pistol",
    "desert eagle": "pistol",
    "r8 revolver": "pistol",
    "dual berettas": "pistol",

    "mac-10": "smg",
    "mp9": "smg",
    "mp7": "smg",
    "mp5-sd": "smg",
    "ump-45": "smg",
    "p90": "smg",
    "pp-bizon": "smg",

    "nova": "shotgun",
    "xm1014": "shotgun",
    "mag-7": "shotgun",
    "sawed-off": "shotgun",

    "m249": "machine_gun",
    "negev": "machine_gun",
}

GRENADE_CATEGORIES = {
    "smoke grenade": "smoke",
    "flashbang": "flash",
    "high explosive grenade": "he",
    "he grenade": "he",
    "molotov": "molotov",
    "incendiary grenade": "incendiary",
    "decoy grenade": "decoy",
}


def build_player_loadout(player):
    inventory = player.get("inventory")

    if not isinstance(inventory, (list, tuple)):
        return {
            "status": "unknown",
            "primary": None,
            "secondary": None,
            "knife": None,
            "grenades": None,
            "has_bomb": None,
            "armor": player.get("status", {}).get("armor"),
            "has_helmet": player.get("status", {}).get("has_helmet"),
            "has_defuser": player.get("status", {}).get("has_defuser"),
        }

    primary = None
    secondary = None
    knife = None
    grenades = {
        "smoke": 0,
        "flash": 0,
        "he": 0,
        "molotov": 0,
        "incendiary": 0,
        "decoy": 0,
    }
    has_bomb = False
    unclassified = []

    for item in inventory:
        if not isinstance(item, str):
            unclassified.append(item)
            continue

        name = item.strip()
        normalized = name.lower()

        category = WEAPON_CATEGORIES.get(normalized)

        if category == "pistol":
            secondary = name

        elif category is not None:
            primary = name

        elif normalized in GRENADE_CATEGORIES:
            grenade_type = GRENADE_CATEGORIES[normalized]
            grenades[grenade_type] += 1

        elif "knife" in normalized or normalized == "bayonet":
            knife = name

        elif normalized == "c4 explosive":
            has_bomb = True

        else:
            unclassified.append(name)

    status = player.get("status", {})

    return {
        "status": "parsed",
        "primary": primary,
        "secondary": secondary,
        "knife": knife,
        "grenades": grenades,
        "has_bomb": has_bomb,
        "armor": status.get("armor"),
        "has_helmet": status.get("has_helmet"),
        "has_defuser": status.get("has_defuser"),
        "unclassified": unclassified,
    }


def build_team_loadout(players, team_number):
    team_players = [
        player for player in players
        if player.get("team") == team_number
    ]

    loadouts = [
        build_player_loadout(player)
        for player in team_players
    ]

    known = [
        loadout for loadout in loadouts
        if loadout["status"] == "parsed"
    ]

    return {
        "team": team_number,
        "player_count": len(team_players),
        "known_loadouts": len(known),
        "players": loadouts,
        "primary_weapons": [
            loadout["primary"]
            for loadout in known
            if loadout["primary"] is not None
        ],
        "grenades": {
            grenade: sum(
                loadout["grenades"][grenade]
                for loadout in known
            )
            for grenade in GRENADE_CATEGORIES.values()
        },
    }

