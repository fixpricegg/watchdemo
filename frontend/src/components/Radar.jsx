import { useRef } from "react";

import { getMapConfig } from "../config/maps";

import PlayerHud from "./PlayerHud";
import KillFeed from "./KillFeed";

import "./Radar.css";

function Radar({ tickIndex, radarData }) {
    const playerFloorState = useRef({});

    if (!radarData) {
        return null;
    }

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
    
    
    const isNuke =
    radarData.map === "de_nuke" &&
    Boolean(mapConfig.lowerImage);

    const NUKE_ENTER_LOWER_Z = -560;
    const NUKE_EXIT_LOWER_Z = -430;

    const getNukeFloor = (z) => {
        if (
            isNuke &&
            z !== null &&
            z !== undefined &&
            z <= NUKE_ENTER_LOWER_Z
        ) {
            return "lower";
        }

        return "upper";
    };

    const playersWithFloor =
        playersWithCurrentPosition.map((player) => {
            const pos = player.currentPosition;

            let floor = "upper";

            if (
                isNuke &&
                pos?.z !== null &&
                pos?.z !== undefined
            ) {
                const previousFloor =
                    playerFloorState.current[
                        player.steamid
                    ] ?? "upper";

                if (previousFloor === "lower") {
                    floor =
                        pos.z < NUKE_EXIT_LOWER_Z
                            ? "lower"
                            : "upper";
                } else {
                    floor =
                        pos.z <= NUKE_ENTER_LOWER_Z
                            ? "lower"
                            : "upper";
                }

                playerFloorState.current[
                    player.steamid
                ] = floor;
            }

            return {
                ...player,
                floor,
            };
        });

    const alivePlayers =
        playersWithFloor.filter(
            (player) =>
                player.currentPosition?.is_alive
        );

    const aliveLowerPlayers =
        alivePlayers.filter(
            (player) =>
                player.floor === "lower"
        );

    const mainFloor = "upper";
    const insetFloor = "lower";

    const mainMapImage = mapConfig.image;
    const insetMapImage = mapConfig.lowerImage;

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

        const toFloorCoordinates = (
        x,
        y,
        floor = "upper"
    ) => {
        if (
            isNuke &&
            floor === "lower"
        ) {
            return {
                imageX:
                    (x - mapConfig.lowerPosX) /
                    mapConfig.lowerScaleX,

                imageY:
                    (mapConfig.lowerPosY - y) /
                    mapConfig.lowerScaleY,

                imageSize:
                    mapConfig.lowerImageSize ??
                    1254,
            };
        }

        return {
            imageX:
                (x - mapConfig.posX) /
                mapConfig.scale,

            imageY:
                (mapConfig.posY - y) /
                mapConfig.scale,

            imageSize: 1024,
        };
    };

    const toFloorPercent = (
        x,
        y,
        floor
    ) => {
        const coordinates =
            toFloorCoordinates(
                x,
                y,
                floor
            );

        return {
            left:
                (
                    coordinates.imageX /
                    coordinates.imageSize
                ) * 100,

            top:
                (
                    coordinates.imageY /
                    coordinates.imageSize
                ) * 100,
        };
    };

    const getInsetTransform = (floor) => {
    if (floor === "lower") {
        return {
            scale: 0.47,
            offsetX: -94,
            offsetY: -70,
        };
    }

    return {
        scale: 340 / 1024,
        offsetX: 0,
        offsetY: 0,
    };
};

    const toInsetCoordinates = (
        x,
        y,
        floor
    ) => {
        const coordinates =
            toFloorCoordinates(
                x,
                y,
                floor
            );

        const transform =
            getInsetTransform(floor);

        return {
            left:
                coordinates.imageX *
                    transform.scale +
                transform.offsetX,

            top:
                coordinates.imageY *
                    transform.scale +
                transform.offsetY,
        };
    };

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
    
    const grenadesWithFloor =
        activeGrenades.map((grenade) => ({
            ...grenade,
            floor: getNukeFloor(
                grenade.currentPosition?.z
            ),
        }));

    const lowerGrenades =
        grenadesWithFloor.filter(
            (grenade) =>
                grenade.floor === "lower"
        );

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

    let bombFloor = "upper";

    if (isNuke && bombState) {
        const carrier =
            playersWithFloor.find(
                (player) =>
                    player.name ===
                    bombState.carrier_name
            );

        if (
            bombState.state === "carried" &&
            carrier
        ) {
            bombFloor = carrier.floor;
        } else {
            bombFloor =
                getNukeFloor(bombState.z);
        }
    }

    const showInset =
        isNuke &&
        (
            aliveLowerPlayers.length > 0 ||
            (
                canDrawBomb &&
                bombFloor === "lower"
            ) ||
            lowerGrenades.length > 0
        );
    
    const insetTransform =
        getInsetTransform(insetFloor);

    const insetImageSize =
        insetFloor === "lower"
            ? (mapConfig.lowerImageSize ?? 1254)
            : 1024;

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
                        src={mainMapImage}
                        alt={`${mapConfig.name} radar`}
                        className="radar-map"
                    />

                    {showInset && (
                        <div className="nuke-lower-inset">
                            <div className="nuke-lower-window">
                                <img
                                    src={insetMapImage}
                                    alt={`Nuke ${insetFloor} radar`}
                                    className="nuke-lower-map"
                                    style={{
                                        width: `${
                                            insetImageSize *
                                            insetTransform.scale
                                        }px`,

                                        height: `${
                                            insetImageSize *
                                            insetTransform.scale
                                        }px`,

                                        left: `${insetTransform.offsetX}px`,
                                        top: `${insetTransform.offsetY}px`,
                                    }}
                                />

                                {playersWithFloor.map(
                                    (player, index) => {
                                        const pos =
                                            player.currentPosition;

                                        if (
                                            !pos ||
                                            player.floor !==
                                                insetFloor
                                        ) {
                                            return null;
                                        }

                                        const team =
                                            pos.team ||
                                            player.team;

                                        const aliveClass =
                                            pos.is_alive
                                                ? "alive-dot"
                                                : "dead-dot";

                                        const {
                                            left,
                                            top,
                                        } =
                                            toInsetCoordinates(
                                                pos.x,
                                                pos.y,
                                                insetFloor
                                            );
                     
                                        return (
                                            <div
                                                key={`inset-${player.steamid}`}
                                                className={`player-dot player-dot-inset ${aliveClass} ${
                                                    team === "CT"
                                                        ? "ct-dot"
                                                        : "t-dot"
                                                }`}
                                                style={{
                                                    left: `${left}px`,
                                                    top: `${top}px`,

                                                    "--view-yaw": `${
                                                        -(pos.yaw ?? 0)
                                                    }deg`,
                                                }}
                                            >
                                                <span className="player-name">
                                                    {player.name}
                                                </span>
                                            </div>
                                        );
                                    }
                                )}

                                {lowerGrenades.map((grenade) => {
                                    const {
                                        left,
                                        top,
                                    } =
                                        toInsetCoordinates(
                                            grenade.currentPosition.x,
                                            grenade.currentPosition.y,
                                            "lower"
                                        );

                                    return (
                                        <div
                                            key={`lower-grenade-${grenade.track_id}`}
                                            className={[
                                                "grenade-marker",
                                                `grenade-marker-${grenade.type}`,
                                                `grenade-marker-${grenade.phase}`,
                                                grenade.phase === "effect"
                                                    ? "grenade-effect"
                                                    : "grenade-projectile",
                                            ].join(" ")}
                                            style={{
                                                left: `${left}px`,
                                                top: `${top}px`,
                                            }}
                                        >
                                            {grenade.phase === "projectile" && (
                                                <>
                                                    {grenade.type === "smoke" && "S"}
                                                    {grenade.type === "flash" && "F"}
                                                    {grenade.type === "he" && "HE"}
                                                    {grenade.type === "molotov" && "M"}
                                                    {grenade.type === "decoy" && "D"}
                                                </>
                                            )}

                                            {grenade.phase === "effect" && (
                                                <>
                                                    {grenade.type === "smoke" && (
                                                        <span className="grenade-effect-label">
                                                            SMOKE
                                                        </span>
                                                    )}

                                                    {grenade.type === "molotov" && (
                                                        <span className="grenade-effect-label">
                                                            FIRE
                                                        </span>
                                                    )}

                                                    {grenade.type === "decoy" && "D"}
                                                </>
                                            )}
                                        </div>
                                    );
                                })}

                                {canDrawBomb &&
                                    bombFloor === insetFloor &&
                                    (() => {
                                        const coordinates =
                                            toInsetCoordinates(
                                                bombState.x,
                                                bombState.y,
                                                insetFloor
                                            );

                                        return (
                                            <div
                                                className={`bomb-marker bomb-marker-${bombState.state}`}
                                                title={getBombStatusText()}
                                                style={{
                                                    left: `${coordinates.left}px`,
                                                    top: `${coordinates.top}px`,
                                                }}
                                            >
                                                C4
                                            </div>
                                        );
                                    })()}
                            </div>
                        </div>
                    )}

                    <KillFeed
                        kills={kills}
                        players={playersWithFloor}
                        currentTick={currentTick}
                    />

                    {playersWithFloor.map(
                        (player, index) => {
                            const pos =
                                player.currentPosition;

                            if (!pos) {
                                return null;
                            }

                            if (
                                isNuke &&
                                player.floor !== mainFloor
                            ) {
                                return null;
                            }

                           const {
                                left,
                                top,
                            } =
                                toFloorPercent(
                                    pos.x,
                                    pos.y,
                                    mainFloor
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
                                        left: `${left}%`,
                                        top: `${top}%`,
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

                    {grenadesWithFloor
                        .filter(
                            (grenade) =>
                                !isNuke ||
                                grenade.floor === "upper"
                        )
                        .map(
                        (grenade) => {
                            const {
                                left,
                                top,
                            } =
                                toFloorPercent(
                                    grenade.currentPosition.x,
                                    grenade.currentPosition.y,
                                    "upper"
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
                                        left: `${left}%`,
                                        top: `${top}%`,
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

                    {canDrawBomb &&
                        (
                            !isNuke ||
                            bombFloor === mainFloor
                        ) && (() => {
                            const coordinates =
                                toFloorPercent(
                                    bombState.x,
                                    bombState.y,
                                    mainFloor
                                );

                            return (
                                <div
                                    className={`bomb-marker bomb-marker-${bombState.state}`}
                                    title={getBombStatusText()}
                                    style={{
                                        left: `${coordinates.left}%`,
                                        top: `${coordinates.top}%`,
                                    }}
                                >
                                    C4
                                </div>
                            );
                        })()}
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