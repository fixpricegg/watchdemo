
SPECIAL_ONLY = {
    "playerclip",
    "npcclip",
    "csgo_grenadeclip",
    "sky",
    "blocksound",
    "ladder",
}

UNCERTAIN = {
    "glass",
    "chainlink",
    "metalgrate",
    "metalrailing",
}


def classify_collision_group(group):
    flags = set(group.get("interact_as") or [])
    material = str(
        group.get("surface_property") or ""
    ).lower()

    if "passbullets" in flags:
        return "special_passbullets"

    if "blocklos" in flags:
        return "explicit_los_blocker"

    if flags & SPECIAL_ONLY:
        return "special_collision"

    if flags or material in UNCERTAIN:
        return "requires_review"

    return "solid_candidate"
