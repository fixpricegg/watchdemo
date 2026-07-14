import infernoMap from "../assets/maps/de_inferno_radar.png";
import radarData from "../data/radar.json";

function Radar({ tickIndex }) {
    const players = Object.values(radarData.players);

    const mapInfo = {
        pos_x: -2087,
        pos_y: 3870,
        scale: 4.9,
    };

    return (
        <section>
            <h2>Radar</h2>

            <div className="radar-container">
                <img
                    src={infernoMap}
                    alt="Inferno radar"
                    className="radar-map"
                />

                {players.map((player, index) => {
                    const pos = player.positions[tickIndex];

                    if (!pos) return null;

                    const imageX =
                        (pos.x - mapInfo.pos_x) / mapInfo.scale;

                    const imageY =
                        (mapInfo.pos_y - pos.y) / mapInfo.scale;

                    const team = pos.team || player.team;
                    const aliveClass = pos.is_alive ? "alive-dot" : "dead-dot";

                    return (
                        <div
                            key={index}
                            className={`player-dot ${aliveClass} ${
                                team === "CT"
                                    ? "ct-dot"
                                    : "t-dot"
                            }`}
                            title={`${player.name} · ${team} · ${
                                pos.is_alive ? "Alive" : "Dead"
                            }`}
                            style={{
                                left: `${imageX}px`,
                                top: `${imageY}px`,
                            }}
                        ></div>
                    );
                })}
            </div>
        </section>
    );
}

export default Radar;