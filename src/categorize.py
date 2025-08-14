import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from joblib import dump, load
from pathlib import Path

MODEL_PATH = Path("data/category_model.joblib")

def train_category_model(df: pd.DataFrame):
    # Expect df with columns: Description, Category
    df = df.dropna(subset=["Description","Category"])
    X = df["Description"].astype(str)
    y = df["Category"].astype(str)
    vec = TfidfVectorizer(ngram_range=(1,2), min_df=2)
    Xv = vec.fit_transform(X)
    clf = LogisticRegression(max_iter=200)
    clf.fit(Xv, y)
    dump((vec, clf), MODEL_PATH)

def predict_category(descriptions):
    vec, clf = load(MODEL_PATH)
    Xv = vec.transform(pd.Series(descriptions).astype(str))
    return clf.predict(Xv)

# Quick CLI usage
if __name__ == "__main__":
    import pandas as pd
    df = pd.read_parquet("data/cleaned_transactions.parquet")
    train_category_model(df)  # trains from your current labeled data (rules)
    print("Model trained ->", MODEL_PATH)
