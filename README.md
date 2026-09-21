# DART SK하이닉스 재무분석 Agent

SK하이닉스(종목코드 000660, DART corp_code 00164779)의 OpenDART 정기보고서/재무제표를 자동 수집하고,
첨부된 「재무제표 및 재무비율 실무 가이드」의 핵심 지표를 계산하여 `docs/`의 GitHub Pages 대시보드로 공개하는 프로젝트입니다.

## 구성

- `src/fetch_dart.py` : DART 공시검색 → 사업보고서 원문/XML 저장 + 재무제표 JSON 수집
- `src/analyze.py` : 5개년 재무수치 정규화 및 재무비율 계산
- `src/build_dashboard.py` : 대시보드용 `docs/data.json` 생성
- `docs/index.html` : GitHub Pages 정적 대시보드
- `.github/workflows/update.yml` : 매일 자동 수집/분석/커밋/Pages 배포
- `data/raw/` : DART 원천자료
- `data/processed/` : 분석 결과 CSV/JSON

## 분석 지표

첨부 가이드의 분석 흐름을 반영했습니다.

### 핵심 금액
총자산, 현금및현금성자산, 매출채권, 재고자산, 유형자산, 총부채,
이자부차입금, 자본총계, 매출액, 매출총이익, 판관비, 영업이익,
세전이익, 당기순이익, 지배주주순이익, EBITDA, 영업활동현금흐름,
투자활동현금흐름, 재무활동현금흐름, CAPEX, FCF, 순차입금

### 재무비율
매출총이익률, 영업이익률, 순이익률, EBITDA 마진, ROA, ROE,
유동비율, 당좌비율, 부채비율, 자기자본비율, 차입금의존도,
이자보상배율, 순차입금/EBITDA, 총자산회전율, DSO, DIO, DPO, CCC,
매출증가율, CFO/순이익

ROIC는 NOPAT/투하자본의 조정 정의가 회사별로 달라질 수 있으므로
기본 버전에서는 원자료와 계산에 필요한 항목을 표시하고, 설정에서 확장할 수 있도록 설계했습니다.
PER/PBR/EV/EBITDA는 DART 재무정보만으로 현재 주가를 만들 수 없으므로 기본 대시보드에서는
'시장 데이터 연동 필요'로 표시합니다.

## API 키 설정

1. OpenDART에서 인증키를 발급합니다.
2. GitHub 저장소:
   https://github.com/sgk70062-code/dart-
3. `Settings → Secrets and variables → Actions → New repository secret`
4. Name: `DART_API_KEY`
5. Value: 발급받은 40자리 인증키

인증키는 `.env`, 코드, README, Git 커밋에 직접 넣지 마세요.

## 로컬 실행

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

# PowerShell
$env:DART_API_KEY="발급받은_키"

python src/fetch_dart.py
python src/analyze.py
python src/build_dashboard.py
```

완료 후 `docs/index.html`을 브라우저에서 열거나 GitHub Pages로 배포합니다.

## GitHub Actions 자동 업데이트

기본 설정은 매일 한국시간 오전 2시(UTC 17:00)에 실행됩니다.
또한 Actions 탭에서 수동 실행할 수 있습니다.

자동화 순서:

1. DART 공시목록 조회
2. 최신 사업보고서/정기보고서 확인
3. 원문 XML 저장
4. 최근 5개 연도 재무제표 수집
5. 주요 재무수치 추출
6. 재무비율 계산
7. CSV/JSON 갱신
8. Git commit/push
9. GitHub Pages 대시보드 배포

GitHub Actions의 scheduled workflow는 cron으로 실행할 수 있으며, GitHub Pages는
Actions 기반 정적 사이트 배포를 지원합니다.

## 중요한 회계 기준

첨부 가이드의 원칙에 따라 연결(CFS) 기준을 우선하고, 평균 자산/평균 자본이 필요한
ROA/ROE/회전율은 전기와 당기의 평균을 사용합니다. 연결/별도 기준을 섞지 않으며,
일회성 항목은 자동으로 정상화한다고 가정하지 않습니다.

DART 계정명은 회사/연도에 따라 변형될 수 있으므로 `src/analyze.py`의 ALIASES를
확장할 수 있습니다.

## 주의

이 프로젝트는 공시자료의 자동 수집 및 재무분석용 교육/분석 도구입니다.
재무비율은 정의와 조정 방식에 따라 달라질 수 있으므로 원문 주석과 사업보고서를 함께 확인하세요.
