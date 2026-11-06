import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchJSON } from "../api";

const PAGE_SIZE = 20;
const statuses = { completed: "Готов", processing: "Обрабатывается", failed: "Ошибка" };

export default function SavedReportsPage() {
    const [offset, setOffset] = useState(0);
    const [attempt, setAttempt] = useState(0);
    const [state, setState] = useState(null);
    useEffect(() => {
        const controller = new AbortController();
        fetchJSON(`/reports?limit=${PAGE_SIZE}&offset=${offset}`, { signal: controller.signal })
            .then((data) => {
                if (!controller.signal.aborted) setState({ offset, attempt, reports: data.reports });
            })
            .catch((error) => {
                if (!controller.signal.aborted) setState({ offset, attempt, error: error.message });
            });
        return () => controller.abort();
    }, [offset, attempt]);
    const current = state?.offset === offset && state?.attempt === attempt ? state : null;
    return (
        <main className="upload-page">
            <section className="upload-card">
                <h1>Сохранённые отчёты</h1>
                <p>Результаты доступны после перезапуска сервера без повторного анализа demo.</p>
                <button className="secondary-button" onClick={() => setAttempt((v) => v + 1)}>
                    Обновить
                </button>
                {!current && <p role="status">Загрузка…</p>}
                {current?.error && <p role="alert">{current.error}</p>}
                {current?.reports?.length === 0 && <p>Отчётов пока нет. <Link to="/upload">Загрузить demo</Link></p>}
                <ul>
                    {current?.reports?.map((report) => (
                        <li key={report.id}>
                            <p>
                                {report.original_filename} · {report.player_name} · {report.map_name || "Карта не определена"}
                                {" · "}{new Date(report.created_at).toLocaleString()}
                                {" · "}{statuses[report.status] || report.status}
                            </p>
                            {report.status === "completed" && <Link to={`/reports/${report.id}`}>Открыть отчёт</Link>}
                            {report.error && <p>{report.error}</p>}
                        </li>
                    ))}
                </ul>
                <button disabled={offset === 0} onClick={() => setOffset((v) => Math.max(0, v - PAGE_SIZE))}>Назад</button>
                <button disabled={!current?.reports || current.reports.length < PAGE_SIZE}
                    onClick={() => setOffset((v) => v + PAGE_SIZE)}>Далее</button>
            </section>
        </main>
    );
}
