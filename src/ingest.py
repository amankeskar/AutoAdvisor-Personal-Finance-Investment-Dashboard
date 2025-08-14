import pandas as pd
import yaml
from pathlib import Path
import re

# Load config
with open("config/config.yaml", "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

REQUIRED = {"date","description","amount","type","account"}

def _read_csv_robust(path: Path) -> pd.DataFrame:
    # Try auto-detect separator, strip BOM
    df = pd.read_csv(
        path,
        sep=None,
        engine="python",
        encoding="utf-8-sig",
        dtype=str  # read as str first, we’ll coerce later
    )
    # Normalize headers
    df.columns = (
        df.columns.str.replace("\ufeff", "", regex=False)  # BOM
                 .str.strip()
                 .str.lower()
    )

    # Map header variants
    rename_map = {
        "date": "date",
        "transaction date": "date",
        "posted date": "date",
        "time": "date",  # last resort

        "description": "description",
        "merchant": "description",
        "details": "description",
        "memo": "description",

        "amount": "amount",
        "amt": "amount",
        "debit": "amount",     # some exports split debit/credit; we’ll handle below
        "credit": "amount",

        "type": "type",
        "transaction type": "type",
        "dr/cr": "type",

        "account": "account",
        "account name": "account",
        "card": "account",
    }
    df = df.rename(columns={c: rename_map.get(c, c) for c in df.columns})

    # If separate debit/credit columns exist, combine
    if "amount" not in df.columns and {"debit","credit"}.issubset(df.columns):
        # Prefer non-null value per row; credit positive, debit negative
        debit = pd.to_numeric(df["debit"].str.replace(",","", regex=False), errors="coerce").fillna(0)
        credit = pd.to_numeric(df["credit"].str.replace(",","", regex=False), errors="coerce").fillna(0)
        df["amount"] = credit - debit

    # Ensure required cols exist
    present = set(df.columns)
    missing = REQUIRED - present
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. Found: {sorted(present)}.\n"
            f"Fix your CSV headers or extend the rename_map."
        )
    return df

def load_transactions():
    path = Path(CONFIG["data"]["transactions_path"])
    if not path.exists():
        raise FileNotFoundError(f"Transactions file not found: {path}")

    df = _read_csv_robust(path)

    # --- Parse dates ---
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # --- Normalize Amounts ---
    # strip $, commas, plus signs, spaces
    df["amount"] = (
        df["amount"]
        .astype(str)
        .str.replace(r"[\$,]", "", regex=True)
        .str.replace("+", "", regex=False)
        .str.strip()
    )
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    # Normalize Type (debit negative, credit positive)
    t = df["type"].astype(str).str.lower()
    df.loc[t.str.contains("debit|dbt|withdraw|purchase", na=False), "amount"] = -df["amount"].abs()
    df.loc[t.str.contains("credit|deposit|refund|paycheck|salary", na=False), "amount"] = df["amount"].abs()

    # --- Add simple categories ---
    category_map = {
        "starbucks": "Dining",
        "uber": "Transport",
        "walmart": "Groceries",
        "amazon": "Shopping",
        "rent": "Housing",
        "electric": "Utilities",
        "paycheck": "Income",
        "salary": "Income",
        "prime": "Subscriptions",
        "netflix": "Subscriptions",
    }

    def categorize(desc: str) -> str:
        d = str(desc).lower()
        for k, v in category_map.items():
            if k in d:
                return v
        return "Other"

    df["category"] = df["description"].apply(categorize)

    # Reorder & title-case final columns for downstream
    df = df.rename(columns={
        "date":"Date",
        "description":"Description",
        "amount":"Amount",
        "type":"Type",
        "account":"Account",
        "category":"Category",
    })[["Date","Description","Category","Amount","Type","Account"]]

    # --- Save cleaned version ---
    cleaned_path = Path(CONFIG["data"].get("cleaned_transactions_path","data/cleaned_transactions.parquet"))
    cleaned_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cleaned_path, index=False)
    return df

def load_investments():
    path = Path(CONFIG["data"]["investments_path"])
    if not path.exists():
        raise FileNotFoundError(f"Investments file not found: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = df.columns.str.replace("\ufeff","", regex=False).str.strip()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df

if __name__ == "__main__":
    tx = load_transactions()
    iv = load_investments()
    print("Transactions Preview:")
    print(tx.head())
    print("\nInvestments Preview:")
    print(iv.head())
