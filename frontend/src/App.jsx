import { useEffect, useState } from "react";

import "./App.css";
import Header from "./components/Header";
import Summary from "./components/Summary";
import Radar from "./components/Radar";
import Timeline from "./components/Timeline";



function App() {
    const [tickIndex, setTickIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);

    const [demoFile, setDemoFile] = useState(null);
    const [players, setPlayers] = useState([]);
    const [uploadedFilename, setUploadedFilename] = useState("");
    const [selectedPlayer, setSelectedPlayer] = useState(null);

    const [isUploading, setIsUploading] = useState(false);
    const [uploadError, setUploadError] = useState("");

    // Пока null.
    // На следующем шаге сюда положим настоящий ответ backend.
    const [analysisResult, setAnalysisResult] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analysisError, setAnalysisError] = useState("");

    const liveRadarData = analysisResult
        ? {
            ...analysisResult.radar,
            rounds: analysisResult.timeline_rounds ?? [],
            events: analysisResult.events ?? [],
        }
        : null;

    const masterTicks = (
        liveRadarData?.bomb?.states ?? []
    ).map((state) => state.tick);

    const maxTickIndex = Math.max(
        0,
        masterTicks.length - 1
    );

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


    async function handleUpload() {
        if (!demoFile) {
            setUploadError("Сначала выбери .dem файл");
            return;
        }

        setIsUploading(true);
        setUploadError("");
        setPlayers([]);
        setSelectedPlayer(null);
        setAnalysisResult(null);

        const formData = new FormData();
        formData.append("file", demoFile);

        try {
            const response = await fetch(
                "http://127.0.0.1:8000/demo/upload",
                {
                    method: "POST",
                    body: formData,
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Ошибка загрузки демки"
                );
            }

            setPlayers(data.players ?? []);
            setUploadedFilename(data.filename ?? "");

        } catch (error) {
            setUploadError(error.message);
        } finally {
            setIsUploading(false);
        }
    }

    async function handleAnalyze() {
        if (!selectedPlayer || !uploadedFilename) {
            return;
        }

        setIsAnalyzing(true);
        setAnalysisError("");

        try {
            const response = await fetch(
                "http://127.0.0.1:8000/demo/analyze",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        filename: uploadedFilename,
                        steamid: selectedPlayer.steamid,
                    }),
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    typeof data.detail === "string"
                        ? data.detail
                        : "Ошибка анализа демки"
                );
            }

            console.log("ANALYSIS RESULT:", data.result);

            setTickIndex(0);
            setIsPlaying(false);
            setAnalysisResult(data.result);

        } catch (error) {
            setAnalysisError(error.message);
        } finally {
            setIsAnalyzing(false);
        }
    }

    const ctPlayers = players.filter(
        (player) => player.team === "CT"
    );

    const tPlayers = players.filter(
        (player) => player.team === "T"
    );


    return (
        <div>
            <Header />

            {!analysisResult && (
                <main className="upload-page">

                    <section className="upload-card">
                        <p className="upload-eyebrow">
                            CS2 Demo Analyzer
                        </p>

                        <h1>Analyze your match</h1>

                        <p className="upload-description">
                            Upload a CS2 demo and choose the player
                            you want to analyze.
                        </p>

                        <div className="upload-controls">
                            <input
                                type="file"
                                accept=".dem"
                                onChange={(event) => {
                                    setDemoFile(
                                        event.target.files[0] ?? null
                                    );
                                }}
                            />

                            <button
                                className="primary-button"
                                onClick={handleUpload}
                                disabled={isUploading}
                            >
                                {isUploading
                                    ? "Uploading..."
                                    : "Upload demo"}
                            </button>
                        </div>

                        {uploadError && (
                            <p className="upload-error">
                                {uploadError}
                            </p>
                        )}

                        {uploadedFilename && (
                            <p className="uploaded-file">
                                {uploadedFilename}
                            </p>
                        )}
                    </section>


                    {players.length > 0 && (
                        <section className="player-selection">
                            <div className="player-selection-header">
                                <h2>Choose your player</h2>

                                <p>
                                    Select yourself from the match.
                                </p>
                            </div>


                            <div className="teams-grid">

                                <div className="team-column">
                                    <h3 className="team-title ct-title">
                                        CT
                                    </h3>

                                    {ctPlayers.map((player) => (
                                        <button
                                            key={player.steamid}
                                            className={
                                                selectedPlayer?.steamid ===
                                                player.steamid
                                                    ? "player-card selected"
                                                    : "player-card"
                                            }
                                            onClick={() =>
                                                setSelectedPlayer(player)
                                            }
                                        >
                                            <span className="select-player-name">
                                                {player.name}
                                            </span>

                                            <span className="player-team">
                                                CT
                                            </span>
                                        </button>
                                    ))}
                                </div>


                                <div className="team-column">
                                    <h3 className="team-title t-title">
                                        T
                                    </h3>

                                    {tPlayers.map((player) => (
                                        <button
                                            key={player.steamid}
                                            className={
                                                selectedPlayer?.steamid ===
                                                player.steamid
                                                    ? "player-card selected"
                                                    : "player-card"
                                            }
                                            onClick={() =>
                                                setSelectedPlayer(player)
                                            }
                                        >
                                            <span className="select-player-name">
                                                {player.name}
                                            </span>

                                            <span className="player-team">
                                                T
                                            </span>
                                        </button>
                                    ))}
                                </div>

                            </div>


                            {selectedPlayer && (
                                <div className="analyze-section">
                                    <p>
                                        Selected:
                                        {" "}
                                        <strong>
                                            {selectedPlayer.name}
                                        </strong>
                                    </p>

                                    <button
                                        className="primary-button"
                                        onClick={handleAnalyze}
                                        disabled={isAnalyzing}
                                    >
                                        {isAnalyzing
                                            ? "Analyzing..."
                                            : "Analyze player"}
                                    </button>

                                    {analysisError && (
                                        <p className="upload-error">
                                            {analysisError}
                                        </p>
                                    )}
                                </div>
                            )}
                        </section>
                    )}

                </main>
            )}


            {analysisResult && liveRadarData && (
                <>
                    <Summary report={analysisResult.report} />

                    <Radar
                        tickIndex={tickIndex}
                        radarData={liveRadarData}
                    />

                    <Timeline
                        radarData={liveRadarData}
                        tickIndex={tickIndex}
                        setTickIndex={setTickIndex}
                        isPlaying={isPlaying}
                        setIsPlaying={setIsPlaying}
                    />
                </>
            )}
        </div>
    );
}


export default App;