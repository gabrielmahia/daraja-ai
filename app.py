"""DarajaAI Streamlit app — upload CSV, get AI analytics."""
import streamlit as st
import pandas as pd
import plotly.express as px
import io, os
from daraja_ai import TransactionAnalyser

st.set_page_config(page_title="DarajaAI", page_icon="🦁", layout="wide")
st.title("🦁 DarajaAI — M-Pesa Transaction Intelligence")
st.caption("Upload a Daraja transaction export. Get fraud signals and analytics in under 60 seconds.")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Anthropic API key (optional — for NL queries):",
                             type="password", value=os.getenv("ANTHROPIC_API_KEY",""))
    st.divider()
    st.caption("Data stays local — no transactions are sent externally.")
    st.caption("[mpesa-mcp](https://github.com/gabrielmahia/mpesa-mcp) · [GitHub](https://github.com/gabrielmahia/daraja-ai)")

uploaded = st.file_uploader("Upload Daraja CSV export", type=["csv"])

SAMPLE_CSV = """TransactionID,Timestamp,Amount,PhoneNumber,TransactionType,AccountNumber,Status
TX001,2024-03-01 09:15:00,5000,254712345678,PayBill,123456,Completed
TX002,2024-03-01 09:17:00,5000,254712345678,PayBill,123456,Completed
TX003,2024-03-01 14:22:00,1500,254723456789,Till,678901,Completed
TX004,2024-03-01 02:05:00,50000,254734567890,B2C,None,Completed
TX005,2024-03-02 10:00:00,10000,254745678901,PayBill,123456,Completed
TX006,2024-03-02 10:00:00,200000,254756789012,PayBill,999999,Completed
TX007,2024-03-02 23:45:00,300,254767890123,Till,678901,Completed
TX008,2024-03-03 08:30:00,2500,254712345678,PayBill,123456,Completed
TX009,2024-03-03 08:31:00,2500,254712345678,PayBill,123456,Completed
TX010,2024-03-03 16:00:00,100000,254778901234,B2C,None,Completed
"""

if st.button("Use sample data", type="secondary"):
    uploaded = io.StringIO(SAMPLE_CSV)

if uploaded:
    analyser = TransactionAnalyser()
    df = pd.read_csv(uploaded if isinstance(uploaded, io.StringIO) else uploaded)
    analyser.load_dataframe(df)

    col1, col2, col3, col4 = st.columns(4)
    summary = analyser.analytics_summary()
    col1.metric("Transactions", f"{summary.get('total_transactions',0):,}")
    col2.metric("Total Volume", f"KES {summary.get('total_volume_kes',0):,.0f}")
    col3.metric("Avg Transaction", f"KES {summary.get('avg_transaction_kes',0):,.0f}")
    col4.metric("Customers", f"{summary.get('unique_customers',0):,}")

    tab1, tab2, tab3 = st.tabs(["🚨 Fraud Signals", "📊 Analytics", "💬 Ask AI"])

    with tab1:
        report = analyser.fraud_signals()
        if report.total_signals == 0:
            st.success("No fraud signals detected.")
        else:
            st.warning(f"{report.total_signals} signals found — {len(report.high_risk)} HIGH risk")
            for s in report.high_risk:
                st.error(f"🔴 **{s.signal_type}** — {s.description} ({s.affected_rows} transactions)")
            for s in report.medium_risk:
                st.warning(f"🟡 **{s.signal_type}** — {s.description} ({s.affected_rows} transactions)")
            for s in report.low_risk:
                st.info(f"🟢 **{s.signal_type}** — {s.description} ({s.affected_rows} transactions)")

    with tab2:
        if "amount" in df.columns and "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df["date"] = df["timestamp"].dt.date
            daily = df.groupby("date")["amount"].sum().reset_index()
            fig = px.bar(daily, x="date", y="amount",
                         title="Daily Transaction Volume (KES)",
                         labels={"amount":"KES","date":"Date"},
                         color_discrete_sequence=["#00A86B"])
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        if not api_key:
            st.info("Add an Anthropic API key in the sidebar to enable natural language queries.")
        else:
            q = st.text_input("Ask a question about this transaction data:")
            if q:
                with st.spinner("Analysing..."):
                    ans = analyser.ask(q, api_key=api_key)
                st.write(ans)

st.divider()
st.caption("© 2026 Gabriel Mahia · CC BY-NC-ND 4.0 · contact@aikungfu.dev")
