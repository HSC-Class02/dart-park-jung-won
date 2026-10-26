import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

# OpenDART 계정명 변형에 대응하기 위한 보수적 alias
ALIASES = {
    "total_assets": ["자산총계", "자산 총계"],
    "cash": ["현금및현금성자산", "현금 및 현금성자산"],
    "receivables": ["매출채권", "매출채권및기타채권", "매출채권 및 기타채권"],
    "inventory": ["재고자산"],
    "ppe": ["유형자산", "유형자산순액"],
    "current_assets": ["유동자산"],
    "current_liabilities": ["유동부채"],
    "total_liabilities": ["부채총계", "부채 총계"],
    "equity": ["자본총계", "자본 총계"],
    "revenue": ["매출액", "수익(매출액)", "매출"],
    "gross_profit": ["매출총이익", "매출총이익(손실)"],
    "sga": ["판매비와관리비", "판매비와 일반관리비"],
    "operating_income": ["영업이익", "영업이익(손실)"],
    "pretax_income": ["법인세비용차감전순이익", "세전이익", "세전계속사업이익"],
    "net_income": ["당기순이익", "당기순이익(손실)"],
    "controlling_net_income": ["지배기업의 소유주에게 귀속되는 당기순이익", "지배주주순이익"],
    "cfo": ["영업활동으로 인한 현금흐름", "영업활동현금흐름", "영업활동현금흐름(순액)"],
    "cfi": ["투자활동으로 인한 현금흐름", "투자활동현금흐름"],
    "cff": ["재무활동으로 인한 현금흐름", "재무활동현금흐름"],
    "interest_expense": ["이자비용", "금융비용"],
    "ebitda": ["EBITDA", "EBITDA(영업이익+감가상각비)"],
    "short_borrowings": ["단기차입금"],
    "long_borrowings": ["장기차입금", "장기차입금및사채", "사채"],
    "trade_payables": ["매입채무", "매입채무및기타채무"],
    "cost_of_sales": ["매출원가"],
    "capex_ppe": ["유형자산의 취득"],
    "capex_intangibles": ["무형자산의 취득"],
}

def num(v):
    if v is None or v == "":
        return None
    s = str(v).replace(",", "").strip()
    if s in {"-", "–", "—"}:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return None

def rows_for_year(year):
    p = RAW / f"financials_{year}_annual_cfs.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return data.get("list", [])

def pick(rows, aliases, statement=None):
    candidates = []
    for r in rows:
        if statement and r.get("sj_nm") != statement:
            continue
        name = (r.get("account_nm") or "").replace(" ", "")
        for alias in aliases:
            if name == alias.replace(" ", ""):
                candidates.append(r)
                break
    if not candidates:
        return None
    # 연결(CFS) 내에서도 당기/전기 금액이 있는 행을 우선
    r = candidates[0]
    return num(r.get("thstrm_amount"))

def pick_by_account_ids(rows, account_ids):
    """Prefer stable DART account IDs for current and non-current borrowings."""
    for row in rows:
        if row.get("sj_nm") != "재무상태표":
            continue
        if row.get("account_id") in account_ids:
            value = num(row.get("thstrm_amount"))
            if value is not None:
                return value
    return None

def extract_year(year):
    rows = rows_for_year(year)
    result = {"year": year}
    for key, aliases in ALIASES.items():
        result[key] = pick(rows, aliases)
    # SK하이닉스 DART CFS에서는 여러 해에 걸쳐 계정명이 "차입금"으로 같으므로 계정 ID로 유동/비유동을 구분한다.
    short_by_id = pick_by_account_ids(rows, {
        "ifrs-full_ShorttermBorrowings",
        "ifrs-full_CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings",
    })
    long_by_id = pick_by_account_ids(rows, {
        "dart_LongTermBorrowingsGross",
        "ifrs-full_LongtermBorrowings",
    })
    if short_by_id is not None:
        result["short_borrowings"] = short_by_id
    if long_by_id is not None:
        result["long_borrowings"] = long_by_id

    # 이자부차입금 = 단기 + 장기 차입금/사채의 단순 합
    short = result.get("short_borrowings") or 0
    long = result.get("long_borrowings") or 0
    result["interest_bearing_debt"] = short + long if (result.get("short_borrowings") is not None or result.get("long_borrowings") is not None) else None
    capex_ppe = result.get("capex_ppe")
    capex_intangibles = result.get("capex_intangibles")
    result["capex"] = capex_ppe + capex_intangibles if capex_ppe is not None and capex_intangibles is not None else None
    result["fcf"] = result["cfo"] - result["capex"] if result.get("cfo") is not None and result.get("capex") is not None else None
    if result.get("cfo") is not None and result.get("ppe") is not None:
        # DART 원자료만으로 CAPEX를 완전히 일관되게 정의하기 어렵기 때문에
        # 현금흐름 세부계정 alias가 발견될 경우 아래 값을 덮어쓸 수 있게 둠.
        pass
    return result

