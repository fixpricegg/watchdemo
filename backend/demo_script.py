import json

import radar
from analyzer_service import analyze_demo


DEMO_PATH = "demos/match18cache.dem"
PLAYER = "StRoGo"


def main():
    try:
        result = analyze_demo(
            DEMO_PATH,
            PLAYER
        )
    except Exception as error:
        print(f"Ошибка анализа: {error}")
        return

    with open(
        "report.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            result["report"],
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        "Frontend report сохранён в report.json"
    )

    with open(
        "report.md",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(
            result["report_text"]
        )

    print(
        "\nОтчёт сохранён в report.md"
    )

    radar.export_radar_json(
        result["radar"],
        result["timeline_rounds"],
        result["events"]
    )


if __name__ == "__main__":
    main()