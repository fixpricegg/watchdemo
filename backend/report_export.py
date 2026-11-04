"""Public report projection; never serialize database/user/session rows wholesale."""
SUMMARY_FIELDS = {"kills", "deaths", "kd", "adr", "hs_rate", "entry_kills", "entry_deaths",
                  "entry_success", "trade_kills", "multi_kills", "two_k", "three_k", "four_k", "ace"}


def export_report(row):
    report = row["result"].get("report", {})
    summary = report.get("summary", {})
    problems = [{"name": problem.get("name") if isinstance(problem.get("name"), str) else None,
                 "description": problem.get("description") if isinstance(problem.get("description"), str) else None,
                 "score": problem.get("score") if type(problem.get("score")) in (int, float) else None,
                 "advice": [item for item in problem.get("advice", []) if isinstance(item, str)]
                 if isinstance(problem.get("advice", []), list) else []}
                for problem in report.get("top_problems", []) if isinstance(problem, dict)]
    return {"format_version": 1, "report_id": str(row["id"]), "match_id": str(row["match_id"]),
            "created_at": row["created_at"].isoformat(),
            "report": {"player": report.get("player"), "map": report.get("map"),
                       "summary": {key: summary[key] for key in SUMMARY_FIELDS if key in summary
                                   and (summary[key] is None or type(summary[key]) in (int, float))},
                       "top_problems": problems},
            "notice": "Top Problems — статистические сигналы, не подтверждённые игровые ошибки."}
