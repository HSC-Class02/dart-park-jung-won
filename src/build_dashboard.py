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
    "years": df.to_dict(orient="records"),
}
(DOCS / "data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("docs/data.json 생성 완료")
