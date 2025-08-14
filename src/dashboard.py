# --- make project root importable (so `from src.*` works) ---
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from src.llm import llm_narrative
import yaml, os
with open(os.path.join(ROOT,"config","config.yaml"),"r") as f:
    APP_CONFIG = yaml.safe_load(f)

import streamlit as st
import pandas as pd
import yaml
from pathlib import Path
from io import StringIO

from src.analyze import analyze_month
from src.insights import generate_insights

# ----------------------------- config & data loaders -----------------------------

# Load config
with open(os.path.join(ROOT, "config", "config.yaml"), "r") as f:
    CONFIG = yaml.safe_load(f)

DATA_PATH = Path(CONFIG["data"].get("cleaned_transactions_path", "data/cleaned_transactions.parquet"))

@st.cache_data
def load_cleaned_transactions() -> pd.DataFrame:
    """Load cleaned parquet from disk and ensure types."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"{DATA_PATH} not found. Run `python src/ingest.py` first.")
    df = pd.read_parquet(DATA_PATH)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df.dropna(subset=["Date"])

def month_options(df: pd.DataFrame):
    return (
        df["Date"].dt.to_period("M").astype(str).sort_values().unique().tolist()
    )

# ----------------------------------- app -----------------------------------

def main():
    st.set_page_config(page_title="AutoAdvisor Dashboard", page_icon="📊", layout="wide")
    st.title("📊 AutoAdvisor — Personal Finance & Investment (MVP)")
    st.caption("Interactive view of your monthly spend, income, savings, categories, and insights.")

    # Load data
    df = load_cleaned_transactions()

    # Sidebar
    st.sidebar.header("Filters")
    months = month_options(df)
    if not months:
        st.warning("No months found in data.")
        st.stop()
    default_idx = len(months) - 1
    month = st.sidebar.selectbox("Month (YYYY-MM)", options=months, index=default_idx)
    st.sidebar.write("Data file:", f"`{DATA_PATH.as_posix()}`")

    # Analyze selected month
    metrics = analyze_month(df=df, month=month)
    insights = generate_insights(metrics)

    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Income", f"${metrics['income_total']:.2f}")
    c2.metric("Expenses", f"${abs(metrics['expense_total']):.2f}")
    c3.metric("Net", f"${metrics['net']:.2f}")
    c4.metric("Savings Rate", f"{metrics['savings_rate_pct']:.1f}%")

    st.divider()

    # Charts row
    left, right = st.columns(2)

    # Category breakdown (bar)
    with left:
        st.subheader("Category Breakdown (Expenses)")
        cat_df = pd.DataFrame(metrics["category_breakdown"], columns=["Category", "Amount"])
        if cat_df.empty:
            st.info("No expense data for this month.")
        else:
            st.bar_chart(cat_df.set_index("Category"))

    # Cumulative spend over time (line)
    with right:
        st.subheader("Cumulative Spend Over Time")
        period = pd.Period(month, freq="M")
        start = period.to_timestamp()
        end = (period + 1).to_timestamp()
        mdf = df[(df["Date"] >= start) & (df["Date"] < end)].copy()
        if mdf.empty:
            st.info("No transactions in this month.")
        else:
            daily = (
                mdf.assign(Expense=mdf["Amount"].where(mdf["Amount"] < 0, 0))
                   .groupby(mdf["Date"].dt.date)["Expense"]
                   .sum()
                   .abs()
                   .cumsum()
            )
            st.line_chart(pd.DataFrame({"Cumulative Expense": daily}))

    st.divider()

    # Tables: Top categories and spikes
    t1, t2 = st.columns(2)
    with t1:
        st.subheader("Top Categories")
        if metrics["top_categories"]:
            tc = pd.DataFrame(metrics["top_categories"], columns=["Category", "Amount"])
            st.dataframe(tc, hide_index=True)
        else:
            st.write("—")

    with t2:
        st.subheader("Biggest Transactions")
        if metrics["spikes"]:
            sp = pd.DataFrame(metrics["spikes"])
            st.dataframe(sp, hide_index=True)
        else:
            st.write("—")

    st.divider()


    # Insights section
    st.subheader("Insights")

    # Toggle for AI vs rule-based
    use_llm = st.toggle("AI narrative (Hugging Face)", value=False)

    if use_llm and APP_CONFIG.get("ai", {}).get("provider") == "hf":
        with st.spinner("Generating AI narrative..."):
            summary = llm_narrative(metrics)  # <-- Calls our Hugging Face integration
        st.write(summary)
    else:
        for line in insights:  # <-- insights is the list from generate_insights()
            st.write(f"• {line}")


    # Transactions table (with filters)
    st.divider()
    st.subheader("Transactions (Selected Month)")

    df_all = df  # already loaded
    period = pd.Period(month, freq="M")
    start = period.to_timestamp()
    end = (period + 1).to_timestamp()
    tx = df_all[(df_all["Date"] >= start) & (df_all["Date"] < end)].copy()

    cats = sorted(tx["Category"].dropna().unique().tolist())
    sel = st.multiselect("Filter by category", options=cats, default=cats)
    if sel:
        tx = tx[tx["Category"].isin(sel)]

    st.dataframe(
        tx.sort_values("Date")[["Date", "Description", "Category", "Amount", "Type", "Account"]]
          .reset_index(drop=True),
        hide_index=True
    )

    

    # Export as text
    st.divider()
    st.subheader("Export")
    report = StringIO()
    report.write(f"AutoAdvisor Monthly Summary — {metrics['period']}\n")
    report.write(f"Income: ${metrics['income_total']:.2f}\n")
    report.write(f"Expenses: ${abs(metrics['expense_total']):.2f}\n")
    report.write(f"Net: ${metrics['net']:.2f}\n")
    report.write(f"Savings Rate: {metrics['savings_rate_pct']:.1f}%\n\n")
    report.write("Top Categories:\n")
    for c, a in metrics["top_categories"]:
        report.write(f"- {c}: ${a:.2f}\n")
    report.write("\nInsights:\n")
    for line in insights:
        report.write(f"- {line}\n")

    st.download_button(
        "Download monthly report (.txt)",
        data=report.getvalue().encode("utf-8"),
        file_name=f"AutoAdvisor_{metrics['period']}.txt",
        mime="text/plain",
    )

if __name__ == "__main__":
    main()
