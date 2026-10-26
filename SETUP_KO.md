# GitHub 저장소 연결 순서

저장소: https://github.com/HSC-Class02/dart-park-jung-won

1. 저장소의 `.github/workflows/update.yml`과 `src/`, `docs/` 폴더가 있는지 확인합니다.
3. `DART_API_KEY`를 GitHub Actions Secret으로 등록합니다.
4. `Settings → Pages`에서 Source를 `GitHub Actions`로 설정합니다.
5. `Actions → DART Financial Update → Run workflow`를 한 번 실행합니다.
6. 성공하면 Pages에 대시보드가 배포됩니다.

권장 저장소 구조:

dart-park-jung-won/
├─ .github/workflows/update.yml
├─ src/
├─ data/
├─ docs/
├─ requirements.txt
├─ README.md
└─ .gitignore

API 키는 공개 저장소의 파일에 절대 입력하지 않습니다.
