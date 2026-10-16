# 국내주식 눌림목 추적 웹사이트

기존 v1.3.4의 스크리닝 조건을 그대로 재사용하는 온라인 배포본입니다.
주식 추천·자동 주문이 아닌 조건 발견과 가격 변화 추적 도구입니다.

## 처음 한 번 설정
GitHub Settings → Pages → Build and deployment → Source를 **GitHub Actions**로 선택하세요.
Actions → Daily pullback tracker → Run workflow에서 실행할 수 있습니다.
사이트 주소: https://eoajflrn.github.io/kr-pullback-tracker/
이 주소는 실제 Pages 배포 성공 후에만 열립니다.

## 자동 갱신
월~금 한국시간 19:00에 수집하며 19:30에 재시도합니다. GitHub 스케줄은 지연될 수 있습니다.
휴장일/일봉 미확보 시 이전 종목을 당일 신규로 만들지 않습니다.
총 대상·검사 완료·미확보 수와 종가 기준일을 화면에서 확인하세요.
일부 종목 실패는 PARTIAL로 기록하며 기존 DB는 유지합니다.
수집과 배포가 별도 job이므로 Pages 실패와 수집 실패를 구분할 수 있습니다.

## 휴대폰
사이트에서 날짜 조회·검색·차트·누적 원장을 볼 수 있습니다. PC를 켜둘 필요가 없습니다.
미저장 날짜는 Actions의 scan_date에 YYYY-MM-DD를 입력해 재계산한 후 조회합니다.
최초 실제 발견 기록과 과거 재계산은 별도 집계입니다.
관심목록은 해당 브라우저에 저장됩니다. PC와 자동 동기화되지 않습니다.

## 기존 자료 이전
이번 초기 업로드에는 사용자 PC의 과거 누적 DB나 오래된 테스트 데이터가 포함되지 않습니다.
PC의 최신 data/tracker.db와 web/data 전체를 가져와 병합하는 작업이 별도로 필요합니다.
최초 발견가격·발견일은 이후 결과를 보고 변경하지 않습니다.

## 데이터와 보존
모집단: 날짜별 FinanceDataReader KRX 목록 캐시, 불가 시 당일 네이버 목록.
일봉: 네이버 일봉 API. 종목코드 끝자리 0, 시총 1천억원 이상 기준은 기존과 동일합니다.
공개 비공식 API의 가용성·응답 형식·기업행사 수정주가에 제한이 있습니다.
SQLite와 정규화 JSON은 git에 누적 저장합니다. raw 응답과 직전 DB 백업은 Actions artifact 7일 보관입니다.
웹에 게시된 종목 데이터와 저장소 코드는 공개됩니다. 개인정보·비밀번호를 업로드하지 마세요.
GitHub 무료 범위/정책 변경과 자동 실행 중단 여부를 정기적으로 확인하세요.

## 검증
python -m unittest discover -s tests -v
로컬: PREVIEW.cmd / 같은 Wi-Fi 휴대폰: PREVIEW_MOBILE.cmd
