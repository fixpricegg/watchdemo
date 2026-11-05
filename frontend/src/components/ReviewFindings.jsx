import { useState } from "react";
import { findEpisodeFrame } from "../utils/replay";
import "./ReviewFindings.css";

export default function ReviewFindings({ report, radarData, onSeek, selectedId }) {
    const [filter, setFilter] = useState("all");
    const findings = report.review_findings ?? [];
    const groups = report.top_problems ?? [];
    const visible = filter === "all" ? findings : findings.filter((f) => f.type === filter);
    const states = radarData.bomb?.states ?? [];
    return (
        <section className="review-section" aria-labelledby="review-heading">
            <h2 id="review-heading">Эпизоды для разбора</h2>
            <p>Приоритет задаёт порядок просмотра. Это не оценка тяжести ошибки и не доказательство неправильного решения.</p>
            <div className="review-filters" aria-label="Тип эпизода">
                <button aria-pressed={filter === "all"} onClick={() => setFilter("all")}>Все ({findings.length})</button>
                {groups.filter((g) => g.type).map((group) => (
                    <button key={group.type} aria-pressed={filter === group.type} onClick={() => setFilter(group.type)}>
                        {group.detector} ({group.count})
                    </button>
                ))}
            </div>
            {!findings.length && <p>{report.review_findings
                ? "Кандидаты по этим правилам не найдены. Это не означает отсутствие ошибок."
                : "В этом сохранённом отчёте ещё нет эпизодов. Запустите новый анализ матча."}</p>}
            <div className="review-list">
                {visible.map((finding) => {
                    const frame = findEpisodeFrame(states, radarData.rounds ?? [], finding);
                    const round = radarData.rounds?.find((r) => r.round === finding.round);
                    const elapsed = round ? Math.max(0, (finding.tick - round.live_start_tick) / 64).toFixed(1) : null;
                    return (
                        <article key={finding.id} className={`review-card ${selectedId === finding.id ? "review-selected" : ""}`}>
                            <h3>{finding.detector} · Раунд {finding.round}</h3>
                            <p>Тик {finding.tick}{elapsed !== null && ` · ${elapsed} с от начала раунда`} · Требует проверки</p>
                            <p>{finding.description}</p>
                            <ul>{finding.facts.map((fact, index) => <li key={index}>{fact}</li>)}</ul>
                            <details><summary>Ограничения вывода</summary>
                                <ul>{finding.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul>
                            </details>
                            <button disabled={frame === null} onClick={() => onSeek(finding, frame)}>
                                Открыть на радаре · раунд {finding.round}
                            </button>
                            {frame === null && <p>Кадры этого раунда отсутствуют.</p>}
                        </article>
                    );
                })}
            </div>
        </section>
    );
}
