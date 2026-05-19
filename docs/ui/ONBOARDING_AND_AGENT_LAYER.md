# Онбординг и агентурный слой

## Проблема

В приложении много специальных терминов: raw, signature, FIFO, PnL, Jito, priority fee, trigger, coverage, SoT, verdict, cluster_context, repeat_wave, price_action, cross_chain_regime.

Если пользователь видит график, но не понимает термин, график превращается в шум. Если пользователь видит PASS и воспринимает это как BUY, это уже риск.

## Решение

Основной пользовательский слой приложения должен быть на русском языке.

Онбординг встроен внутрь Iskra Forge как вкладка `Гайд / Агент`, а не как новая верхнеуровневая Streamlit page.

## UI

### Мини-подсказки

Термины получают маленький полупрозрачный значок `?`.
При клике раскрывается карточка:
- название термина;
- простое объяснение;
- зачем термин нужен в membot.

Подсказка должна быть читаемой: светлый заголовок, контрастный body text, тёплая строка `why`, высокий z-index.

### Вкладки

- `Кузница сигналов` — главный обзор.
- `Гайд / Агент` — FAQ, словарь, агент.
- `Raw` — сырые swaps/transaction-derived rows.
- `FIFO` — paired trades и учёт входов/выходов.
- `PnL по дням` — календарь прибыли/убытка.
- `Fee/Jito` — priority fee, ComputeBudget, Jito evidence.
- `Триггеры` — pre-buy и entry/exit hypotheses.
- `Отчёты` — markdown reports.
- `Загрузка` — upload артефактов.

## Термины, которые должны быть в словаре

- `cluster_context` — окружение токена, соседние сделки, похожие кошельки, режим рынка.
- `repeat_wave` — повторная волна похожей активности.
- `price_action` — поведение цены до и после входа.
- `cross_chain_regime` — режим, где импульс может прийти из другой сети или рынка.
- `Entry/exit hypotheses` — проверяемые предположения входа и выхода.

## Агентурный слой v2

Агент изучает, анализирует, учится на прогонах, оценивает вероятность поддержки гипотезы, уведомляет о рисках, собирает информацию и предлагает следующий research-step.

Он не выдаёт финансовую рекомендацию, не отдаёт BUY/SELL и всегда показывает риск и цену ошибки.

### Read-only tools

- `summarize_artifacts` — сводка доступных артефактов и строк.
- `explain_term` — объяснение термина из словаря.
- `inspect_fee_jito` — Fee/Jito/ComputeBudget разбор.
- `inspect_green_days` — проверка готовности green-days claim.
- `estimate_hypothesis_support` — вероятность поддержки гипотезы без BUY/SELL.
- `risk_price_explainer` — риск и цена ошибки.
- `propose_next_run` — следующий безопасный run-step.

## Boundary formula

```text
Агент оценивает вероятность и риск.
Агент не отдаёт приказ.
Raw artifacts остаются выше agent output.
```

## QA

PASS если:
- интерфейсные вкладки на русском;
- hero на русском;
- `?` подсказки читаемые;
- `cluster_context`, `repeat_wave`, `price_action`, `cross_chain_regime`, `Entry/exit hypotheses` есть в словаре;
- `Гайд / Агент` открывается;
- FAQ раскрывается;
- glossary search фильтрует термины;
- агент отвечает на:
  - `что дальше?`
  - `объясни FIFO`
  - `проверь fee/Jito`
  - `почему daily PnL UNKNOWN?`
  - `какой риск у trigger?`
  - `какие инструменты есть?`
- агент не выдаёт BUY/SELL;
- sidebar не получает новых top-level pages.

## Future

- Optional OpenAI/Agents SDK mode behind env flag.
- AgentMemory recall ниже repo/artifacts в Truth Ladder.
- Persistent run notes в Supabase без секретов.
- Уведомления только как риск/изменение состояния, не как торговая команда.
