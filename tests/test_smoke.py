"""Smoke tests for daraja-ai."""
import pandas as pd
from daraja_ai import TransactionAnalyser

SAMPLE = pd.DataFrame([
    {"timestamp":"2024-01-01 09:00:00","amount":5000,"phone":"254700000001","tx_type":"PayBill"},
    {"timestamp":"2024-01-01 09:02:00","amount":5000,"phone":"254700000001","tx_type":"PayBill"},
    {"timestamp":"2024-01-01 02:30:00","amount":3000,"phone":"254700000002","tx_type":"Till"},
    {"timestamp":"2024-01-02 10:00:00","amount":500000,"phone":"254700000003","tx_type":"B2C"},
    {"timestamp":"2024-01-02 10:05:00","amount":100,"phone":"254700000004","tx_type":"Till"},
])

def test_load():
    a = TransactionAnalyser().load_dataframe(SAMPLE)
    assert a.df is not None and len(a.df) == 5

def test_fraud_signals():
    a = TransactionAnalyser().load_dataframe(SAMPLE)
    r = a.fraud_signals()
    assert r.analysed_rows == 5
    assert r.total_signals >= 0

def test_analytics_summary():
    a = TransactionAnalyser().load_dataframe(SAMPLE)
    s = a.analytics_summary()
    assert "total_transactions" in s
    assert s["total_volume_kes"] > 0
