# AGENTS.md — DarajaAI

M-Pesa transaction intelligence.

## Files
- `src/daraja_ai/analyser.py` — TransactionAnalyser (fraud, velocity, outliers, NLP)
- `src/daraja_ai/server.py` — MCP server (4 tools)
- `app.py` — Streamlit UI

## Rules
- Never fabricate transaction data
- Anonymise phone numbers in LLM context
- ANTHROPIC_API_KEY required for NL query tool only
