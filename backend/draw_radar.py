from PIL import Image, ImageDraw
import radar

def draw_radar_frame(
        map_image_path,
        positions,
        map_name,
        tick
):

    image = Image.open(map_image_path)

    draw = ImageDraw.Draw(image)

    for steamid, pos in positions.items():

        x = pos["image_x"]
        y = pos["image_y"]

        radius = 8

        if pos["is_alive"]:
            color = "blue"
        else:
            color = "gray"

        draw.ellipse(
            (
                x - radius,
                y - radius,
                x + radius,
                y + radius
            ),
            fill=color
        )

    image.save(f"frame_{tick}.png")

def build_frame(
        radar_match,
        tick
):

    all_positions = radar.get_all_players_positions(
        radar_match,
        tick
    )

    map_name = radar_match["map"]

    for steamid, pos in all_positions.items():

        image_x, image_y = radar.normalize_coordinates(
            pos["x"],
            pos["y"],
            map_name
        )

        pos["image_x"] = image_x
        pos["image_y"] = image_y

    draw_radar_frame(
        f"maps/{map_name}_radar.png",
        all_positions,
        map_name,
        tick
    )