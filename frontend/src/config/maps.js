import infernoMap from "../assets/maps/de_inferno_radar.png";
import mirageMap from "../assets/maps/de_mirage_radar.png";

const maps = {
    de_inferno: {
        name: "Inferno",
        image: infernoMap,
        posX: -2087,
        posY: 3870,
        scale: 4.9,
    },

    de_mirage: {
        name: "Mirage",
        image: mirageMap,
        posX: -3230,
        posY: 1713,
        scale: 5,
    },
};
export function getMapConfig(mapName) {
    return maps[mapName] ?? null;
}