import "./KillFeed.css";

const KILL_VISIBLE_TICKS = 5 * 64;
const MAX_VISIBLE_KILLS = 5;

function getWeaponName(weapon) {
    if (!weapon) return "Unknown";

    const names = {
        ak47: "AK-47",
        m4a1: "M4A4",
        m4a1_silencer: "M4A1-S",
        awp: "AWP",
        ssg08: "SSG 08",
        deagle: "Desert Eagle",
        elite: "Dual Berettas",
        usp_silencer: "USP-S",
        hkp2000: "P2000",
        glock: "Glock-18",
        famas: "FAMAS",
        galilar: "Galil AR",
        aug: "AUG",
        sg556: "SG 553",
        mp9: "MP9",
        mac10: "MAC-10",
        ump45: "UMP-45",
        p90: "P90",
        mp7: "MP7",
        mp5sd: "MP5-SD",
        nova: "Nova",
        xm1014: "XM1014",
        mag7: "MAG-7",
        sawedoff: "Sawed-Off",
        negev: "Negev",
        m249: "M249",
        taser: "Zeus",
        hegrenade: "HE",
        inferno: "Fire",
    };

    if (weapon.startsWith("knife")) {
        return "Knife";
    }

    return names[weapon] ?? weapon;
}

function getPlayerTeamAtTick(players, steamid, tick) {
    const player = players.find(
        (item) =>
            Number(item.steamid) === Number(steamid)
    );

    if (!player) {
        return null;
    }

    let teamAtKill = null;

    for (const position of player.positions ?? []) {
        if (position.tick <= tick) {
            teamAtKill =
                position.team ??
                teamAtKill;
        } else {
            break;
        }
    }

    return teamAtKill ?? player.team ?? null;
}

function getTeamClass(team) {
    if (team === "CT") {
        return "kill-feed-ct";
    }

    if (team === "T") {
        return "kill-feed-t";
    }

    return "kill-feed-neutral";
}

function KillFeed({ kills, players, currentTick }) {
    if (currentTick === null) {
        return null;
    }

    const visibleKills = kills
        .filter((kill) => {
            const ticksSinceKill =
                currentTick - kill.tick;

            return (
                ticksSinceKill >= 0 &&
                ticksSinceKill <= KILL_VISIBLE_TICKS
            );
        })
        .slice(-MAX_VISIBLE_KILLS)
        .reverse();

    if (visibleKills.length === 0) {
        return null;
    }

    return (
        <div className="kill-feed">
            {visibleKills.map((kill) => {
                const attackerTeam = getPlayerTeamAtTick(
                    players,
                    kill.attacker_steamid,
                    kill.tick
                );

                const victimTeam = getPlayerTeamAtTick(
                    players,
                    kill.victim_steamid,
                    kill.tick
                );

                return (
                    <div
                        key={`${kill.tick}-${kill.attacker_steamid}-${kill.victim_steamid}`}
                        className="kill-feed-item"
                    >
                        <span
                            className={[
                                "kill-feed-player",
                                getTeamClass(attackerTeam),
                            ].join(" ")}
                        >
                            {kill.attacker_name}
                        </span>

                        {kill.assister_name && (
                            <span className="kill-feed-assist">
                                + {kill.assister_name}
                            </span>
                        )}

                        <span className="kill-feed-weapon">
                            {getWeaponName(kill.weapon)}
                        </span>

                        {kill.headshot && (
                            <span
                                className="kill-feed-headshot"
                                title="Headshot"
                            >
                                HS
                            </span>
                        )}

                        <span
                            className={[
                            "kill-feed-player",
                            getTeamClass(victimTeam),
                        ].join(" ")}
                        >
                            {kill.victim_name}
                        </span>
                    </div>
                );
            })}
        </div>
    );
}

export default KillFeed;