def safe_div(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b

def avg(a, b):
    if a is None or b is None:
        return None
    return (a + b) / 2

def pct(x):
    return None if x is None else x * 100

def days_ratio(numerator, denominator):
    """Convert a ratio to days, preserving missing values."""
    value = safe_div(numerator, denominator)
    return None if value is None else 365 * value

def calculate(df):
    out = []
    prev = None
    for _, r in df.iterrows():
        d = r.to_dict()
        d["gross_margin"] = pct(safe_div(d["gross_profit"], d["revenue"]))
        d["operating_margin"] = pct(safe_div(d["operating_income"], d["revenue"]))
        d["net_margin"] = pct(safe_div(d["net_income"], d["revenue"]))
        d["ebitda_margin"] = pct(safe_div(d["ebitda"], d["revenue"]))
        d["current_ratio"] = pct(safe_div(d["current_assets"], d["current_liabilities"]))
        d["quick_ratio"] = None  # 당좌자산 정의가 회사별로 달라 별도 세부 조정 필요
        d["debt_ratio"] = pct(safe_div(d["total_liabilities"], d["equity"]))
        d["equity_ratio"] = pct(safe_div(d["equity"], d["total_assets"]))
        d["debt_to_assets"] = pct(safe_div(d["interest_bearing_debt"], d["total_assets"]))
        d["interest_coverage"] = safe_div(d["operating_income"], d["interest_expense"])
        d["net_debt"] = (d["interest_bearing_debt"] - d["cash"]) if d["interest_bearing_debt"] is not None and d["cash"] is not None else None
        d["net_debt_ebitda"] = safe_div(d["net_debt"], d["ebitda"])
        d["asset_turnover"] = safe_div(d["revenue"], avg(prev["total_assets"], d["total_assets"]) if prev else None)
        d["roa"] = pct(safe_div(d["net_income"], avg(prev["total_assets"], d["total_assets"]) if prev else None))
        d["roe"] = pct(safe_div(d["net_income"], avg(prev["equity"], d["equity"]) if prev else None))
        d["sales_growth"] = pct(safe_div(d["revenue"], prev["revenue"]) - 1) if prev and safe_div(d["revenue"], prev["revenue"]) is not None else None
        d["cfo_net_income"] = safe_div(d["cfo"], d["net_income"])
        d["dso"] = days_ratio(avg(prev["receivables"], d["receivables"]) if prev else None, d["revenue"])
        d["dio"] = days_ratio(avg(prev["inventory"], d["inventory"]) if prev else None, d["cost_of_sales"])
        d["dpo"] = days_ratio(avg(prev["trade_payables"], d["trade_payables"]) if prev else None, d["cost_of_sales"])
        d["ccc"] = (d["dso"] + d["dio"] - d["dpo"]) if all(x is not None for x in [d["dso"], d["dio"], d["dpo"]]) else None
        # FCF는 가이드 정의(CFO - 현금 기준 CAPEX). CAPEX 자동 인식이 가능한 경우에만 계산.
        d["fcf"] = d["cfo"] - d["capex"] if pd.notna(d["cfo"]) and pd.notna(d["capex"]) else None
        d["roic"] = None
        d["roic_minus_wacc"] = None
        out.append(d)
        prev = d
    return pd.DataFrame(out)

def main():
    years = []
    for p in sorted(RAW.glob("financials_*_annual_cfs.json")):
        try:
            years.append(int(p.stem.split("_")[1]))
        except Exception:
            pass
    years = sorted(set(years))
    rows = [extract_year(y) for y in years]
    if not rows:
        raise SystemExit("재무 원자료가 없습니다. 먼저 fetch_dart.py를 실행하세요.")
    df = pd.DataFrame(rows)
    df = calculate(df)
    df.to_csv(OUT / "financial_analysis.csv", index=False, encoding="utf-8-sig")
    (OUT / "financial_analysis.json").write_text(df.to_json(orient="records", force_ascii=False, indent=2), encoding="utf-8")
    print(df[["year", "revenue", "operating_income", "net_income", "total_assets", "equity", "cfo", "gross_margin", "operating_margin", "roe", "roa"]].to_string(index=False))

if __name__ == "__main__":
    main()
