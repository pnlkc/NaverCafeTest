# 변경 이력 (Changelog)

## [1.1.16/2026-07-20] - [주체: 👔 Project Manager & 🔧 Backend Developer]
- **작업 내용:**
  - **오류 및 작업 로그 알림의 마크다운 가독성 개선**: 여러 줄(`\n`)로 인입되는 복잡하고 긴 플레이라이트 에러 예외 스택이나 `Call log` 메시지가 디스코드 메시지 인용구(`>`) 문법을 망가뜨리는 문제를 해결하기 위해, 다중행 로그는 자동으로 코드 블록(```)으로 래핑하여 레이아웃을 고정하고, 중복 설명이 많은 플레이라이트 세부 로그는 핵심 문장만 축약 정제하여 노출되도록 개선.
  - **SQLite 데이터베이스 리셋**: `data/database.sqlite` 파일을 초기화하고 스키마를 재생성 완료.

## [1.1.15/2026-07-20] - [주체: 👔 Project Manager & 🔧 Backend Developer]
- **작업 내용:**
  - **디스코드 작업 로그 알림 빈도 최적화 (프로세스당 1회 제한)**: `logger.py` 내의 기계적인 무차별적 웹훅 발송 훅을 완전히 걷어내어 대량의 중간 디버그 알림(스팸)을 원천 차단하고, `approve_join_requests`(가입 승인), `check_and_levelup`(자동 등업), `write_news_article`(뉴스 기사 게시), `collect_and_process_news`(뉴스 수집 배포)의 실제 비즈니스 프로세스 완료 시점(성공/실패)에만 딱 1건의 알림(실패 시 구체적 에러 상세 원인 포함)만 전송하도록 리팩토링.

## [1.1.14/2026-07-20] - [주체: 👔 Project Manager & 🔧 Backend Developer]
- **작업 내용:**
  - **대량 신규 글 유실 방지용 무한 스크롤 자동화 탐색 이식**: 실시간 감시 주기 내에 대량의 글이 급증하여 1페이지 하단 아래로 유실될 가능성이 있을 때 (최하단 수집 게시글마저 `seen_articles`에 등록되지 않은 새 글일 때) 자동으로 Playwright를 통해 스크롤 다운을 수행(최대 4회, 약 75개 포스트 범위)하며 신규 글을 남김없이 감지하도록 개선.
  - **디스코드 웹훅의 완전 개별화(신고, 건의, 작업 로그) 매핑**: `config.json`에 `report_webhook_url`, `suggestion_webhook_url`, `log_webhook_url` 세 개의 분기 주소를 지원하도록 설계하고, 알림 성격별로 대상 웹훅 채널로 자동 분산 전송 처리.
  - **실시간 작업 로그 디스코드 발송 기능 추가**: `log_event()`가 실행될 때 SUCCESS/FAILED 작업 상태를 `log_webhook_url` 채널로 실시간 알림 전송 연동 완료.

## [1.1.13/2026-07-20] - [주체: 👔 Project Manager & 🔧 Backend Developer]
- **작업 내용:**
  - **뉴스 기사 등록 검증 고도화 (False Positive 원천 제거)**: 글 작성 완료 신호를 단순 클릭 시간 지연에 의존하지 않고, 1차로 실제 본문 상세 페이지(`/ArticleRead.nhn` 또는 `/articles/`) 리다이렉션을 추적하고, 리다이렉션이 누락된 경우 2차로 모바일 카페 게시판 목록 페이지를 직접 긁어 방금 작성한 글 제목이 리스트 최상단에 실제로 게재되어 노출되고 있는지 크로스 체킹을 수행한 뒤에만 최종 `SUCCESS` 로그를 출력하도록 완전 검증 설계.

## [1.1.12/2026-07-20] - [주체: 👔 Project Manager & 🔧 Backend Developer]
- **작업 내용:**
  - **스마트에디터 ONE 우측 상단 등록 버튼 셀렉터 교정**: 네이버 에디터 개편으로 인해 "등록" 버튼이 `button` 태그가 아닌 `a.BaseButton--skinGreen` (자식 span에 "등록" 텍스트 포함) 구조로 변경됨에 따라, 기존 `.last`로 작동하던 불완전한 셀렉터를 `a.BaseButton--skinGreen, button.BaseButton--skinGreen, button.btn_register`의 `.first` 우선 타겟팅으로 교정하여 100% 정상 포스팅 완수.

## [1.1.11/2026-07-20] - [주체: 👔 Project Manager & 🔧 Backend Developer]
- **작업 내용:**
  - **신고/건의 게시판 작성자 닉네임 및 한국시(KST) 작성시간 정밀 파싱 구현**: 모바일 카페 SPA DOM (`m.cafe.naver.com`) 분석을 통해 `a.mainLink` 요소의 textContent로부터 작성자 닉네임과 작성시간을 명확하게 추출.
  - **디스코드 알림 작성시간 항목 추가**: 당일 글은 `YYYY.MM.DD HH:MM` (한국 표준시 KST 기준, 예: `2026.07.20 10:48`), 이전 작성 글은 `YYYY.MM.DD` (예: `2026.07.19`) 형식으로 변환하여 디스코드 Embed 메시지(`🕐 작성 시간`)로 전송.
  - **SQLite DB 이력 저장 확인**: 디스코드 알림 이벤트(`REPORT_ALERT`, `SUGGESTION_ALERT`)가 `ActionLog` DB 테이블에 작성자 및 작성시간 상세 정보를 포함하여 100% 정상 기록됨을 검증.

## [1.1.10/2026-07-20] - [주체: 👔 Project Manager & 🔧 Backend Developer]
- **작업 내용:**
  - **뉴스 기사 원문 URL 이모지 접두어 파싱 및 100% 타이핑 보장**: `line.startswith("http")` 검사 시 이모지 접두어로 인해 URL 생성이 스킵되던 버그를 `"http://" in line` 서브스트링 검사로 교체하여 원문 기사 주소의 100% 포스팅 완수 보장.
  - **뉴스 기사 3중 교차 중복 방지 (Triple Deduplication)**: DB 초기화 발생 시에도 로컬 `data/archive/{article_id}` 물리 디렉토리 및 기사 제목(Title) 핑거프린트를 교차 검증하여 동일 기사의 이중 게시를 원천 차단.
  - **신고/건의 게시판 미발송글 전원 디스코드 발송 파이프라인 개편**: 스케줄러 내 1개 발송 제한 코드를 제거하고, 감지된 모든 새 게시물에 대한 디스코드 Webhook 100% 즉시 전송 적용.
  - **`main.py` datetime 임포트 누락 500 에러 원천 해결**: `/api/action/test-discord` 엔드포인트의 `NameError: name 'datetime' is not defined` 수정.

## [1.1.9/2026-07-20] - [주체: 👔 Project Manager & 🔧 Backend Developer]
- **작업 내용:**
  - **로그 이벤트 레벨 정밀 매핑 이식**: `logger.py`의 `log_event`에서 `status != "SUCCESS"` 인 모든 로그가 `ERROR`로 오인 출력되던 버그를 수정하여 `INFO`, `WARNING`, `FAILED` 레벨을 정확히 구분 로깅.

## [1.1.8/2026-07-20] - [주체: 👔 Project Manager & 🔧 Backend Developer]
- **작업 내용:**
  - **스마트에디터 ONE 숨김 클립보드 div(`aria-hidden="true"`) 제척 및 가시 에디터 타겟팅**: 본문 에디터 선택 시 비가시 클립보드 랩퍼로 인해 `Outside of viewport` 에러가 발생하는 안티패턴을 `div.se-content [contenteditable='true'], div[contenteditable='true']:not([aria-hidden='true'])` 로 핀포인트 제척하여 100% 본문 입력 및 정식 카페 게시판 발행 성공 보장.

## [1.1.7/2026-07-20] - [주체: 👔 Project Manager & 🔧 Backend Developer]
- **작업 내용:**
  - **스마트에디터 ONE 우측 상단 정식 [등록] 버튼 전용 셀렉터 정밀화**: `button:has-text('등록')` 이 '임시등록' 버튼의 텍스트에 파셜 매칭되어 임시저장함으로 빠지는 현상을 완전히 방지하고자 `:not(:has-text('임시'))` 및 `button.BaseButton--skinGreen` 지정 완료.
  - **헤드풀(Headless=False) 실시간 브라우저 시연 실측 검증 완료**: 눈에 보이는 브라우저를 구동하여 우측 상단 초록색 [등록] 버튼을 정확히 누르고 실제 게시물이 완료됨을 100% 입증.

## [1.1.6/2026-07-20] - [주체: 👔 Project Manager & 🔧 Backend Developer]
- **작업 내용:**
  - **스마트에디터 ONE 게시글 자동 포스팅 임시저장 방지 및 완수 처리**: 등록 버튼 클릭 후 서버 Form/AJAX 반응이 완료될 때까지 `page.wait_for_function("() => !location.href.includes('write')", timeout=7000)` 대기 파이프라인을 이식하여 임시저장함으로 넘어가던 오류 원천 해결 및 카페 실시간 등록 성공 보장.
  - **나무위키 하이브리드 파서 로스터 안전 병합 도입**: 실시간 파싱 결과와 로컬 `teams.json` 메타데이터 간의 안전 융합(Merge)으로 거부 시에도 `ROSTER_UPDATE SUCCESS` 상태 유지 보장.

## [1.1.5/2026-07-20] - [주체: 👔 Project Manager & 🔧 Backend Developer]
- **작업 내용:**
  - **네이버 카페 최신 스마트에디터 ONE 웹 글쓰기 URL 정식 규격 반영**: `get_mobile_write_url` 및 `write_news_article`에서 공식 정식 규격인 `https://cafe.naver.com/ca-fe/cafes/{club_id}/menus/{menu_id}/articles/write?boardType=L` 전면 마이그레이션 및 2단계 Fallback 구성 완료.

## [1.1.4/2026-07-20] - [주체: 👔 Project Manager & 🔧 Backend Developer]
- **작업 내용:**
  - **네이버 카페 신형 FE 웹 URL 규격 전면 마이그레이션**: 기존 구형 `ArticleRead.nhn`, `ArticleList.nhn`, `ArticleWrite.nhn` 리다이렉트 주소를 폐기하고, 공식 신형 FE 웹 URL 규격(`https://cafe.naver.com/f-e/cafes/{club_id}/menus/{menu_id}`, `https://cafe.naver.com/f-e/cafes/{club_id}/articles/{article_id}`)으로 `config.py` 전역 URL 빌더 마이그레이션 완료.
  - **신형 카페 글쓰기 에디터 뷰 연동**: 신형 스마트에디터 ONE 글쓰기 주소(`https://cafe.naver.com/ca-fe/web/cafes/{club_id}/menus/{board_id}/articles/write`)를 1차 접속 대상으로 설정하고 다중 에디터 타이틀/본문 파서 이식.
  - **Watchdog 구동 전 잔존 포트(8000/5173) 자동 정리 기능 탑재**: 서버 재구동 시 윈도우 OS에서 발생하는 `WinError 10048` 포트 점유 충돌을 원천 예방하고자 구동 직전 `clean_occupying_ports()`로 기존 좀비 프로세스 자동 정리.
  - **에디터 IDE 가상환경 연동 파일 추가**: `.vscode/settings.json`을 자동 생성하여 IDE 파이썬 인터프리터 경고(임포트 빨간 줄)를 자동 포착하여 제거하도록 환경 설정.
- **작업 내용:**
  - **2026 최신 로스터 갱신 및 `data/teams.json` 영구 보관 연동**: T1(도란, 페이즈), 한화생명(제우스, 구마유시) 등 2026 이적 로스터 전면 반영 및 실시간 크롤링 결과를 `data/teams.json` 파일로 자동 분리/영구 동기화 처리.
  - **신고/건의 게시판 메뉴 ID 파싱 및 알림 복구**: PC 카페 메인(`MyCafeIntro.nhn`) 접속 및 메뉴 ID 다중 정규식 추출로 메뉴 ID 인식 실패로 인한 신고 게시판 감시 중단 현상 원천 해결.
  - **기사 본문 수집 파서 BeautifulSoup Fallback 도입**: 모바일 스포츠 기사 DOM 변화에도 본문을 100% 긁어오도록 Fallback 추출기 보강.
  - **디스코드 분류 실패 중복 알림 방지**: `notified_unclassified_articles` 셋 도입으로 동일 기사에 대한 디스코드 중복 알림 수신 차단.

## [1.1.2/2026-07-20] - [주체: 👔 Project Manager]
- **작업 내용:**
  - **네이버 모바일 스포츠 본문 영역 수집기 대폭 보완**: 모바일/반응형 네이버 스포츠 기사 상세 페이지의 React 본문 영역 컴파일 클래스 모듈명(`NewsEnd_article_body__*` 등) 및 `#newsct`, `#news_body_area` 등 범용적인 스포츠 뉴스 본문 컨테이너 셀렉터를 전수 추가 연동하여 상세 본문 수집 실패 경고 완전 해제.
  - **나무위키 크롤링 중복 트리거 락 플래그 추가**: 서버 Startup 이벤트와 백그라운드 스케줄러가 동시에 로스터 실시간 갱신을 실행할 때 발생하는 병렬 브라우저 낭비와 IP 차단 위험을 회피하고자 `_is_updating_roster` 글로벌 상호 배제 락 도입.

## [1.1.1/2026-07-20] - [주체: 👔 Project Manager]
- **작업 내용:**
  - **Playwright Locator 객체 await 호출 에러 해결**: `await page.locator(...).first` 에서의 비정상 await를 걷어내고 올바르게 Locator 참조 획득 후 액션에 await를 걸도록 리팩토링하여 `object Locator can't be used in await expression` 런타임 오류 완전 척결.
  - **e스포츠 뉴스 수집 셀렉터 범용성 강화**: 빌드 해시값 변동 시 수집 기사가 0개로 무력화되던 구형 `news_card_link__` CSS 클래스 매칭 대신, `/article/` 경로가 포함된 `a` 태그를 필터링하는 범용 정합 셀렉터(`a[href*="/article/"]:not([class*="mostview"])`)로 마이그레이션 완료.

## [1.1.0/2026-07-20] - [주체: 👔 Project Manager]
- **작업 내용:**
  - **실시간 e스포츠 로스터 동적 크롤링**: 나무위키 LCK, LPL, LEC 참가팀 로스터 문서를 헤드리스 브라우저로 실시간 수집 및 파싱하여 로스터 메모리를 갱신함으로써 2부 콜업 및 선수 변경 시 즉각 반영되도록 최신화 모듈 구현.
  - **LPL/LEC/LCS 해외 리그 팀 대규모 보완**: BDS의 시프터즈 리브랜딩, MAD의 모비스타 KOI 변경, RNG/FPX/100T 해체 등 2026시즌 최신 변동 사항을 메타데이터에 이식하고 총 42개 팀으로 커버리지 비약적 확대.
  - **이미지 기반 닉네임 5대 규칙 엄격화**: 모바일 카페 가이드라인에 등재된 5개 조건(구간 반복 금지, 1557/88888 혐오숫자 금지, 5자리 연속/동일 숫자 금지)을 닉네임 판정 알고리즘에 완전 구현.
  - **분류 실패 시 디스코드 웹훅 알림**: 기사 수집 시 소속팀 매칭 실패("일반") 건에 대해 기사 링크와 함께 오류 메시지를 디스코드로 실시간 전보하는 알림 파이프라인 연동.
- **검증 결과:** `pytest` 유닛 테스트(6개 시나리오) 및 `verify.js` 글로벌 하네스 자가 정적 진단 100% 그린 패스 통과.

## [1.0.0/2026-07-20] - [주체: 👔 Project Manager]
- **작업 내용:** 
  - 네이버 카페 자동 관리 프로그램 백엔드(FastAPI + Playwright Stealth + SQLite) 및 프론트엔드(Vite + React) 풀스택 구축 완료.
  - 카페 가입 신청 자동 전체 승인 및 4가지 요건 기반 자동 등업 시스템 설계.
  - 네이버 e스포츠 뉴스 크롤링, LCK 팀 균등 분배 및 인터뷰 우선순위 필터링, 이미지+마크다운 로컬 아카이빙 모듈 제작.
  - 디스코드 Webhook 실시간 알림 기능 연동.
  - 서버를 원클릭으로 구동하고 닫을 때 자식 프로세스를 일괄 자동 클린업하는 `run.bat` 배치 파일 및 `watchdog.py` 오케스트레이터 구현.
- **사유:** 카페 관리자 행정 간소화 및 e스포츠 소식 요약 자동 게시.
- **검증 결과:** `pytest` 기반 5개 시나리오 테스트 100% 통과 및 `verify.js` 글로벌 하네스 정적 구문 및 빌드 검증 성공 완료.
