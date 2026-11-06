# Аккаунты и защита данных — ревью

2 ноября 2026. Ветка `feature/postgres-match-storage`, база `c92d318`.
Изолированный worktree: `C:\Users\petko\.codex\worktrees\postgres-match-storage\WatchDemo`.
Коммит локальный; merge и push в `feature/game-library` не выполнялись.
Пользовательский `codex-review.diff` не изменялся и не включался в коммит.

Добавлены настоящие пользователи PostgreSQL, Argon2id, серверные сессии с
HttpOnly-cookie и CSRF, профиль, смена/сброс пароля, SMTP и React-формы.
История, чтение результатов и повторный анализ доступны только владельцу.
Старая миграция 001 неизменна, 002 сохраняет legacy-результаты без владельцев,
скрывает их от аккаунтов и запрещает новые матчи без владельца.
Структура JSON-результата не менялась. Внешние provider/subject предусмотрены
отдельной таблицей; FACEIT OAuth/import не реализованы.

## Проверки

| Проверка | Результат |
|---|---|
| Backend unittest, PostgreSQL 17.6 на 127.0.0.1:55439 | 254 пройдено, 0 пропущено, 0 упало |
| PostgreSQL-кейсы в этом прогоне | 19 storage + 10 accounts; не SQLite и не моки хранения |
| Реальный перезапуск Uvicorn | Повторный вход и идентичный старый результат после остановки/старта процесса |
| Миграция 001 → 002 | Legacy match/report сохранены, скрыты; новые ownerless inserts запрещены |
| Пользователь B | Списки без A; прямые match/report UUID и повторный анализ A возвращают 404 |
| Logout, смена/сброс пароля | Сессии отзываются в БД; повтор cookie не даёт доступа |
| Почта | Реальный loopback aiosmtpd; ссылка одноразовая, проверено истечение; ответы email recovery одинаковые |
| CSRF, Origin/CORS, секреты | Неверные токены/origins отклонены, credentialed CORS ограничен, ошибки БД/валидации не возвращают секреты |
| npm run build | Успешно |
| ESLint изменённых React/API-файлов | Успешно; весь frontend не объявляется чистым (прежние ошибки Radar/UploadPage вне scope) |
| Chrome browser smoke | Вход, открытие и refresh отчёта, профиль, logout, регистрация B, отказ B по прямому URL; 0 page errors |
| Настоящая demo | match19nuke.dem, 255760505 байт, wesiqe, 22 раунда; полный результат сохранён и повторно прочитан после нового старта приложения |

Реальный анализ использовал имеющийся C4 extractor через
`WATCHDEMO_C4_EXTRACTOR` без изменения анализатора. Первый запуск без этой
зависимости завершился ошибкой; успешный запуск выполнен с настроенным путём.
Новый старт приложения в real-demo smoke — отдельный экземпляр FastAPI;
перезапуск отдельного процесса Uvicorn дополнительно проверяется unittest-кейсом.

SHA-256 исходной demo до и после:
`59c05c5e8927b877cb69620aa002416f9690e3c44c009dcad6743367833036ac`.
SHA-256 нормализованного полного результата:
`33e7a8dc38d58f9946b0e0d53055a89868739fcd02c37586a024e9b42216e96c`.
Исходная demo только читалась. Загруженная копия и результаты создавались в
отдельном временном каталоге и новой схеме PostgreSQL; затем удалены только эти
тестовые объекты. Существующая рабочая база не использовалась.

Полные локальные логи: `review-accounts/backend-tests.log`, `frontend-build.log`,
`frontend-lint.log`, `browser.log`, `real-demo.log`. Они не включены в Git.
Diff для этого этапа: `review-accounts/accounts.patch` относительно `c92d318`.

## Изменённые файлы

- `.gitignore`
- `backend/.env.example`
- `backend/app.py`
- `backend/auth.py`
- `backend/requirements.txt`
- `backend/requirements-test.txt`
- `backend/storage/repository.py`
- `backend/storage/migrations/002_users_and_ownership.sql`
- `backend/tests/test_storage.py`
- `backend/tests/test_accounts.py`
- `backend/scripts/qa_browser_accounts.py`
- `backend/scripts/qa_real_demo_accounts.py`
- `frontend/src/App.jsx`
- `frontend/src/api.js`
- `frontend/src/pages/AccountShell.jsx`
- `tools/qa_accounts/browser.cjs`
- `docs/postgresql-storage.md`
- `docs/accounts-ivr.md`
- `docs/accounts-review.md`

Инструкция Windows/PostgreSQL, SMTP, ограничения и таблица всех 13 требований
`final_application.md`: [accounts-ivr.md](accounts-ivr.md).
Прежние незавершённые пункты ADR, полного перехода от проблем к replay и
пользовательского JSON-экспорта не объявляются выполненными этой задачей.
