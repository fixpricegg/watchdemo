import { useEffect, useState } from "react";

import "./App.css";
import reportData from "./data/report.json";
import Header from "./components/Header";
import Summary from "./components/Summary";
import Radar from "./components/Radar";
import Timeline from "./components/Timeline";

import radarData from "./data/radar.json";

function App() {
    const players = Object.values(radarData.players);

    const [tickIndex, setTickIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);

    useEffect(() => {
        if (!isPlaying) return;

        const interval = setInterval(() => {
            setTickIndex((prev) => {
                if (prev >= players[0].positions.length - 1) {
                    setIsPlaying(false);
                    return prev;
                }

                return prev + 1;
            });
        }, 100);

        return () => clearInterval(interval);
    }, [isPlaying, players]);

    return (
        <div>
            <Header />
            <Summary report={reportData} />

            <Radar tickIndex={tickIndex} />

            <Timeline
                tickIndex={tickIndex}
                setTickIndex={setTickIndex}
                isPlaying={isPlaying}
                setIsPlaying={setIsPlaying}
            />
        </div>
    );
}

export default App;