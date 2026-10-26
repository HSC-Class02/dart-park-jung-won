import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "financial_analysis.json"
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

df = pd.read_json(OUT)
payload = {
    "company": "SK하이닉스",
    "stock_code": "000660",
    "corp_code": "00164779",
    "generated_at": pd.Timestamp.now(tz="Asia/Seoul").isoformat(),
    # DataFrame.to_dict can emit float NaN for missing values; json.loads(to_json) maps them to standard JSON null.
    "years": json.loads(df.to_json(orient="records", date_format="iso")),
}
(DOCS / "data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
print("docs/data.json 생성 완료")
