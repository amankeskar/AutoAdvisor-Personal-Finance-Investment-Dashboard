from src.analyze import analyze_month
from src.insights import generate_insights

def main():
    print("AutoAdvisor: bootstrap OK.")
    metrics = analyze_month()  # or analyze_month(month="2025-08")
    print("\n=== Monthly Metrics ===")
    for k, v in metrics.items():
        print(f"{k}: {v}")

    print("\n=== Insights ===")
    for line in generate_insights(metrics):
        print(f"- {line}")

if __name__ == "__main__":
    main()
