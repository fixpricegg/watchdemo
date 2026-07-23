import { getMapConfig } from "../config/maps";
import radarData from "../data/radar.json";

import PlayerHud from "./PlayerHud";
import KillFeed from "./KillFeed";

import "./Radar.css";

function Radar({ tickIndex }) {
    const mapConfig = getMapConfig(radarData.map);

    if (!mapConfig) {
        return (
            <section className="radar-section">
                <p>
                    Unsupported map: {radarData.map}
                </p>
            </section>
        );
    }

    const players = Object.entries(
        radarData.players
    ).map(([steamid, player]) => ({
        ...player,
        steamid,
    }));

    const masterTicks = (
        radarData.bomb?.states ?? []
    ).map((state) => state.tick);

    const currentTick =
        masterTicks[tickIndex] ?? null;

    function getPositionAtTick(positions, targetTick) {
        if (
            !positions?.length ||
            targetTick === null
        ) {
            return null;
        }

        let left = 0;
        let right = positions.length - 1;
        let result = null;

        while (left <= right) {
            const middle = Math.floor(
                (left + right) / 2
            );

            const position = positions[middle];

            if (position.tick <= targetTick) {
                result = position;
                left = middle + 1;
            } else {
                right = middle - 1;
            }
        }

        return result;
    }
    
    const playersWithCurrentPosition =
        players.map((player) => ({
            ...player,
            currentPosition:
                getPositionAtTick(
                    player.positions,
                    currentTick
                ),
        }));

    const bombStates =
        radarData.bomb?.states ?? [];

    let bombState = null;

    if (currentTick !== null) {
        for (const state of bombStates) {
            if (state.tick <= currentTick) {
                bombState = state;
            } else {
                break;
            }
        }
    }

    const toImageCoordinates = (x, y) => ({
        imageX:
            (x - mapConfig.posX) /
            mapConfig.scale,

        imageY:
            (mapConfig.posY - y) /
            mapConfig.scale,
    });

    const getBombStatusText = () => {
        if (!bombState) {
            return "Bomb unavailable";
        }

        switch (bombState.state) {
            case "carried":
                return bombState.carrier_name
                    ? `C4 · ${bombState.carrier_name}`
                    : "C4 carried";

            case "dropped":
                return "C4 dropped";

            case "planted":
                return bombState.site
                    ? `Bomb planted · Site ${bombState.site}`
                    : "Bomb planted";

            case "defused":
                return "Bomb defused";

            case "exploded":
                return "Bomb exploded";

            default:
                return "Bomb unavailable";
        }
    };

    const kills = radarData.kills ?? [];

    const grenadeTracks =
        radarData.grenades ?? [];

    const activeGrenades = grenadeTracks
        .map((grenade) => {
            if (currentTick === null) {
                return null;
            }

            const isProjectile =
                currentTick >=
                    grenade.start_tick &&
                currentTick <=
                    grenade.projectile_end_tick;

            const isEffect =
                grenade.has_effect !== false &&
                currentTick >=
                    grenade.effect_start_tick &&
                currentTick <=
                    grenade.effect_end_tick;

            if (!isProjectile && !isEffect) {
                return null;
            }

            if (isProjectile) {
                let currentPosition = null;

                for (
                    const position
                    of grenade.positions
                ) {
                    if (
                        position.tick <=
                        currentTick
                    ) {
                        currentPosition =
                            position;
                    } else {
                        break;
                    }
                }

                if (!currentPosition) {
                    return null;
                }

                return {
                    ...grenade,
                    phase: "projectile",
                    currentPosition,
                };
            }

            return {
                ...grenade,
                phase: "effect",
                currentPosition: {
                    x: grenade.effect_x,
                    y: grenade.effect_y,
                    z: grenade.effect_z,
                },
            };
        })
        .filter(Boolean);

    const drawableBombStates = [
        "carried",
        "dropped",
        "planted",
        "defused",
        "exploded",
    ];

    const canDrawBomb =
        drawableBombStates.includes(
            bombState?.state
        ) &&
        bombState.x !== null &&
        bombState.y !== null;

    const bombCoordinates = canDrawBomb
        ? toImageCoordinates(
              bombState.x,
              bombState.y
          )
        : null;

    return (
        <section className="radar-section">
            <div className="radar-header">
                <h2>Radar</h2>

                <div
                    className={`bomb-status bomb-status-${
                        bombState?.state ??
                        "unavailable"
                    }`}
                >
                    {getBombStatusText()}
                </div>
            </div>

            <div className="radar-layout">
                <PlayerHud
                    players={
                        playersWithCurrentPosition
                    }
                    currentTick={currentTick}
                    team="CT"
                />

                <div className="radar-container">
                    <img
                        src={mapConfig.image}
                        alt={`${mapConfig.name} radar`}
                        className="radar-map"
                    />

                    <KillFeed
                        kills={kills}
                        players={playersWithCurrentPosition}
                        currentTick={currentTick}
                    />

                    {playersWithCurrentPosition.map(
                        (player, index) => {
                            const pos =
                                player.currentPosition;

                            if (!pos) {
                                return null;
                            }

                            const {
                                imageX,
                                imageY,
                            } =
                                toImageCoordinates(
                                    pos.x,
                                    pos.y
                                );

                            const team =
                                pos.team ||
                                player.team;

                            const aliveClass =
                                pos.is_alive
                                    ? "alive-dot"
                                    : "dead-dot";

                            return (
                                <div
                                    key={index}
                                    className={`player-dot ${aliveClass} ${
                                        team ===
                                        "CT"
                                            ? "ct-dot"
                                            : "t-dot"
                                    }`}
                                    title={`${
                                        player.name
                                    } · ${team} · ${
                                        pos.is_alive
                                            ? "Alive"
                                            : "Dead"
                                    }`}
                                    style={{
                                        left: `${imageX}px`,
                                        top: `${imageY}px`,
                                        "--view-yaw": `${
                                            -(
                                                pos.yaw ??
                                                0
                                            )
                                        }deg`,
                                    }}
                                >
                                    <span className="player-name">
                                        {
                                            player.name
                                        }
                                    </span>
                                </div>
                            );
                        }
                    )}

                    {activeGrenades.map(
                        (grenade) => {
                            const {
                                imageX,
                                imageY,
                            } =
                                toImageCoordinates(
                                    grenade
                                        .currentPosition
                                        .x,
                                    grenade
                                        .currentPosition
                                        .y
                                );

                            return (
                                <div
                                    key={`grenade-${grenade.track_id}`}
                                    className={[
                                        "grenade-marker",
                                        `grenade-marker-${grenade.type}`,
                                        `grenade-marker-${grenade.phase}`,
                                        grenade.phase ===
                                        "effect"
                                            ? "grenade-effect"
                                            : "grenade-projectile",
                                    ].join(" ")}
                                    title={`${
                                        grenade.type
                                    } · ${
                                        grenade.thrower_name ??
                                        "Unknown"
                                    }`}
                                    style={{
                                        left: `${imageX}px`,
                                        top: `${imageY}px`,
                                    }}
                                >
                                    {grenade.phase ===
                                        "projectile" && (
                                        <>
                                            {grenade.type ===
                                                "smoke" &&
                                                "S"}

                                            {grenade.type ===
                                                "flash" &&
                                                "F"}

                                            {grenade.type ===
                                                "he" &&
                                                "HE"}

                                            {grenade.type ===
                                                "molotov" &&
                                                "M"}

                                            {grenade.type ===
                                                "decoy" &&
                                                "D"}
                                        </>
                                    )}

                                    {grenade.phase ===
                                        "effect" && (
                                        <>
                                            {grenade.type ===
                                                "smoke" && (
                                                <span className="grenade-effect-label">
                                                    SMOKE
                                                </span>
                                            )}

                                            {grenade.type ===
                                                "molotov" && (
                                                <span className="grenade-effect-label">
                                                    FIRE
                                                </span>
                                            )}

                                            {grenade.type ===
                                                "decoy" &&
                                                "D"}
                                        </>
                                    )}
                                </div>
                            );
                        }
                    )}

                    {canDrawBomb && (
                        <div
                            className={`bomb-marker bomb-marker-${bombState.state}`}
                            title={`${getBombStatusText()} · ${
                                bombState.position_accuracy ===
                                "carrier_position"
                                    ? "Exact position"
                                    : "Approximate position"
                            }`}
                            style={{
                                left: `${bombCoordinates.imageX}px`,
                                top: `${bombCoordinates.imageY}px`,
                            }}
                        >
                            C4
                        </div>
                    )}
                </div>

                <PlayerHud
                    players={
                        playersWithCurrentPosition
                    }
                    currentTick={currentTick}
                    team="T"
                />
            </div>
        </section>
    );
}

export default Radar;