import { useEffect, useState } from "react";

import "./App.css";
import reportData from "./data/report.json";
import Header from "./components/Header";
import Summary from "./components/Summary";
import Radar from "./components/Radar";
import Timeline from "./components/Timeline";

import radarData from "./data/radar.json";

function App() {
    const masterTicks = (
        radarData.bomb?.states ?? []
    ).map((state) => state.tick);

    const maxTickIndex = Math.max(
        0,
        masterTicks.length - 1
    );

    const [tickIndex, setTickIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);

    useEffect(() => {
    if (!isPlaying) {
        return;
    }

    const interval = setInterval(() => {
        setTickIndex((prev) => {
            if (prev >= maxTickIndex) {
                setIsPlaying(false);
                return maxTickIndex;
            }

            return prev + 1;
        });
    }, 100);

    return () => clearInterval(interval);
}, [isPlaying, maxTickIndex]);

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