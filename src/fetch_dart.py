import json
import os
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

API_KEY = os.environ.get("DART_API_KEY")
CORP_CODE = "00164779"
STOCK_CODE = "000660"
COMPANY = "SK하이닉스"
BASE = "https://opendart.fss.or.kr/api"

REPORT_CODES = {
    "Q1": "11013",
    "H1": "11012",
    "Q3": "11014",
    "ANNUAL": "11011",
}

def require_key():
    if not API_KEY:
        raise SystemExit("DART_API_KEY 환경변수가 없습니다. GitHub Actions Secret 또는 로컬 환경변수로 설정하세요.")

def get_json(endpoint, params):
    p = dict(params)
    p["crtfc_key"] = API_KEY
    r = requests.get(f"{BASE}/{endpoint}", params=p, timeout=60)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "000":
        raise RuntimeError(f"DART API 오류: {data.get('status')} {data.get('message')}")
    return data

def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def find_reports():
    end = date.today()
    start = end - timedelta(days=400)
    data = get_json("list.json", {
        "corp_code": CORP_CODE,
        "bgn_de": start.strftime("%Y%m%d"),
        "end_de": end.strftime("%Y%m%d"),
        "pblntf_ty": "A",
        "page_count": "100",
        "sort": "date",
        "sort_mth": "desc",
    })
    rows = data.get("list", [])
    for row in rows:
        if "사업보고서" in row.get("report_nm", "") and "정정" not in row.get("report_nm", ""):
            return row
    return None

def download_document(rcept_no, out_path):
    # OpenDART 공시 원문 다운로드 API
    p = {"crtfc_key": API_KEY, "rcept_no": rcept_no}
    r = requests.get(f"{BASE}/document.xml", params=p, timeout=120)
    r.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # document.xml API returns a ZIP archive. Do not save it with an .xml extension.
    if not r.content.startswith(b"PK\x03\x04"):
        try:
            root = ET.fromstring(r.content)
            status = root.findtext("status") or "unknown"
            message = root.findtext("message") or r.text[:200]
        except ET.ParseError:
            status, message = "unknown", r.text[:200]
        raise RuntimeError(f"DART 원문 다운로드 오류: {status} {message}")
    out_path = out_path.with_suffix(".zip")
    out_path.write_bytes(r.content)

def fetch_financials(years=5):
    current = date.today().year
    all_data = {}
    for year in range(current - years, current):
        # 사업보고서는 다음 해에 제출되므로 아직 존재하지 않는 연도는 정상적으로 건너뜀
        try:
            data = get_json("fnlttSinglAcntAll.json", {
                "corp_code": CORP_CODE,
                "bsns_year": str(year),
                "reprt_code": REPORT_CODES["ANNUAL"],
                "fs_div": "CFS",
            })
            all_data[str(year)] = data
            save_json(RAW / f"financials_{year}_annual_cfs.json", data)
        except Exception as e:
            print(f"[WARN] {year} CFS 조회 실패: {e}")
    save_json(RAW / "financials_all.json", all_data)

def main():
    require_key()
    report = find_reports()
    if report:
        save_json(RAW / "latest_report.json", report)
        rcept = report.get("rcept_no")
        if rcept:
            try:
                download_document(rcept, RAW / f"report_{rcept}.zip")
            except Exception as e:
                print(f"[WARN] 원문 XML 다운로드 실패: {e}")
    else:
        print("[WARN] 최근 정기보고서를 찾지 못했습니다.")
    fetch_financials(years=5)

if __name__ == "__main__":
    main()
