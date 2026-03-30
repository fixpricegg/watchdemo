# WatchDemo MVP

MVP-платформа для анализа CS2 demo (`.dem`) с простым AI-отчётом:
- загрузка demo-файла;
- расчет ключевой статистики матча;
- автоматическое выявление ошибок;
- персональные рекомендации по улучшению игры.

## Stack
- **Backend:** FastAPI
- **Frontend:** Vanilla HTML/CSS/JS
- **Tests:** Pytest

## Запуск локально
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Откройте: `http://127.0.0.1:8000`

## API
### `POST /api/analyze`
`multipart/form-data` с полем `file` (обязательно `.dem`).

Пример ответа:
- summary (карта, раунды, impact score)
- stats (kills/deaths/assists, ADR, HS%, utility, clutch/opening)
- mistakes (описания ошибок)
- recommendations (список действий для улучшения)

### `GET /api/health`
Health-check endpoint.

## Тесты
```bash
pytest
```

## Важное ограничение MVP
Сейчас AI-анализ **эвристический** (правила + вычисляемые показатели), чтобы быстро показать end-to-end продукт. В следующей итерации можно заменить модуль анализа на модель, обученную на реальных CS2-демках.
