"""
DarajaAI — M-Pesa transaction intelligence engine.
"""
import os
import json
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta


@dataclass
class FraudSignal:
    severity: str          # HIGH / MEDIUM / LOW
    signal_type: str
    description: str
    affected_rows: int
    sample: list = field(default_factory=list)


@dataclass
class FraudReport:
    high_risk:   list[FraudSignal] = field(default_factory=list)
    medium_risk: list[FraudSignal] = field(default_factory=list)
    low_risk:    list[FraudSignal] = field(default_factory=list)
    total_signals: int = 0
    analysed_rows: int = 0

    def summary(self) -> str:
        lines = [
            f"DarajaAI Fraud Signal Report",
            f"Transactions analysed: {self.analysed_rows:,}",
            f"Signals found: {self.total_signals} ({len(self.high_risk)} HIGH, "
            f"{len(self.medium_risk)} MEDIUM, {len(self.low_risk)} LOW)",
        ]
        for s in self.high_risk:
            lines.append(f"  🔴 HIGH  [{s.signal_type}] {s.description} ({s.affected_rows} rows)")
        for s in self.medium_risk:
            lines.append(f"  🟡 MED   [{s.signal_type}] {s.description} ({s.affected_rows} rows)")
        for s in self.low_risk:
            lines.append(f"  🟢 LOW   [{s.signal_type}] {s.description} ({s.affected_rows} rows)")
        return "\n".join(lines)


