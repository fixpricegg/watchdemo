import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import ReviewFindings from "../components/ReviewFindings";

import Summary from "../components/Summary";
import Radar from "../components/Radar";
import Timeline from "../components/Timeline";


function MatchPage({
    analysisResult,
    radarData,
    tickIndex,
    setTickIndex,
    isPlaying,
    setIsPlaying,
}) {
    const replaySection = useRef(null);
    const [selected, setSelected] = useState(null);
    function seekEpisode(finding, frame) {
        setIsPlaying(false);
        setTickIndex(frame);
        setSelected(finding);
        replaySection.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    if (!analysisResult || !radarData) {
        return (
            <main className="upload-page">
                <section className="upload-card">
                    <h2>No match loaded</h2>

                    <p className="upload-description">
                        Upload and analyze a demo first.
                    </p>

                    <Link
                        to="/upload"
                        className="primary-button page-link"
                    >
                        Upload demo
                    </Link>
                </section>
            </main>
        );
    }

    return (
        <main className="match-page">

            <section className="match-section">
                <div className="match-section-header">
                    <p className="upload-eyebrow">
                        MATCH
                    </p>

                    <h1>
                        {analysisResult.report?.map ?? "Match"}
                    </h1>
                </div>

                <Summary report={analysisResult.report} />
                <ReviewFindings report={analysisResult.report} radarData={radarData} onSeek={seekEpisode} selectedId={selected?.id} />
            </section>


            <section className="match-section" ref={replaySection}>
                <div className="match-section-header">
                    <p className="upload-eyebrow">
                        REPLAY
                    </p>

                    <h2>Match replay</h2>
                </div>

                {selected && <p className="replay-selection" role="status">
                    Выбран эпизод: {selected.detector} · Раунд {selected.round} · Тик {selected.tick}.
                    Кадр радара: {radarData.bomb?.states?.[tickIndex]?.tick ?? "нет данных"}.
                </p>}
                <Radar
                    tickIndex={tickIndex}
                    radarData={radarData}
                />

                <Timeline
                    radarData={radarData}
                    tickIndex={tickIndex}
                    setTickIndex={setTickIndex}
                    isPlaying={isPlaying}
                    setIsPlaying={setIsPlaying}
                />
            </section>




        </main>
    );
}


export default MatchPage;