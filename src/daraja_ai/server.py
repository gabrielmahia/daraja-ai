"""
DarajaAI MCP server — M-Pesa transaction intelligence as MCP tools.
"""
import os
import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from .analyser import TransactionAnalyser

mcp = FastMCP("daraja-ai")
_analyser = TransactionAnalyser()


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
def analyse_transactions(csv_path: str) -> str:
    """
    Load a Daraja CSV export and run a full fraud + analytics pass.
    Returns fraud signals and summary statistics.
    csv_path: absolute path to the M-Pesa transaction CSV file.
    """
    try:
        _analyser.load_csv(csv_path)
        report  = _analyser.fraud_signals()
        summary = _analyser.analytics_summary()
        return json.dumps({
            "fraud_report": report.summary(),
            "analytics":    summary,
        }, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
def detect_anomalies(csv_path: str) -> str:
    """
    Run statistical outlier detection on M-Pesa transaction amounts.
    Uses IQR method to identify unusual transaction values.
    """
    try:
        _analyser.load_csv(csv_path)
        report = _analyser.fraud_signals()
        outliers = [s for s in report.low_risk if s.signal_type == "OUTLIER_AMOUNT"]
        return json.dumps([
            {"signal": s.signal_type, "description": s.description, "count": s.affected_rows}
            for s in outliers
        ], indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
def get_velocity_alerts(csv_path: str, threshold_kes: int = 300000) -> str:
    """
    Flag customers exceeding daily transaction velocity thresholds.
    threshold_kes: Daily KES limit before flagging (default 300,000).
    """
    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
        df.columns = [c.lower().strip() for c in df.columns]
        df["amount"] = pd.to_numeric(df.get("amount", df.get("amount_kes", 0)), errors="coerce")
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["date"] = df["timestamp"].dt.date
        phone_col = "phone" if "phone" in df.columns else "phonenumber" if "phonenumber" in df.columns else None
        if not phone_col:
            return "No phone/customer column found."
        daily = df.groupby([phone_col, "date"])["amount"].sum().reset_index()
        alerts = daily[daily["amount"] > threshold_kes]
        return alerts.to_json(orient="records", indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
def query_transactions(csv_path: str, question: str) -> str:
    """
    Natural language query over M-Pesa transaction history.
    Requires ANTHROPIC_API_KEY environment variable.
    question: Plain language question e.g. 'Which customers sent over KES 50,000 today?'
    """
    try:
        _analyser.load_csv(csv_path)
        return _analyser.ask(question)
    except Exception as e:
        return f"Error: {e}"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
