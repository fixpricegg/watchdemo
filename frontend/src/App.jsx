import { useEffect, useState } from "react";
import {
    Route,
    Routes,
    useNavigate,
} from "react-router-dom";

import "./App.css";

import Header from "./components/Header";

import HomePage from "./pages/HomePage";
import UploadPage from "./pages/UploadPage";
import MatchPage from "./pages/MatchPage";


function App() {
    const navigate = useNavigate();

    const [tickIndex, setTickIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);

    const [demoFile, setDemoFile] = useState(null);
    const [players, setPlayers] = useState([]);
    const [uploadedFilename, setUploadedFilename] = useState("");
    const [selectedPlayer, setSelectedPlayer] = useState(null);

    const [isUploading, setIsUploading] = useState(false);
    const [uploadError, setUploadError] = useState("");

    const [analysisResult, setAnalysisResult] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analysisError, setAnalysisError] = useState("");


    const liveRadarData = analysisResult
        ? {
            ...analysisResult.radar,
            rounds:
                analysisResult.timeline_rounds ?? [],
            events:
                analysisResult.events ?? [],
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
            setUploadError(
                "Сначала выбери .dem файл"
            );
            return;
        }

        setIsUploading(true);
        setUploadError("");

        setPlayers([]);
        setSelectedPlayer(null);
        setAnalysisResult(null);

        const formData = new FormData();

        formData.append(
            "file",
            demoFile
        );

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
                    data.detail ||
                    "Ошибка загрузки демки"
                );
            }

            setPlayers(
                data.players ?? []
            );

            setUploadedFilename(
                data.filename ?? ""
            );

        } catch (error) {
            setUploadError(
                error.message
            );
        } finally {
            setIsUploading(false);
        }
    }


    async function handleAnalyze() {
        if (
            !selectedPlayer ||
            !uploadedFilename
        ) {
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
                        "Content-Type":
                            "application/json",
                    },

                    body: JSON.stringify({
                        filename:
                            uploadedFilename,

                        steamid:
                            selectedPlayer.steamid,
                    }),
                }
            );

            const data =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    typeof data.detail ===
                    "string"
                        ? data.detail
                        : "Ошибка анализа демки"
                );
            }

            setTickIndex(0);
            setIsPlaying(false);

            setAnalysisResult(
                data.result
            );

            navigate("/match");

        } catch (error) {
            setAnalysisError(
                error.message
            );
        } finally {
            setIsAnalyzing(false);
        }
    }


    return (
        <div>
            <Header />

            <Routes>

                <Route
                    path="/"
                    element={
                        <HomePage />
                    }
                />

                <Route
                    path="/upload"
                    element={
                        <UploadPage
                            demoFile={demoFile}
                            setDemoFile={setDemoFile}

                            players={players}

                            uploadedFilename={
                                uploadedFilename
                            }

                            selectedPlayer={
                                selectedPlayer
                            }

                            setSelectedPlayer={
                                setSelectedPlayer
                            }

                            isUploading={
                                isUploading
                            }

                            uploadError={
                                uploadError
                            }

                            handleUpload={
                                handleUpload
                            }

                            handleAnalyze={
                                handleAnalyze
                            }

                            isAnalyzing={
                                isAnalyzing
                            }

                            analysisError={
                                analysisError
                            }
                        />
                    }
                />

                <Route
                    path="/match"
                    element={
                        <MatchPage
                            analysisResult={
                                analysisResult
                            }

                            radarData={
                                liveRadarData
                            }

                            tickIndex={
                                tickIndex
                            }

                            setTickIndex={
                                setTickIndex
                            }

                            isPlaying={
                                isPlaying
                            }

                            setIsPlaying={
                                setIsPlaying
                            }
                        />
                    }
                />

            </Routes>
        </div>
    );
}


export default App;