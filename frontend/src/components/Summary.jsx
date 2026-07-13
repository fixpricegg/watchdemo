function formatPercent(value) {
    if (value === null || value === undefined) {
        return "N/A";
    }

    return `${value}%`;
}

function Summary({ report }) {
    const summary = report.summary;
    const problems = report.top_problems || [];

    return (
        <section className="summary-section">
            <div className="summary-header">
                <div>
                    <p className="eyebrow">Match Summary</p>
                    <h2>{report.player}</h2>
                </div>

                <div className="map-pill">
                    {report.map}
                </div>
            </div>

            <div className="summary-grid">
                <div className="summary-card">
                    <span>Combat</span>
                    <strong>{summary.kills} / {summary.deaths}</strong>
                    <p>K/D {summary.kd}</p>
                </div>

                <div className="summary-card">
                    <span>Aim</span>
                    <strong>{formatPercent(summary.hs_rate)}</strong>
                    <p>Headshot rate</p>
                </div>

                <div className="summary-card">
                    <span>Entry</span>
                    <strong>
                        {summary.entry_kills} / {summary.entry_deaths}
                    </strong>
                    <p>{formatPercent(summary.entry_success)} success</p>
                </div>

                <div className="summary-card">
                    <span>Teamplay</span>
                    <strong>{summary.trade_kills}</strong>
                    <p>Trade kills</p>
                </div>

                <div className="summary-card">
                    <span>Multi-kills</span>
                    <strong>{summary.multi_kills}</strong>
                    <p>
                        2K {summary.two_k} · 3K {summary.three_k} · 4K {summary.four_k} · Ace {summary.ace}
                    </p>
                </div>
            </div>

            <div className="problems-block">
                <div className="problems-header">
                    <h3>Top Problems</h3>
                    <p>Главные вещи, которые сильнее всего повлияли на матч.</p>
                </div>

                {problems.length === 0 ? (
                    <div className="problem-card">
                        <strong>Критичных проблем не найдено</strong>
                        <p>По текущим правилам матч выглядит достаточно стабильным.</p>
                    </div>
                ) : (
                    <div className="problem-list">
                        {problems.map((problem, index) => (
                            <div className="problem-card" key={problem.name}>
                                <div className="problem-top">
                                    <span>#{index + 1}</span>
                                    <strong>{problem.name}</strong>
                                    <em>Score {problem.score}</em>
                                </div>

                                <p>{problem.description}</p>

                                {problem.advice && (
                                    <ul>
                                        {problem.advice.slice(0, 3).map((item) => (
                                            <li key={item}>{item}</li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </section>
    );
}

export default Summary;