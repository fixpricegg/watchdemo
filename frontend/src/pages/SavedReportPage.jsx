import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchJSON } from "../api";
import MatchReplay from "../components/MatchReplay";
import { API_URL } from "../api";

export default function SavedReportPage() {
    const { reportId } = useParams();
    const [state, setState] = useState(null);
    useEffect(() => {
        const controller = new AbortController();
        fetchJSON(`/reports/${encodeURIComponent(reportId)}`, { signal: controller.signal })
            .then((report) => {
                if (!controller.signal.aborted) setState({ reportId, report });
            })
            .catch((error) => {
                if (!controller.signal.aborted) setState({ reportId, error: error.message });
            });
        return () => controller.abort();
    }, [reportId]);
    const current = state?.reportId === reportId ? state : null;
    const report = current?.report;
    let message = "Загрузка отчёта…";
    if (current?.error) message = current.error;
    else if (report?.status === "failed") message = report.error || "Анализ завершился ошибкой";
    else if (report?.status === "processing") message = "Анализ ещё выполняется. Откройте отчёт позже.";
    else if (report && report.format_version !== 1) message = "Эта версия отчёта пока не поддерживается";

    return (
        <>
            <p><Link to="/reports">Все сохранённые отчёты</Link></p>
            {report?.status === "completed" && <p><a href={`${API_URL}/reports/${encodeURIComponent(reportId)}/export`}>Скачать отчёт JSON</a></p>}
            {report?.status === "completed" && report.format_version === 1 && report.result
                ? <MatchReplay key={reportId} analysisResult={report.result} />
                : <main className="upload-page"><p role={current?.error ? "alert" : "status"}>{message}</p></main>}
        </>
    );
}
