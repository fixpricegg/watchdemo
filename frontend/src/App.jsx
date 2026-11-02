import { useState } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import "./App.css";
import AccountShell from "./pages/AccountShell";
import Header from "./components/Header";
import MatchReplay from "./components/MatchReplay";
import HomePage from "./pages/HomePage";
import UploadPage from "./pages/UploadPage";
import SavedReportsPage from "./pages/SavedReportsPage";
import SavedReportPage from "./pages/SavedReportPage";
import { fetchJSON } from "./api";

function Workspace() {
    const navigate = useNavigate();
    const [demoFile, setDemoFile] = useState(null);
    const [players, setPlayers] = useState([]);
    const [uploadedFilename, setUploadedFilename] = useState("");
    const [uploadedMatchId, setUploadedMatchId] = useState(null);
    const [selectedPlayer, setSelectedPlayer] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadError, setUploadError] = useState("");
    const [analysisResult, setAnalysisResult] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analysisError, setAnalysisError] = useState("");

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
        setUploadedMatchId(null);
        setUploadedFilename("");
        setAnalysisError("");
        const formData = new FormData();
        formData.append("file", demoFile);
        try {
            const data = await fetchJSON("/demo/upload", { method: "POST", body: formData });
            setPlayers(data.players ?? []);
            setUploadedFilename(data.original_filename ?? data.filename ?? "");
            setUploadedMatchId(data.match_id);
        } catch (error) {
            setUploadError(error.message);
        } finally {
            setIsUploading(false);
        }
    }

    async function handleAnalyze() {
        if (!selectedPlayer || !uploadedMatchId) return;
        setIsAnalyzing(true);
        setAnalysisError("");
        try {
            const data = await fetchJSON("/demo/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ match_id: uploadedMatchId, steamid: selectedPlayer.steamid }),
            });
            setAnalysisResult(data.result);
            navigate(`/reports/${data.report_id}`);
        } catch (error) {
            setAnalysisError(error.message);
        } finally {
            setIsAnalyzing(false);
        }
    }

    return (
        <div>
            <Header />
            <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/upload" element={<UploadPage {...{
                    demoFile, setDemoFile, players, uploadedFilename, selectedPlayer, setSelectedPlayer,
                    isUploading, uploadError, handleUpload, handleAnalyze, isAnalyzing, analysisError,
                }} />} />
                <Route path="/match" element={<MatchReplay key={uploadedMatchId} analysisResult={analysisResult} />} />
                <Route path="/reports" element={<SavedReportsPage />} />
                <Route path="/reports/:reportId" element={<SavedReportPage />} />
                <Route path="*" element={<HomePage />} />
            </Routes>
        </div>
    );
}

export default function App() {
    return <AccountShell><Workspace /></AccountShell>;
}
