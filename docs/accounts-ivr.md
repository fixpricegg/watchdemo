# Аккаунты и PostgreSQL — ИВР, 2 ноября 2026

Работа продолжает `c92d318` в `feature/postgres-match-storage`. Основной checkout,
детекторы, Match Library, Geometry Layer, Decision Context и анализатор не меняются.
Изменения предназначены для ревью; merge/push не выполняются.

## Запуск на Windows

Нужны Python 3.13, Node/npm и установленный PostgreSQL (проверено на 17.6).
Создайте отдельную базу и роль. Из PostgreSQL `bin`:

```powershell
.\createuser.exe -U postgres -P watchdemo
.\createdb.exe -U postgres -O watchdemo watchdemo
```

`-P` интерактивно запрашивает новый пароль. В backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Задайте WATCHDEMO_DATABASE_URL в окружении с паролем своей новой роли.
# Формат: postgresql://watchdemo:<password>@127.0.0.1:5432/watchdemo
$env:WATCHDEMO_COOKIE_SECURE = 'false' # только для локального HTTP
$env:WATCHDEMO_FRONTEND_URL = 'http://127.0.0.1:5173'
$env:WATCHDEMO_ALLOWED_ORIGINS = 'http://127.0.0.1:5173'
python manage_storage.py migrate
python manage_storage.py check
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

В frontend: `npm ci`, затем `npm run dev -- --host 127.0.0.1`.
Откройте `http://127.0.0.1:5173`. Используйте один hostname для frontend/backend:
не смешивайте localhost и 127.0.0.1. Приложение не загружает `.env` автоматически;
переменные из `backend/.env.example` нужно экспортировать в окружение процесса.
Для настоящего анализа нужна прежняя зависимость C4 extractor; путь можно задать
через `WATCHDEMO_C4_EXTRACTOR`, не меняя анализатор.

Для HTTPS оставляйте `WATCHDEMO_COOKIE_SECURE=true` (значение по умолчанию).
Cookie имеет HttpOnly, SameSite=Lax, Path=/, срок 7 дней и не имеет Domain.
Продакшен должен использовать HTTPS и frontend/API на одном site, точный CORS
allowlist и SPA fallback на index.html. Смена site потребует отдельной настройки,
не ослабляйте SameSite и CORS для обхода ошибок локальной конфигурации.

## Проверка почты без секретов

В дополнительном терминале backend:

```powershell
python -m pip install -r requirements-test.txt
python -m aiosmtpd -n -l 127.0.0.1:1025
```

В окружении backend задайте `WATCHDEMO_SMTP_HOST=127.0.0.1`,
`WATCHDEMO_SMTP_PORT=1025`, `WATCHDEMO_SMTP_TLS=none` и перезапустите API.
Этот loopback SMTP принимает письма без внешней доставки. Для чтения ссылок
используйте debug-вывод тестового сервера (при необходимости `-d`), либо Mailpit
на том же SMTP-порту. Автоматический тест использует настоящий aiosmtpd и читает
принятое письмо напрямую, без внешнего аккаунта.

Для настоящего SMTP доступны HOST, PORT, FROM, USER, PASSWORD и TLS (`starttls`
по умолчанию, либо `ssl`). Пароли не сохраняйте в Git. `none` разрешён здесь для
локального почтового теста. Ошибка доставки логируется без адреса, ссылки или
секретов; HTTP-ответ восстановления одинаков для существующего и неизвестного email.

## Контракт и защита

- `GET /auth/session`: создаёт/читает серверную сессию, возвращает пользователя
  и CSRF-токен. Токен сессии доступен только в HttpOnly cookie; в БД хранится SHA-256.
- Любой изменяющий запрос требует `X-CSRF-Token`, совпадающий с токеном сессии.
  Переданный Origin должен входить в точный allowlist. CORS разрешает credentials
  только выбранным origins. CSRF-токен React хранит в памяти, не в localStorage.
- `POST /auth/register`: email, password (12–128 символов), display_name.
  Email нормализуется и уникален. Пароль — Argon2id (64 MiB, 3 прохода).
- `POST /auth/login`: email/password; сессия и CSRF-токен ротируются.
- `POST /auth/logout`: удаляет сессию из БД и cookie; повтор старой cookie не работает.
- `GET/PATCH /auth/profile`: email и имя; изменяется display_name. Email остаётся
  идентификатором входа, его изменение в этой версии не предлагается.
- `POST /auth/password`: old_password/password. Проверяет старый пароль и
  отзывает все сессии и ссылки восстановления пользователя.
- `POST /auth/forgot-password`: email; отправляет случайную ссылку на 30 минут.
  В БД только хеш токена, новое письмо отменяет предыдущие ссылки.
