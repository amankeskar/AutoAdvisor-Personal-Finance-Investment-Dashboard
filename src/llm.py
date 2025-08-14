import os, json, requests
import yaml

with open("config/config.yaml","r") as f:
    CONFIG = yaml.safe_load(f)

HF_API = "https://api-inference.huggingface.co/models/"
HF_MODEL = CONFIG.get("ai",{}).get("model","google/flan-t5-large")
HF_KEY = os.getenv("HUGGINGFACE_API_KEY")

def llm_narrative(metrics: dict) -> str:
    if not HF_KEY:
        return "⚠️ No HUGGINGFACE_API_KEY set; showing rules-based insights only."
    prompt = f"""You are a concise personal finance coach.
Given this JSON monthly summary, write 4-6 bullet points:
- call out changes vs typical patterns
- highlight risky categories
- give 2 actionable tips

JSON:
{json.dumps(metrics, indent=2)}
"""
    headers = {"Authorization": f"Bearer {HF_KEY}"}
    # Basic text-generation payload (works with instruct models)
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 220}}
    r = requests.post(HF_API + HF_MODEL, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    out = r.json()
    # HF output can be list/dict depending on model
    if isinstance(out, list) and out and "generated_text" in out[0]:
        return out[0]["generated_text"].strip()
    if isinstance(out, dict) and "generated_text" in out:
        return out["generated_text"].strip()
    # Fallback
    return str(out)[:1500]
