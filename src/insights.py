from __future__ import annotations
from typing import Dict, List

def generate_insights(metrics: Dict) -> List[str]:
    msgs = []
    income = metrics.get("income_total", 0.0)
    expense = abs(metrics.get("expense_total", 0.0))
    net = metrics.get("net", 0.0)
    rate = metrics.get("savings_rate_pct", 0.0)
    top_cats = metrics.get("top_categories", [])
    spikes = metrics.get("spikes", [])
    period = metrics.get("period")

    # Savings health
    if income <= 0:
        msgs.append(f"For {period}, no income detected. Check data or add sources.")
    elif rate >= 20:
        msgs.append(f"Great month: savings rate is {rate:.1f}% — above the 20% rule of thumb.")
    elif 10 <= rate < 20:
        msgs.append(f"Savings rate is {rate:.1f}%. Solid, but there’s room to push past 20%.")
    else:
        msgs.append(f"Savings rate is {rate:.1f}%. Consider trimming flexible spend to boost savings.")

    # Expense composition
    if top_cats:
        top_cat, top_amt = top_cats[0]
        share = (top_amt / expense * 100) if expense else 0
        msgs.append(f"Top spend category: {top_cat} (${top_amt:.2f}), ~{share:.1f}% of total expenses.")

    # Spikes
    if spikes:
        s = spikes[0]
        msgs.append(f"Largest transaction: {s['description']} {s['amount']:.2f} on {s['date']} ({s['category']}).")

    # Nudges based on patterns
    if expense > 0 and expense < 0.5 * income:
        msgs.append("Your expenses are under 50% of income — strong cost control.")
    if expense > 0.8 * income:
        msgs.append("Expenses exceed 80% of income — consider a budget review.")

    # Tiny data note
    if metrics.get("tx_count", 0) < 10:
        msgs.append("Limited transactions this month — insights may be noisy. Add more data for better signal.")


    return msgs
