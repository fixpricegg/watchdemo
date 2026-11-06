import json
import math
from pathlib import Path


def point_in_polygon(x, y, polygon):
    inside = False
    j = len(polygon) - 1

    for i in range(len(polygon)):
        xi = polygon[i]["x"]
        yi = polygon[i]["y"]

        xj = polygon[j]["x"]
        yj = polygon[j]["y"]

        intersects = (
            (yi > y) != (yj > y)
            and x
            < (
                (xj - xi)
                * (y - yi)
                / ((yj - yi) or 1e-9)
                + xi
            )
        )

        if intersects:
            inside = not inside

        j = i

    return inside


def distance_to_z_range(z, min_z, max_z):
    if min_z <= z <= max_z:
        return 0.0

    if z < min_z:
        return min_z - z

    return z - max_z


class MapGeometry:
    def __init__(self, nav_json_path):
        nav_json_path = Path(nav_json_path)

        with nav_json_path.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        self.version = data.get("version")
        self.sub_version = data.get("subVersion")

        self.areas = {}

        for area in data["areas"]:
            corners = area["corners"]

            xs = [
                corner["x"]
                for corner in corners
            ]

            ys = [
                corner["y"]
                for corner in corners
            ]

            zs = [
                corner["z"]
                for corner in corners
            ]

            area_id = int(area["id"])

            self.areas[area_id] = {
                "id": area_id,
                "hull": area.get("hull"),

                "corners": corners,

                "min_x": min(xs),
                "max_x": max(xs),

                "min_y": min(ys),
                "max_y": max(ys),

                "min_z": min(zs),
                "max_z": max(zs),

                "center": {
                    "x": sum(xs) / len(xs),
                    "y": sum(ys) / len(ys),
                    "z": sum(zs) / len(zs),
                },

                "connections": [
                    int(connection["areaId"])
                    for connection
                    in area.get(
                        "connections",
                        []
                    )
                ],
            }

        self.ladders = data.get(
            "ladders",
            []
        )

    def find_area(
        self,
        x,
        y,
        z,
        max_vertical_distance=96,
    ):
        candidates = []

        for area in self.areas.values():
            if not (
                area["min_x"] <= x <= area["max_x"]
                and area["min_y"] <= y <= area["max_y"]
            ):
                continue

            if not point_in_polygon(
                x,
                y,
                area["corners"],
            ):
                continue

            vertical_distance = (
                distance_to_z_range(
                    z,
                    area["min_z"],
                    area["max_z"],
                )
            )

            if (
                vertical_distance
                > max_vertical_distance
            ):
                continue

            candidates.append(
                (
                    vertical_distance,
                    area,
                )
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: item[0]
        )

        return candidates[0][1]

    def get_neighbors(
        self,
        area_id,
    ):
        area = self.areas.get(
            int(area_id)
        )

        if area is None:
            return []

        result = []

        for neighbor_id in area[
            "connections"
        ]:
            neighbor = self.areas.get(
                neighbor_id
            )

            if neighbor is not None:
                result.append(neighbor)

        return result

    def shortest_path(
            self,
            start_area_id,
            end_area_id,
    ):
        start_area_id = int(start_area_id)
        end_area_id = int(end_area_id)

        if start_area_id not in self.areas:
            return None

        if end_area_id not in self.areas:
            return None

        if start_area_id == end_area_id:
            return [start_area_id]

        distances = {
            start_area_id: 0.0
        }

        previous = {}

        queue = [
            (0.0, start_area_id)
        ]

        while queue:
            queue.sort(
                key=lambda item: item[0]
            )

            current_distance, current_id = (
                queue.pop(0)
            )

            if (
                    current_distance
                    > distances[current_id]
            ):
                continue

            if current_id == end_area_id:
                break

            current_area = self.areas[
                current_id
            ]

            for neighbor_id in current_area[
                "connections"
            ]:
                neighbor = self.areas.get(
                    neighbor_id
                )

                if neighbor is None:
                    continue

                step_distance = (
                    self.area_distance(
                        current_area,
                        neighbor,
                    )
                )

                new_distance = (
                        current_distance
                        + step_distance
                )

                old_distance = distances.get(
                    neighbor_id
                )

                if (
                        old_distance is None
                        or new_distance
                        < old_distance
                ):
                    distances[
                        neighbor_id
                    ] = new_distance

                    previous[
                        neighbor_id
                    ] = current_id

                    queue.append(
                        (
                            new_distance,
                            neighbor_id,
                        )
                    )

        if end_area_id not in distances:
            return None

        path = [
            end_area_id
        ]

        current_id = end_area_id

        while current_id != start_area_id:
            current_id = previous.get(
                current_id
            )

            if current_id is None:
                return None

            path.append(
                current_id
            )

        path.reverse()

        return path

    def nearest_area(
        self,
        x,
        y,
        z,
    ):
        best_area = None
        best_distance = None

        for area in self.areas.values():
            center = area["center"]

            distance = math.sqrt(
                (center["x"] - x) ** 2
                + (center["y"] - y) ** 2
                + (center["z"] - z) ** 2
            )

            if (
                best_distance is None
                or distance < best_distance
            ):
                best_distance = distance
                best_area = area

        return best_area, best_distance

    def area_distance(
            self,
            area_a,
            area_b,
    ):
        center_a = area_a["center"]
        center_b = area_b["center"]

        return math.sqrt(
            (center_a["x"] - center_b["x"]) ** 2
            + (center_a["y"] - center_b["y"]) ** 2
            + (center_a["z"] - center_b["z"]) ** 2
        )

    def reachable_areas(
            self,
            start_area_id,
            max_distance,
    ):
        start_area_id = int(start_area_id)

        if start_area_id not in self.areas:
            return {}

        distances = {
            start_area_id: 0.0
        }

        queue = [
            (0.0, start_area_id)
        ]

        while queue:
            queue.sort(
                key=lambda item: item[0]
            )

            current_distance, current_id = queue.pop(0)

            if current_distance > distances[current_id]:
                continue

            current_area = self.areas[current_id]

            for neighbor_id in current_area["connections"]:
                neighbor = self.areas.get(neighbor_id)

                if neighbor is None:
                    continue

                step_distance = self.area_distance(
                    current_area,
                    neighbor,
                )

                new_distance = (
                        current_distance
                        + step_distance
                )

                if new_distance > max_distance:
                    continue

                old_distance = distances.get(
                    neighbor_id
                )

                if (
                        old_distance is None
                        or new_distance < old_distance
                ):
                    distances[neighbor_id] = (
                        new_distance
                    )

                    queue.append(
                        (
                            new_distance,
                            neighbor_id,
                        )
                    )

        return distances

    def reachable_areas_by_time(
            self,
            start_area_id,
            seconds,
            max_speed,
    ):
        max_distance = seconds * max_speed

        return self.reachable_areas(
            start_area_id,
            max_distance,
        )

    def possible_region_from_last_seen(
            self,
            last_seen_position,
            age_seconds,
            max_speed,
    ):
        start_area = self.find_area(
            last_seen_position["x"],
            last_seen_position["y"],
            last_seen_position["z"],
        )

        if start_area is None:
            return None

        reachable = self.reachable_areas_by_time(
            start_area["id"],
            seconds=age_seconds,
            max_speed=max_speed,
        )

        return {
            "start_area_id": start_area["id"],
            "age_seconds": age_seconds,
            "max_speed": max_speed,
            "reachable_area_ids": list(
                reachable.keys()
            ),
            "distances": reachable,
        }