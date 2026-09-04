function UploadPage({
    demoFile,
    setDemoFile,
    players,
    uploadedFilename,
    selectedPlayer,
    setSelectedPlayer,
    isUploading,
    uploadError,
    handleUpload,
    handleAnalyze,
    isAnalyzing,
    analysisError,
}) {
    const ctPlayers = players.filter(
        (player) => player.team === "CT"
    );

    const tPlayers = players.filter(
        (player) => player.team === "T"
    );

    return (
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
                                Selected:{" "}
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
    );
}


export default UploadPage;