import { Link } from "react-router-dom";

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
            </section>


            <section className="match-section">
                <div className="match-section-header">
                    <p className="upload-eyebrow">
                        PLAYERS
                    </p>

                    <h2>Match statistics</h2>

                    <p>
                        Full statistics for all players will appear here.
                    </p>
                </div>

                <div className="match-placeholder">
                    Player scoreboard
                </div>
            </section>


            <section className="match-section">
                <div className="match-section-header">
                    <p className="upload-eyebrow">
                        REPLAY
                    </p>

                    <h2>Match replay</h2>
                </div>

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


            <section className="match-section analysis-placeholder">
                <div className="match-section-header">
                    <p className="upload-eyebrow">
                        ANALYSIS
                    </p>

                    <h2>Key situations</h2>

                    <p>
                        Important moments from your match will appear here.
                    </p>
                </div>

                <div className="match-placeholder">
                    Visual match analysis
                </div>
            </section>

        </main>
    );
}


export default MatchPage;