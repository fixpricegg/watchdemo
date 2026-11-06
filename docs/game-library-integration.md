# Объединение ИВР с основной рабочей веткой

6 ноября 2026: feature/game-library обновлена fast-forward с 0a3dbdc до 464c581 из integration/ivr-2026-11-05. Все коммиты PostgreSQL, аккаунтов, ADR, детекторов, Match Library, радара и React сохранены.

Перед объединением создан Git stash «Preserve primary WatchDemo before IVR integration» и файловая резервная копия в C:/Users/petko/OneDrive/Документы/ChatGPT/WatchDemo CS2/merge-backup. Stash оставлен. Девять локальных неотслеживаемых файлов восстановлены побайтово и оставлены неотслеживаемыми. Исходники C4 Extractor совпали с интеграционными и теперь отслеживаются Git; оба локальных бинарных файла сохранились и совпадают с SHA256SUMS.txt.

В общий код перенесена локальная настройка coordinate_space="source2_raw" при загрузке collision geometry, а demo_script сохраняет существовавший путь demos/match20nuke.dem. Файл демки существует.

Локальное окружение основной папки: backend/venv. Недостающие зависимости установлены из backend/requirements-test.txt. PostgreSQL проверена в отдельном тестовом кластере и частных схемах, рабочие базы не изменялись.

Проверки после объединения: 376 backend-тестов, 0 падений, 0 пропусков; 3 frontend-теста; полный ESLint; React production build; совместный импорт backend-модулей и запуск C4 Extractor. Все прошли.

Дополнительные ограничения аналитики из docs/ivr-integration-verification.md сохраняются: кандидаты не являются доказанными игровыми ошибками. Иные worktree и ветка main не менялись. Разрешена публикация только feature/game-library.
