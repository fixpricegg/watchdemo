# Запуск интеграционной версии WatchDemo

Рабочая папка: `WatchDemo-ivr`, ветка `integration/ivr-2026-11-05`.
Основная `WatchDemo` и worktree Codex используются отдельно.

## Локальный запуск

Нужны Python с зависимостями `backend/requirements.txt`, Node.js с зависимостями
`frontend/package-lock.json` и PostgreSQL. В текущей папке уже есть локальные
`.venv` и `node_modules`; они не включаются в Git.

1. Создайте отдельную базу PostgreSQL и роль для интеграционной версии.
   Не подключайте тесты к рабочей базе. Реальные пароли в Git не сохраняются.
2. В PowerShell из `WatchDemo-ivr/backend` задайте настройки и запустите API:

```powershell
$env:WATCHDEMO_DATABASE_URL = 'postgresql://USER:PASSWORD@127.0.0.1:5432/DATABASE'
$env:WATCHDEMO_UPLOAD_DIR = Join-Path $PWD 'uploads'
$env:WATCHDEMO_COOKIE_SECURE = 'false' # только локальный HTTP
.\.venv\Scripts\python.exe manage_storage.py migrate
.\.venv\Scripts\python.exe manage_storage.py check
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

3. В другом PowerShell из `WatchDemo-ivr/frontend`:

```powershell
npm ci # только если зависимости ещё не установлены
npm run dev
```

4. Откройте `http://localhost:5173`, зарегистрируйтесь и войдите. Загрузите `.dem`,
   выберите игрока и запустите анализ. В отчёте выберите карточку эпизода и нажмите
   «Открыть на радаре». Воспроизведение остановится на ближайшем кадре нужного раунда.
   Исходный тик и показанный кадр подписаны отдельно. Сохранённые отчёты открываются
   в разделе «Мои отчёты» и экспортируются в JSON.

По умолчанию разрешены локальные origin, указанные в `backend/.env.example`.
При смене адресов согласуйте `WATCHDEMO_ALLOWED_ORIGINS` и `VITE_API_URL`.
Для восстановления пароля через реальные письма настройте SMTP по
`docs/accounts-ivr.md`; без SMTP реальная доставка письма не обещается.

## Координаты бомбы

В этой рабочей папке исполняемый C4 extractor находится в
`tools/c4_extractor/bin/c4-extractor-windows-amd64.exe`. Двоичный файл игнорируется
Git. В новом checkout соберите его по `tools/c4_extractor/build.ps1` (нужен Go)
или укажите проверенный файл через `WATCHDEMO_C4_EXTRACTOR`.
Исходники и лицензии сохранены в ветке.

## Проверки

```powershell
# Из backend. URL должен указывать на отдельную тестовую базу.
$env:WATCHDEMO_TEST_DATABASE_URL = 'postgresql://TEST_USER:TEST_PASSWORD@127.0.0.1:5432/TEST_DATABASE'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -u scripts/qa_ivr_real_demo.py 'PATH_TO_DEMO.dem' --output '../review-ivr/real'
```

Тесты создают частные схемы `watchdemo_test_UUID` и удаляют только эти схемы.
Реальная проверка удаляет временную копию загрузки; исходная демозапись сохраняется.
В `frontend`: `npm run lint`, затем `npm run build`.
Браузерная проверка: `backend/scripts/qa_ivr_browser.py --output ... --real-result ...`;
ей нужны Playwright в `NODE_PATH`, Chromium/Chrome и отдельный TEST URL.
Необязательные пути: `WATCHDEMO_NODE`, `WATCHDEMO_CHROME`.

## Границы результата

Entry Death, Missed Trade v2 и Buy Mismatch создают кандидатов для разбора.
Ни один из них не объявляет решение игрока доказанной ошибкой. Ноль кандидатов
не означает отсутствие ошибок. Расширенная навигационная геометрия доступна
для Nuke; статическая трассировка не заменяет видимость с учётом дыма и объектов.
При одинаковых именах игроков общий анализатор пока не обеспечивает однозначный
SteamID-сценарий. Новый дизайн и видеоматериалы в эту интеграцию не входят.