- `POST /auth/reset-password`: token/password. Одноразовое применение и смена
  пароля транзакционны, блокировка пользователя защищает от конкурентного повтора.
  Все его сессии отзываются. Токен в fragment URL не попадает в HTTP access logs.
- Авторизационные попытки ограничиваются счётчиками PostgreSQL на IP/action:
  20 за 15 минут, восстановление — 5. Не доверяем произвольному X-Forwarded-For.
  Внешний reverse proxy должен корректно передавать доверенный client address.
- Ответы private API не кешируются, referrer выключен. Ошибки валидации не
  возвращают введённые пароли, ошибки БД не раскрывают connection string.

`002_users_and_ownership.sql` добавляет users, sessions, password_resets,
auth_limits, external_identities и nullable owner_id у matches. `001` неизменна.
Старые owner_id=NULL не показываются никому и не присваиваются автоматически.
Новые API-загрузки получают владельца из сессии. Все списки/чтения фильтруются по
owner_id в SQL; повторный анализ проверяет владельца до чтения файла.
Чужой UUID возвращает 404. Формат JSON-результатов сохранён.

`external_identities(provider, subject, user_id)` позволяет позднее привязать
FACEIT ID и SteamID без изменения локального user UUID. Сейчас OAuth-маршрутов,
FACEIT Connect, привязки через UI и автоматического импорта нет.

## Повторение проверок

Только отдельный PostgreSQL и явно заданный `WATCHDEMO_TEST_DATABASE_URL`.
Никогда не используется fallback на рабочую базу. Каждый тест создаёт собственную
схему watchdemo_test_UUID и удаляет только её. При ограниченном TEMP Windows
направьте TEMP/TMP в каталог своего worktree.

```powershell
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```

Без TEST URL интеграционные тесты **пропускаются**, а не считаются успешными.
Тест `test_saved_result_survives_actual_server_process_restart` запускает отдельный
Uvicorn, останавливает его, запускает снова, повторно входит и сравнивает результат.
Тесты accounts проверяют реальный PostgreSQL и SMTP, CSRF, роли A/B, logout,
изменение пароля, одноразовый reset/expiry и безопасные ошибки.

Дополнительные проверки из backend (PYTHONPATH должен включать backend):

```powershell
# В корне repo: npm install --prefix .test-tools playwright
python scripts/qa_browser_accounts.py
python scripts/qa_real_demo_accounts.py 'C:\path\to\match.dem'
```

Browser QA требует системный Chrome, свободные localhost:8000/5173, npm ci в
frontend и тестовые зависимости Python. Запускает только собственные тестовые
процессы и чистит свою схему. Реальный demo QA читает исходник, проверяет его SHA,
анализирует временную копию и повторно читает отчёт после удаления копии и нового
старта приложения. Это отдельные smoke-проверки, не дополнительные unittest-кейсы.

## Ограничения

Нет верификации email, MFA, изменения email, админского присвоения старых записей,
автоочистки истёкших сессий/лимитов и успешных временных demo. Требуется политика
retention перед публичным развёртыванием. Сессии имеют фиксированный срок 7 дней.
Синхронный анализ и существующие ограничения геометрии/детекторов сохранены.
Восстановление зависит от настроенного SMTP; фоновая отправка не является durable
очередью писем. Нет JSON-экспорта через интерфейс и FACEIT OAuth/import.

Использованные рекомендации: [OWASP CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html),
[OWASP Forgot Password](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).

## Функциональные требования final_application.md

| № | Требование | Состояние в этой ветке |
|---|---|---|
| 1 | Аккаунт, профиль, пароль, старые результаты | Реализовано этой задачей; email не редактируется |
| 2 | Загрузка .dem | Существующий API/UI сохранён, добавлен владелец |
| 3 | Проверка входного файла | Существующая проверка сохранена, ошибки тестируются |
| 4 | Извлечение событий матча | Существующий анализатор; не изменён |
| 5 | Выбор игрока | Существующий UI/API сохранён |
| 6 | K/D, ADR, entry и прочие метрики | Частично: K/D/entry есть, ADR не реализовывался этой задачей |
| 7 | Интерактивный радар | Существующий; логика не изменялась |
| 8 | Timeline и переход к раунду/моменту | Существующее; логика не изменялась |
| 9 | 3–5 типов игровых проблем | Существующие правила; качество и покрытие этой задачей не переоценивались |
| 10 | Список наиболее значимых проблем | Существующий Summary/top_problems |
| 11 | Объяснение проблемы и переход на радар | Частично: Timeline умеет переходы по событиям; секция Key situations ещё placeholder |
| 12 | БД и повторное открытие | Реализовано, добавлены владение и авторизация |
| 13 | JSON-экспорт | Формат результата есть; пользовательский экспорт не реализован |

Эта таблица не объявляет весь ИВР завершённым: перечисленные пробелы №6, №11,
№13 остаются вне изменения аккаунтов и хранения.
