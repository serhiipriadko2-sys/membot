# Changelog

Все значимые изменения в проекте membot будут документироваться в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Добавлено
- Синтетические данные для тестирования (`scripts/_generate_synthetic_data.py`)
- Матрица статусов гипотез (`docs/HYPOTHESIS_STATUS_MATRIX.md`)
- GitHub Actions workflow для nightly тестов Observer Gate
- Pre-commit хуки для форматирования, линтинга и безопасности
- Шаблоны для issue (bug report, data quality, documentation gap, hypothesis proposal)
- Шаблон для pull requests
- Makefile с 25+ командами для управления проектом
- `.editorconfig` для единообразия кода

### Изменено
- Расширено тестовое покрытие для граничных случаев
- Централизована конфигурация через Makefile
- Улучшена документация архитектуры и устранения неполадок

### Исправлено
- Восстановлен конвейер данных с генерацией CSV-файлов
- Автоматизирован Observer Gate через GitHub Actions

## [0.1.0] - 2026-05-27

### Добавлено
- Начальная версия проекта membot
- Исследовательский пайплайн для анализа мем-коинов на Solana
- Fast10 detector и observer для микро-альфа стратегий
- Система триггеров для entry/exit сигналов
- Бэктестинг фреймворк
- Интеграция с Dune Analytics для market context
- Интеграция с Supabase для хранения данных
- RPC health checking и backoff логика
- Security scan и audit скрипты
- Agent CI smoke tests

### Техническое
- Python 3.11+
- Pandas для обработки данных
- Pytest для тестирования
- Black, flake8, mypy для код-качества
- GitHub Actions для CI/CD