class TransactionAnalyser:
    """
    Core analytics engine for M-Pesa Daraja transaction exports.
    
    Expects a CSV with columns (flexible — auto-detects):
      TransactionID, Timestamp, Amount, PhoneNumber, TransactionType,
      AccountNumber (paybill/till), Status
    """

    REQUIRED_COLS = {"amount", "timestamp"}
    ROUND_NUMBER_THRESHOLD = 0.40  # flag if >40% of transactions are round numbers
    VELOCITY_DAILY_KES = 300_000   # flag customers sending >KES 300K/day
    DUPLICATE_WINDOW_MINS = 5      # same phone+amount within 5 mins = likely duplicate

    def __init__(self):
        self.df: pd.DataFrame | None = None

    def load_csv(self, path: str | Path) -> "TransactionAnalyser":
        df = pd.read_csv(path)
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
        # Normalise column names
        for alias, canonical in [
            ("transactionid", "transaction_id"),
            ("phonenumber", "phone"),
            ("msisdn", "phone"),
            ("transactiontype", "tx_type"),
            ("accountnumber", "account"),
            ("amount_kes", "amount"),
        ]:
            if alias in df.columns and canonical not in df.columns:
                df.rename(columns={alias: canonical}, inplace=True)
        # Parse timestamp
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        self.df = df
        return self

    def load_dataframe(self, df: pd.DataFrame) -> "TransactionAnalyser":
        self.df = df.copy()
        return self

    def fraud_signals(self) -> FraudReport:
        if self.df is None:
            raise ValueError("Load data first with load_csv() or load_dataframe()")
        df = self.df
        report = FraudReport(analysed_rows=len(df))

        # 1. Duplicate transactions (same phone + amount within window)
        if "phone" in df.columns and "timestamp" in df.columns:
            df_sorted = df.sort_values("timestamp")
            df_sorted["prev_ts"] = df_sorted.groupby("phone")["timestamp"].shift(1)
            df_sorted["prev_amount"] = df_sorted.groupby("phone")["amount"].shift(1)
            df_sorted["time_diff_min"] = (
                df_sorted["timestamp"] - df_sorted["prev_ts"]
            ).dt.total_seconds() / 60
            dupes = df_sorted[
                (df_sorted["time_diff_min"] < self.DUPLICATE_WINDOW_MINS) &
                (df_sorted["amount"] == df_sorted["prev_amount"])
            ]
            if len(dupes) > 0:
                report.high_risk.append(FraudSignal(
                    severity="HIGH", signal_type="DUPLICATE",
                    description=f"Potential duplicate transactions within {self.DUPLICATE_WINDOW_MINS}-min window",
                    affected_rows=len(dupes),
                    sample=dupes.head(3).to_dict("records"),
                ))

        # 2. Velocity alerts (daily spend per customer)
        if "phone" in df.columns and "timestamp" in df.columns:
            df["date"] = df["timestamp"].dt.date
            daily = df.groupby(["phone", "date"])["amount"].sum().reset_index()
            high_vel = daily[daily["amount"] > self.VELOCITY_DAILY_KES]
            if len(high_vel) > 0:
                report.high_risk.append(FraudSignal(
                    severity="HIGH", signal_type="VELOCITY",
                    description=f"Daily spend > KES {self.VELOCITY_DAILY_KES:,} for {daily['phone'].nunique()} customers",
                    affected_rows=len(high_vel),
                    sample=high_vel.head(3).to_dict("records"),
                ))

        # 3. Off-hours transactions (11pm–5am)
        if "timestamp" in df.columns:
            df["hour"] = df["timestamp"].dt.hour
            off_hours = df[(df["hour"] >= 23) | (df["hour"] < 5)]
            pct = len(off_hours) / len(df)
            if pct > 0.05:  # >5% off-hours
                report.medium_risk.append(FraudSignal(
                    severity="MEDIUM", signal_type="OFF_HOURS",
                    description=f"{pct:.0%} of transactions occurred 11pm–5am",
                    affected_rows=len(off_hours),
                ))

        # 4. Round number patterns
        if "amount" in df.columns:
            round_mask = df["amount"] % 100 == 0
            pct_round = round_mask.sum() / len(df)
            if pct_round > self.ROUND_NUMBER_THRESHOLD:
                report.medium_risk.append(FraudSignal(
                    severity="MEDIUM", signal_type="ROUND_NUMBERS",
                    description=f"{pct_round:.0%} of transactions are round numbers (>= KES multiples of 100)",
                    affected_rows=int(round_mask.sum()),
                ))

        # 5. Statistical outliers in transaction amounts (IQR method)
        if "amount" in df.columns and len(df) > 20:
            Q1 = df["amount"].quantile(0.25)
            Q3 = df["amount"].quantile(0.75)
            IQR = Q3 - Q1
            outliers = df[(df["amount"] < Q1 - 3 * IQR) | (df["amount"] > Q3 + 3 * IQR)]
            if len(outliers) > 0:
                report.low_risk.append(FraudSignal(
                    severity="LOW", signal_type="OUTLIER_AMOUNT",
                    description=f"{len(outliers)} transactions are statistical outliers (3× IQR from median)",
                    affected_rows=len(outliers),
                    sample=outliers.nlargest(3, "amount").to_dict("records"),
                ))

        report.total_signals = len(report.high_risk) + len(report.medium_risk) + len(report.low_risk)
        return report

    def analytics_summary(self) -> dict:
        """Return a structured analytics summary suitable for display or LLM context."""
        if self.df is None:
            return {}
        df = self.df
        summary = {
            "total_transactions": len(df),
            "total_volume_kes": float(df["amount"].sum()) if "amount" in df.columns else 0,
            "avg_transaction_kes": float(df["amount"].mean()) if "amount" in df.columns else 0,
            "max_transaction_kes": float(df["amount"].max()) if "amount" in df.columns else 0,
            "unique_customers": int(df["phone"].nunique()) if "phone" in df.columns else 0,
        }
        if "timestamp" in df.columns:
            summary["date_range"] = {
                "from": str(df["timestamp"].min()),
                "to":   str(df["timestamp"].max()),
            }
            df["hour"] = df["timestamp"].dt.hour
            peak_hour = int(df["hour"].mode()[0])
            summary["peak_hour"] = peak_hour
        if "tx_type" in df.columns:
            summary["by_type"] = df.groupby("tx_type")["amount"].agg(["count", "sum"]).to_dict()
        return summary

    def ask(self, question: str, api_key: str = "") -> str:
        """Natural language query over transaction data. Uses Gemini or Anthropic via llm_router."""
        import sys, os as _os
        sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
        from llm_router import ask as _ask
        summary = self.analytics_summary()
        fraud   = self.fraud_signals().summary()
        system  = "You are a financial analyst reviewing M-Pesa transaction data. Answer concisely with KES figures."
        prompt  = (
            f"Transaction summary:\n{json.dumps(summary, indent=2)}\n\n"
            f"Fraud signals:\n{fraud}\n\n"
            f"Question: {question}"
        )
        return _ask(prompt, system=system, user_key=api_key)
