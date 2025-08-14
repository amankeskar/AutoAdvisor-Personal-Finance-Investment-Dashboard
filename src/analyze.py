from __future__ import annotations
import pandas as pd
from pathlib import Path
import yaml
from typing import Dict, Any

# Load config once
with open("config/config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

def _ensure_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if "Amount" in df.columns:
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    if "Category" not in df.columns:
        df["Category"] = "Other"
    return df

def _latest_month(df: pd.DataFrame) -> pd.Period:
    if df["Date"].dropna().empty:
        raise ValueError("No valid dates in transactions.")
    return df["Date"].max().to_period("M")

def _slice_month(df: pd.DataFrame, period: pd.Period) -> pd.DataFrame:
    start = period.to_timestamp()
    end = (period + 1).to_timestamp()  # exclusive
    return df[(df["Date"] >= start) & (df["Date"] < end)].copy()

def _money(x: float) -> float:
    """Round to 2 decimals for clean outputs."""
    return float(round(x, 2))

def analyze_month(df: pd.DataFrame | None = None,
                  month: str | None = None) -> Dict[str, Any]:
    """
    Analyze one month of transactions.
    - df: if None, reads parquet from config.data.cleaned_transactions_path
    - month: 'YYYY-MM' (optional). If None, uses latest month in data.
    Returns: dict of metrics.
    """
    if df is None:
        cleaned_path = Path(CONFIG["data"].get("cleaned_transactions_path", "data/cleaned_transactions.parquet"))
        if not cleaned_path.exists():
            raise FileNotFoundError(f"Cleaned parquet not found at {cleaned_path}. Run ingest first.")
        df = pd.read_parquet(cleaned_path)

    df = _ensure_types(df)
    if month is None:
        period = _latest_month(df)
    else:
        period = pd.Period(month, freq="M")

    mdf = _slice_month(df, period)

    # Income (positive) & Expenses (negative)
    income_total = _money(mdf.loc[mdf["Amount"] > 0, "Amount"].sum())
    expense_total = _money(mdf.loc[mdf["Amount"] < 0, "Amount"].sum())  # negative
    net = _money(income_total + expense_total)  # expense_total is negative

    income_abs = income_total
    expense_abs = abs(expense_total)
    savings_rate = _money((net / income_abs * 100) if income_abs else 0.0)

    # Top categories by absolute spend (expenses only)
    cat_series = (
        mdf.loc[mdf["Amount"] < 0]
        .groupby("Category")["Amount"]
        .sum()
        .abs()
        .sort_values(ascending=False)
    )
    top_categories = [(k, _money(v)) for k, v in cat_series.head(5).items()]

    # Biggest expense transactions (spikes)
    if not mdf.empty:
        spikes_df = (
            mdf[mdf["Amount"] < 0]
            .sort_values("Amount")  # most negative first
            .head(5)[["Date", "Description", "Amount", "Category"]]
        )
    else:
        spikes_df = pd.DataFrame(columns=["Date", "Description", "Amount", "Category"])

    spikes = [
        {
            "date": str(r["Date"].date()) if pd.notna(r["Date"]) else None,
            "description": r["Description"],
            "amount": _money(r["Amount"]),
            "category": r["Category"],
        }
        for _, r in spikes_df.iterrows()
    ]

    # Full category breakdown (expenses only) for charts
    category_breakdown = [(k, _money(v)) for k, v in cat_series.items()]

    metrics = {
        "period": str(period),  # 'YYYY-MM'
        "income_total": income_total,
        "expense_total": expense_total,   # negative
        "net": net,
        "savings_rate_pct": savings_rate,
        "top_categories": top_categories,
        "spikes": spikes,
        "category_breakdown": category_breakdown,
        "tx_count": int(len(mdf)),
    }
    return metrics
