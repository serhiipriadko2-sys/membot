# Onboarding and agent layer

## Problem
The app has many specialized terms: raw, signature, FIFO, PnL, Jito, priority fee, trigger, coverage, SoT, verdict. New users can see charts but not understand what each term means or what action is safe.

## Decision
Add an in-app onboarding and agent layer inside Iskra Forge, not as another top-level Streamlit page.

## UI additions

### Mini term hints
Terms can be rendered with a small translucent `?` marker.
Clicking it opens a compact explanation:
- simple meaning
- why it matters in this project

Implementation uses HTML `<details>` blocks rendered through Streamlit markdown. This avoids adding a new dependency and works inside existing text/cards.

### Guide/Agent tab
A new internal tab is added inside Iskra Forge:
- onboarding cards
- FAQ
- glossary search
- agent chat
- agent architecture expander

## Agentic layer v1
This is a read-only, deterministic agent layer. It does not call external LLM APIs yet.

Agents/modes:
- Onboarding Agent — explains terms and flow
- Data QA Agent — checks artifact readiness and missing critical files
- Fee/Jito Agent — explains fee/Jito/ComputeBudget state
- Trigger Agent — explains trigger hypotheses and why PASS is not BUY
- Verdict Guard — keeps claims at UNKNOWN/PARTIAL when evidence is weak

## Boundaries
- No BUY/SELL output
- No secret storage
- No wallet private keys
- No mutation of Supabase or GitHub from the chat agent
- Memory is only Streamlit `session_state` in v1

## Why not full autonomous trading agent?
Because the project goal is forensic/reverse-engineering. Agentic UI can help read and verify evidence, but it must not become an execution layer.

## Future v2
- Optional OpenAI/Agents SDK mode behind explicit environment flag
- AgentMemory recall for past run explanations, still below repo/artifacts in Truth Ladder
- Tool registry with read-only tools:
  - summarize_artifacts
  - explain_term
  - inspect_fee_jito
  - inspect_green_days
  - propose_next_run
- Persistent run notes in Supabase, never secrets

## QA
PASS if:
- Guide/Agent tab opens
- FAQ expanders open
- glossary search filters terms
- terms with `?` reveal simple explanations
- chat agent responds to:
  - `что дальше?`
  - `объясни FIFO`
  - `почему daily PnL UNKNOWN?`
  - `проверь fee/Jito`
- no new top-level sidebar noise appears
