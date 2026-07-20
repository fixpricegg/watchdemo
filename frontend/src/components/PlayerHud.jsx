import "./PlayerHud.css";

function getGrenadeShortName(item) {
    const name = String(item).toLowerCase();

    if (name.includes("smoke")) return "S";
    if (name.includes("flash")) return "F";
    if (name.includes("he grenade")) return "HE";
    if (name.includes("molotov")) return "M";
    if (name.includes("incendiary")) return "M";
    if (name.includes("decoy")) return "D";

    return null;
}

function getCurrentState(player, currentTick) {
    const states = player.states ?? [];
    let currentState = null;

    for (const state of states) {
        if (state.tick <= currentTick) {
            currentState = state;
        } else {
            break;
        }
    }

    return currentState;
}

function PlayerHud({ players, currentTick, team }) {
    if (currentTick === null) {
        return null;
    }

    const hudPlayers = players
        .map((player) => {
            const position = player.currentPosition;
            const state = getCurrentState(
                player,
                currentTick
            );

            return {
                ...player,
                currentTeam:
                    position?.team || player.team,
                isAlive:
                    position?.is_alive ?? false,
                state,
            };
        })
        .filter(
            (player) =>
                player.currentTeam === team
        );

    const renderPlayer = (player) => {
        const health =
            player.state?.health ?? 0;

        const armor =
            player.state?.armor ?? 0;

        const weapon =
            player.state?.active_weapon ??
            "Unknown";

        const grenades = (
            player.state?.inventory ?? []
        )
            .map(getGrenadeShortName)
            .filter(Boolean);

        return (
            <div
                key={player.name}
                className={[
                    "hud-player",
                    team === "CT"
                        ? "hud-player-ct"
                        : "hud-player-t",
                    player.isAlive
                        ? "hud-player-alive"
                        : "hud-player-dead",
                ].join(" ")}
            >
                <div className="hud-player-main">
                    <span className="hud-player-name">
                        {player.name}
                    </span>

                    <span className="hud-player-weapon">
                        {weapon}
                    </span>
                </div>

                <div className="hud-player-stats">
                    <span className="hud-stat">
                        HP {health}
                    </span>

                    <span className="hud-stat">
                        AR {armor}
                    </span>

                    {player.state?.has_helmet && (
                        <span
                            className="hud-helmet"
                            title="Helmet"
                        >
                            H
                        </span>
                    )}

                    <div className="hud-grenades">
                        {grenades.map(
                            (grenade, index) => (
                                <span
                                    key={`${grenade}-${index}`}
                                    className="hud-grenade"
                                >
                                    {grenade}
                                </span>
                            )
                        )}
                    </div>
                </div>
            </div>
        );
    };

    return (
        <aside
            className={`hud-team hud-team-${team.toLowerCase()}`}
        >
            <h3>{team}</h3>

            {hudPlayers.map(renderPlayer)}
        </aside>
    );
}

export default PlayerHud;