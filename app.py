import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

"""DarajaAI — M-Pesa transaction intelligence. Upload a Daraja CSV, get fraud signals."""
import streamlit as st
import pandas as pd

# Graceful optional imports
try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    from daraja_ai import TransactionAnalyser
    HAS_DARAJA = True
except ImportError as e:
    HAS_DARAJA = False
    _import_error = str(e)

st.set_page_config(page_title="DarajaAI", page_icon="🦁", layout="wide")

if not HAS_DARAJA:
    st.error("Setup error — please contact contact@aikungfu.dev")
    st.stop()

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

HAS_AI = HAS_GEMINI or HAS_ANTHROPIC

st.title("🦁 DarajaAI — M-Pesa Transaction Intelligence")
st.caption("Upload a Daraja transaction export. Fraud signals and analytics in under 60 seconds.")

with st.sidebar:
    st.header("Settings")
    ENV_KEY = os.getenv("GEMINI_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")
    if ENV_KEY:
        api_key = ENV_KEY
        st.success("✅ AI queries ready")
    elif HAS_AI:
        st.markdown(
            "**Enable AI queries (optional):**\n\n"
            "Paste a **Gemini API key** (free at [aistudio.google.com](https://aistudio.google.com)) "
            "or an **Anthropic key** (free at [console.anthropic.com](https://console.anthropic.com))."
        )
        api_key = st.text_input(
            "AI key (Gemini or Anthropic):",
            type="password",
            help="Gemini keys start with AIza. Anthropic keys start with sk-ant-. Never stored here."
        )
    else:
        api_key = ""
    st.divider()
    st.caption("🔒 Your data stays local — transactions are never sent externally.")
    st.caption("[GitHub](https://github.com/gabrielmahia/daraja-ai) · © 2026 Gabriel Mahia")

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

import io
col_a, col_b = st.columns([3, 1])
with col_b:
    st.markdown("<br>", unsafe_allow_html=True)
    use_sample = st.button("Use sample data", use_container_width=True)

if use_sample:
    uploaded = io.StringIO(SAMPLE_CSV)

if uploaded:
    try:
        analyser = TransactionAnalyser()
        df = pd.read_csv(uploaded if isinstance(uploaded, io.StringIO) else uploaded)
        analyser.load_dataframe(df)

        summary = analyser.analytics_summary()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Transactions", f"{summary.get('total_transactions',0):,}")
        c2.metric("Total Volume", f"KES {summary.get('total_volume_kes',0):,.0f}")
        c3.metric("Avg Transaction", f"KES {summary.get('avg_transaction_kes',0):,.0f}")
        c4.metric("Customers", f"{summary.get('unique_customers',0):,}")

        tab1, tab2, tab3 = st.tabs(["🚨 Fraud Signals", "📊 Analytics", "💬 Ask AI"])

        with tab1:
            with st.spinner("Analysing transactions..."):
                report = analyser.fraud_signals()
            if report.total_signals == 0:
                st.success("✅ No fraud signals detected in this dataset.")
            else:
                st.warning(f"**{report.total_signals} signal(s) found** — review before proceeding.")
                for s in report.high_risk:
                    st.error(f"🔴 **{s.signal_type}** — {s.description} ({s.affected_rows} transactions)")
                for s in report.medium_risk:
                    st.warning(f"🟡 **{s.signal_type}** — {s.description} ({s.affected_rows} transactions)")
                for s in report.low_risk:
                    st.info(f"🟢 **{s.signal_type}** — {s.description} ({s.affected_rows} transactions)")

        with tab2:
            if HAS_PLOTLY and "amount" in df.columns and "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
                df["date"] = df["timestamp"].dt.date
                daily = df.groupby("date")["amount"].sum().reset_index()
                fig = px.bar(daily, x="date", y="amount",
                             title="Daily Transaction Volume (KES)",
                             labels={"amount": "KES", "date": "Date"},
                             color_discrete_sequence=["#00A86B"])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(df.head(20))

        with tab3:
            if not HAS_ANTHROPIC or not api_key:
                st.info("Add an Anthropic API key in the sidebar to ask questions in plain language.")
                st.caption("Example: *'Which customers sent over KES 50,000 this month?'*")
            else:
                q = st.text_input("Ask a question about this data:")
                if q:
                    with st.spinner("Analysing..."):
                        try:
                            if api_key.startswith("AIza") and HAS_GEMINI:
                                # Gemini path
                                genai.configure(api_key=api_key)
                                model = genai.GenerativeModel("gemini-2.0-flash")
                                summary = analyser.analytics_summary()
                                report  = analyser.fraud_signals().summary()
                                prompt  = f"M-Pesa transaction analytics:\n{summary}\n\nFraud signals:\n{report}\n\nQuestion: {q}\n\nAnswer concisely with KES figures."
                                resp = model.generate_content(prompt)
                                st.write(resp.text)
                            else:
                                # Anthropic path
                                ans = analyser.ask(q, api_key=api_key)
                                st.write(ans)
                        except Exception:
                            st.error("Could not complete that query. Try rephrasing your question.")

    except Exception as e:
        st.error("Could not read the uploaded file. Please check it is a valid Daraja CSV export.")
        st.caption("Expected columns: TransactionID, Timestamp, Amount, PhoneNumber, TransactionType")

st.divider()
st.caption("© 2026 Gabriel Mahia · CC BY-NC-ND 4.0 · contact@aikungfu.dev · Not affiliated with Safaricom")
