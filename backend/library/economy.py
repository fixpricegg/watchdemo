
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
