import infernoMap from "../assets/maps/de_inferno_radar.png";
import mirageMap from "../assets/maps/de_mirage_radar.png";
import dust2Map from "../assets/maps/de_dust2_radar.png";
import ancientMap from "../assets/maps/de_ancient_radar.png";
import anubisMap from "../assets/maps/de_anubis_radar.png";
import cacheMap from "../assets/maps/de_cache_radar.png";
import nukeMap from "../assets/maps/de_nuke_radar.png";
import nukeLowerMap from "../assets/maps/de_nuke_lower_radar.png";

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

    de_dust2: {
    name: "Dust2",
    image: dust2Map,
    posX: -2476,
    posY: 3239,
    scale: 4.4,
    },
    
    de_ancient: {
    name: "Ancient",
    image: ancientMap,
    posX: -2953,
    posY: 2164,
    scale: 5,
    },

    de_anubis: {
    name: "Anubis",
    image: anubisMap,
    posX: -2796,
    posY: 3328,
    scale: 5.22,
    },

    de_cache: {
    name: "Cache",
    image: cacheMap,
    posX: -2000,
    posY: 3250,
    scale: 5.5,
    },

    de_nuke: {
    name: "Nuke",

    image: nukeMap,
    lowerImage: nukeLowerMap,

    posX: -3453,
    posY: 2887,
    scale: 7,

    lowerImageSize: 1254,

    lowerPosX: -1203.17,
    lowerPosY: 1105.91,

    lowerScaleX: 3.1517,
    lowerScaleY: 3.1634,
    },
    
};
export function getMapConfig(mapName) {
    return maps[mapName] ?? null;
}