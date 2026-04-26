# 🦁 DarajaAI — M-Pesa Transaction Intelligence

> AI-powered fraud signals, anomaly detection, and payment analytics for Safaricom Daraja v3. Give any AI agent the ability to analyse M-Pesa transaction patterns, detect outliers, and surface payment intelligence.

[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green)](https://modelcontextprotocol.io)
[![Streamlit](https://img.shields.io/badge/Streamlit-Live-red)](https://darajaniai.streamlit.app)
[![PyPI](https://img.shields.io/badge/PyPI-daraja--ai-orange)](https://pypi.org/project/daraja-ai/)

## What it does

DarajaAI adds an intelligence layer on top of raw M-Pesa Daraja v3 transaction data.

| Capability | Description |
|-----------|-------------|
| 🚨 **Fraud signals** | Velocity checks, duplicate detection, off-hours anomalies, round-number patterns |
| 📊 **Payment analytics** | Daily/weekly volume trends, peak hours, paybill vs till breakdown |
| 🔍 **Customer profiling** | Spend patterns, frequency, average transaction size, dormancy detection |
| 💬 **Natural language queries** | Ask "Which paybills had unusual spikes last week?" in plain text |
| 🤖 **MCP server** | Expose analytics as MCP tools for Claude, GPT, or any AI agent |

## Why this exists

Every East African fintech, SACCO, chama, microfinance, and NGO processing M-Pesa transactions is flying blind after the payment completes. Daraja tells you *if* money moved. DarajaAI tells you *what it means*.

## Quickstart

```bash
pip install daraja-ai
```

```python
from daraja_ai import TransactionAnalyser

analyser = TransactionAnalyser()
analyser.load_csv("transactions.csv")

# Fraud signals
signals = analyser.fraud_signals()
print(signals.high_risk)

# Natural language query
result = analyser.ask("Which customers sent more than KES 50,000 in a single day last week?")
print(result)
```

## MCP server

```json
{
  "mcpServers": {
    "daraja-ai": {
      "command": "uvx",
      "args": ["daraja-ai"],
      "env": {
        "ANTHROPIC_API_KEY": "your_key",
        "TRANSACTION_CSV": "/path/to/transactions.csv"
      }
    }
  }
}
```

**MCP tools exposed:**
- `analyse_transactions` — full fraud + analytics pass on a CSV
- `detect_anomalies` — statistical outlier detection on transaction values
- `get_velocity_alerts` — flag customers exceeding velocity thresholds
- `query_transactions` — natural language query over transaction history

## Streamlit app

Live at [daraja-ai.streamlit.app](https://darajaniai.streamlit.app) — upload a Daraja CSV export and get an AI-powered analytics report in under 60 seconds.

## Related

- [mpesa-mcp](https://github.com/gabrielmahia/mpesa-mcp) — M-Pesa MCP server (3,000+ downloads) — *trigger* M-Pesa payments
- **DarajaAI** — *analyse* M-Pesa transaction data
- [Hesabu](https://darajaniai.streamlit.app) — County budget execution (public sector M-Pesa data)

Together: `mpesa-mcp` sends money → `daraja-ai` analyses what happened.

## Data privacy

DarajaAI runs entirely locally or on your own server. No transaction data leaves your environment. The LLM receives only aggregated statistics, never raw phone numbers or account identifiers.

## IP & Collaboration

© 2026 Gabriel Mahia · [contact@aikungfu.dev](mailto:contact@aikungfu.dev)
License: CC BY-NC-ND 4.0
Not affiliated with Safaricom or M-Pesa Africa.
