# WatchDemo

**WatchDemo** — веб-сервис для разбора демозаписей Counter-Strike 2. Он принимает файл `.dem`, извлекает события матча, показывает статистику, таймлайн и интерактивный 2D-радар, а также помогает находить игровые эпизоды для самостоятельного анализа.

## Где находится версия для итоговой ИВР (ноябрь 2026)

**Код интеграционной версии находится в ветке [`feature/game-library`](https://github.com/fixpricegg/watchdemo/tree/feature/game-library).** Ветка `main` содержит более раннее состояние проекта; при проверке итоговой работы **не используйте `main` как финальную сборку**.

Материалы интеграционной версии:
- [Исходный код финальной интеграционной ветки](https://github.com/fixpricegg/watchdemo/tree/feature/game-library)
- [Итоговый отчёт ИВР (.docx)](https://github.com/fixpricegg/watchdemo/blob/feature/game-library/docs/WatchDemo_Final_Report_IVR.docx)
- [Инструкция запуска](https://github.com/fixpricegg/watchdemo/blob/feature/game-library/docs/ivr-runbook.md)
- [Проверки и оставшиеся ограничения](https://github.com/fixpricegg/watchdemo/blob/feature/game-library/docs/ivr-integration-verification.md)
- [Папка демонстрационных материалов](https://drive.google.com/drive/folders/1TfTVa33cGFJFxxLesWFQdYQPqDo6Qadx?usp=drive_link) (наличие записи и доступ по ссылке проверяются отдельно).

## Что реализовано в интеграционной ветке

- Загрузка и валидация файлов `.dem`, получение игровых событий и статистики (в том числе K/D, ADR, первые убийства и смерти).
- Выбор игрока, отчёт, временная шкала, 2D-радар и переход к эпизодам матча.
- Аккаунты и сохранение результатов в PostgreSQL с повторным открытием и экспортом JSON.
- Три типа эпизодов для проверки: **Entry Death**, **Missed Trade v2**, **Buy Mismatch**.
- Контекстный анализ с учётом доступных данных; геометрические проверки на Nuke имеют экспериментальные ограничения.

**Важно:** детекторы находят *кандидатов для разбора*, а не доказывают, что решение игрока было ошибочным. Отсутствие найденных эпизодов не означает отсутствие ошибок. Реальные письма восстановления пароля требуют SMTP. Сервис не заявлен как готовая публичная коммерческая версия.

## Локальный запуск на Windows (PowerShell)

Нужны **Python**, **Node.js/npm**, **PostgreSQL** и Git. Для извлечения некоторых данных о C4 может понадобиться отдельная сборка компонента на Go. Полная инструкция: [docs/ivr-runbook.md](https://github.com/fixpricegg/watchdemo/blob/feature/game-library/docs/ivr-runbook.md).

```powershell
git clone --branch feature/game-library --single-branch https://github.com/fixpricegg/watchdemo.git
cd watchdemo

cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Создайте в PostgreSQL отдельную базу и пользователя с правами на создание схемы. Вместо `USER`, `PASSWORD` и `DATABASE` укажите ваши значения:

```powershell
$env:WATCHDEMO_DATABASE_URL = 'postgresql://USER:PASSWORD@127.0.0.1:5432/DATABASE'
$env:WATCHDEMO_COOKIE_SECURE = 'false' # Только для локального HTTP
.\.venv\Scripts\python.exe manage_storage.py migrate
.\.venv\Scripts\python.exe manage_storage.py check
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Откройте **новое окно PowerShell** в папке `watchdemo/frontend`:

```powershell
npm ci
npm run dev
```

Откройте **http://localhost:5173**, зарегистрируйтесь, войдите в аккаунт, загрузите демозапись CS2, выберите игрока и откройте отчёт. PostgreSQL должен работать до запуска backend.

Файл `backend/.env.example` перечисляет конфигурационные переменные, но **не загружается автоматически**. Не публикуйте реальные пароли. Для проверки геометрии, C4, SMTP и тестов используйте подробный runbook.

## Проверки

Документ [о проверке интеграционной версии](https://github.com/fixpricegg/watchdemo/blob/feature/game-library/docs/ivr-integration-verification.md) фиксирует проведённые разработчиком проверки, в том числе **376 backend-тестов**, сборку React и ESLint, а также тестирование на настоящей демозаписи Nuke. Это отчёт о конкретной проверенной сборке, а не гарантия корректности любой будущей версии. Сначала создайте **отдельную тестовую базу**, затем выполняйте тесты по runbook.

## Дальнейшее развитие

Улучшение надёжности контекстного анализа и уменьшение ложных срабатываний, расширение поддержки карт, настройка публичного развёртывания и проверка востребованности на реальных пользователях.
