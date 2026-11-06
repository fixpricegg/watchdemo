import { useEffect, useState } from "react";
import MatchPage from "../pages/MatchPage";

export default function MatchReplay({ analysisResult }) {
    const [tickIndex, setTickIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);
    const radarData = analysisResult ? {
        ...analysisResult.radar,
        rounds: analysisResult.timeline_rounds ?? [],
        events: analysisResult.events ?? [],
    } : null;
    const maxTickIndex = Math.max(0, (radarData?.bomb?.states?.length ?? 0) - 1);

    useEffect(() => {
        if (!isPlaying) return;
        const interval = setInterval(() => {
            setTickIndex((previous) => {
                if (previous >= maxTickIndex) {
                    setIsPlaying(false);
                    return maxTickIndex;
                }
                return previous + 1;
            });
        }, 100);
        return () => clearInterval(interval);
    }, [isPlaying, maxTickIndex]);

    return <MatchPage {...{
        analysisResult, radarData, tickIndex, setTickIndex, isPlaying, setIsPlaying,
    }} />;
}
