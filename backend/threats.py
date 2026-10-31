import heapq
import math


DEFAULT_MAX_ENEMY_SPEED = 250.0
DEFAULT_MAX_NAV_DISTANCE = 1500.0



def _nav_distances_from(
    geometry,
    start_area_id,
    max_distance=DEFAULT_MAX_NAV_DISTANCE,
):
    """
    Считает nav-distance от одной area до соседних areas.

    Используем существующие connections navmesh.

    Возвращает:
        {
            area_id: distance,
            ...
        }
    """

    if start_area_id is None:
        return {}

    start_area_id = int(start_area_id)

    start_area = geometry.areas.get(
        start_area_id
    )

    if start_area is None:
        return {}

    distances = {
        start_area_id: 0.0
    }

    queue = [
        (0.0, start_area_id)
    ]

    while queue:
        current_distance, current_area_id = (
            heapq.heappop(queue)
        )

        if current_distance > distances.get(
            current_area_id,
            math.inf,
        ):
            continue

        if current_distance > max_distance:
            continue

        current_area = geometry.areas.get(
            current_area_id
        )

        if current_area is None:
            continue

        for neighbor in geometry.get_neighbors(
            current_area_id
        ):
            neighbor_id = int(
                neighbor["id"]
            )

            edge_distance = geometry.area_distance(
                current_area,
                neighbor,
            )

            new_distance = (
                current_distance
                + float(edge_distance)
            )

            if new_distance > max_distance:
                continue

            old_distance = distances.get(
                neighbor_id,
                math.inf,
            )

            if new_distance >= old_distance:
                continue

            distances[neighbor_id] = new_distance

            heapq.heappush(
                queue,
                (
                    new_distance,
                    neighbor_id,
                ),
            )

    return distances


def build_movement_threats(
    geometry,
    player_position,
    enemies,
    max_enemy_speed=DEFAULT_MAX_ENEMY_SPEED,
    max_nav_distance=DEFAULT_MAX_NAV_DISTANCE,
):
    """
    Первый threat model.

    ВАЖНО:
    это НЕ line-of-sight модель.

    Она отвечает только на вопрос:
    насколько близко враг МОГ физически оказаться
    к игроку по navmesh с учётом last-known info.
    """

    player_area = geometry.find_area(
        player_position["x"],
        player_position["y"],
        player_position["z"],
    )

    if player_area is None:
        return {
            "player_area_id": None,
            "threats": [],
        }

    if isinstance(player_area, dict):
        player_area_id = int(player_area["id"])
    else:
        player_area_id = int(player_area)

    # Один Dijkstra от игрока.
    # Не запускаем поиск отдельно для каждой enemy area.
    distances_from_player = _nav_distances_from(
        geometry,
        player_area_id,
        max_distance=max_nav_distance,
    )

    results = []

    for enemy in enemies:
        last_seen_position = enemy.get(
            "last_seen_position"
        )

        if not last_seen_position:
            continue

        age_seconds = float(
            enemy.get(
                "age_seconds",
                0.0,
            )
            or 0.0
        )

        freshness_score = float(
            enemy.get(
                "freshness_score",
                0.0,
            )
            or 0.0
        )

        region = (
            geometry.possible_region_from_last_seen(
                last_seen_position,
                age_seconds,
                max_speed=max_enemy_speed,
            )
        )

        if not region:
            continue

        possible_area_ids = [
            int(area_id)
            for area_id in region.get(
                "reachable_area_ids",
                [],
            )
        ]

        if not possible_area_ids:
            continue

        closest_area_id = None
        min_nav_distance = math.inf

        for area_id in possible_area_ids:
            nav_distance = (
                distances_from_player.get(
                    area_id
                )
            )

            if nav_distance is None:
                continue

            if nav_distance < min_nav_distance:
                min_nav_distance = nav_distance
                closest_area_id = area_id

        if math.isinf(min_nav_distance):
            contact_seconds = None

        else:
            contact_seconds = (
                    min_nav_distance
                    / max_enemy_speed
            )

        results.append({
            "enemy_name": enemy.get(
                "target_name"
            ),
            "enemy_steamid": enemy.get(
                "target_steamid"
            ),

            "status": enemy.get(
                "status"
            ),

            "age_seconds": age_seconds,
            "freshness": enemy.get(
                "freshness"
            ),
            "last_seen_position":
                last_seen_position,


            "possible_area_count": len(
                possible_area_ids
            ),

            "possible_area_ids": possible_area_ids,

            "player_area_id": player_area_id,

            "player_area_possible": (
                player_area_id
                in possible_area_ids
            ),

            "closest_possible_area_id":
                closest_area_id,

            "min_nav_distance": (
                round(
                    min_nav_distance,
                    1,
                )
                if not math.isinf(
                    min_nav_distance
                )
                else None
            ),

            "estimated_contact_seconds": (
                round(
                    contact_seconds,
                    2,
                )
                if contact_seconds
                is not None
                else None
            ),



        })

    results.sort(
        key=lambda item: (
            item["min_nav_distance"]
            if item["min_nav_distance"] is not None
            else math.inf
        )
    )

    return {
        "player_area_id": player_area_id,
        "threats": results,
    }