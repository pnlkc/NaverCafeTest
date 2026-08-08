# 변경 이력 (Changelog)

## [1.1.75/2026-08-08] - [주체: 👔 Project Manager]
- **작업 내용:**
  - **.env.example 템플릿 주석 오타 수정 ([.env.example](file:///c:/Users/pnlkc/AIProject/NaverCafe/.env.example#L1))**:
    - 파일 첫 줄의 잘못 포함된 한글 글자 `ㄷ#`을 `#`로 수정 및 정리.
- **사유:** 사용자의 `.env.example` 커밋 지시 반영.
- **검증 결과:** `verify.js` 자가 검증 완료.

## [1.1.74/2026-07-22] - [주체: ⚙️ Backend Developer]
- **작업 내용:**
  - **뉴스 요약 전용 경량 Flash-Lite 모델 파이프라인 최적화 ([backend/news_crawler.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/news_crawler.py#L843), [backend/config.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/config.py#L44), [data/config.json](file:///c:/Users/pnlkc/AIProject/NaverCafe/data/config.json#L44))**:
    - 불필요한 헤비 모델 호출(오버스펙)을 방지하고 빠른 텍스트 요약 속도를 위해 경량(Flash-Lite/Flash) 전용 모델 3종으로 파이프라인 재구성:
      1. `gemini-3.5-flash-lite` (1순위: 뉴스 3줄 요약 전용 최적 초경량 초고속 모델 ⚡)
      2. `gemini-2.5-flash` (2순위: 2.5세대 텍스트 파싱 전용 경량 Flash)
      3. `gemini-1.5-flash` (3순위: 안정적인 백업 경량 Flash)
- **사유:** 사용자의 오버스펙 방지 및 뉴스 요약 과업에 최적화된 경량 모델 선택 지시 반영.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.73/2026-07-22] - [주체: ⚙️ Backend Developer]
- **작업 내용:**
  - **Google Gemini API 최신 무료 모델 3종 폴백 파이프라인 적용 ([backend/news_crawler.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/news_crawler.py#L843), [backend/config.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/config.py#L43), [data/config.json](file:///c:/Users/pnlkc/AIProject/NaverCafe/data/config.json#L44))**:
    - 구글 Gemini 공식 무료 티어(15 RPM / 일일 1,500회 제한) 기반 최신 Flash 모델 3종 순차 시도 폴백 체인 구축:
      1. `gemini-2.5-flash` (1순위: 최신 고성능 요약 전용 모델)
      2. `gemini-2.0-flash` (2순위: 2.0세대 초고속 Flash 모델)
      3. `gemini-1.5-flash` (3순위: 안정적인 1.5세대 백업 Flash 모델)
    - 기본 LLM 요약 제공자를 `gemini`로 갱신하여 100% 무료 쿼터 범위 내에서 뉴스 요약을 수행하도록 설정.
- **사유:** 구글 Gemini 최신 모델 적용 및 3단계 무료 폴백 안정화 지시 반영.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.72/2026-07-22] - [주체: 🧹 Clean Coder & ⚙️ Backend Developer]
- **작업 내용:**
  - **Playwright 컨텍스트 생성 공통 모듈화 ([backend/naver_bot.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/naver_bot.py#L59))**:
    - `_create_browser_context` 헬퍼 함수를 신설하여 크롬 인스턴스 launch, User-Agent 지정, Stealth 우회 일괄 적용 중복 코드를 단일화.
  - **JSON 파일 I/O 보일러플레이트 제거 ([backend/news_crawler.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/news_crawler.py#L24))**:
    - `_read_json_file` 및 `_write_json_file` 공통 헬퍼를 도입하여 repetitive `json.load`/`json.dump` 보일러플레이트 3쌍을 모듈화 및 슬림화.
  - **프론트엔드 유틸리티 함수 단일화 ([frontend/src/utils.js](file:///c:/Users/pnlkc/AIProject/NaverCafe/frontend/src/utils.js#L61), [frontend/src/App.jsx](file:///c:/Users/pnlkc/AIProject/NaverCafe/frontend/src/App.jsx#L25))**:
    - `getNormalizedTeamName` 헬퍼를 `utils.js`로 이관 및 `App.jsx`에서 수입하여 인라인 중복 정의 코드 완전 제거.
- **사유:** 코드 가독성 향상, 중복(DRY) 제거 및 유지보수성 극대화.
- **검증 결과:** `verify.js` 자가 검증 및 Vite 빌드 성공 패스 완료.

## [1.1.71/2026-07-22] - [주체: 👔 Project Manager & ⚙️ Backend Developer & 🗄️ DB Administrator & 🎨 Frontend Developer & 🛡️ QA Engineer]
- **작업 내용:**
  - **DB SQLite 동시성 & 잠금 방지 ([backend/database.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/database.py#L15))**:
    - SQLite Connection Timeout 15초 설정 및 `PRAGMA journal_mode=WAL;` 자동 적용으로 동시 쓰기 시 `database is locked` 오류 차단.
    - 30일 초과 데이터 삭제용 `cleanup_old_logs(days=30)` retention 함수 구현.
  - **세션 24시간 사전 만료 알림 ([backend/naver_bot.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/naver_bot.py#L60), [frontend/src/App.jsx](file:///c:/Users/pnlkc/AIProject/NaverCafe/frontend/src/App.jsx#L747))**:
    - `NID_SES` 쿠키 만료 시간을 추적하여 24시간 이내 만료 임박 시 `expiry_warning` 반환 및 대시보드 사이드바 주황색 만료 임박 뱃지 렌더링.
  - **스케줄러 예외 격리 & DB 30일 Cleanup 자동화 ([backend/scheduler.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/scheduler.py#L104))**:
    - 24시간 주기 `_loop_db_cleanup` 백그라운드 태스크 등록 및 자동 정리 수행.
- **사유:** 사용자의 지시에 따른 1~3순위 개선 과제(안전성/사용성/운영성) 반영.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.70/2026-07-21] - [주체: 🎨 Frontend Developer]
- **작업 내용:**
  - **뉴스 보관함 필터 칩 수량 기준 내림차순 정렬 적용 ([frontend/src/App.jsx](file:///c:/Users/pnlkc/AIProject/NaverCafe/frontend/src/App.jsx#L635))**:
    - 뉴스 포스팅 보관함 탭의 카테고리/팀 필터 칩 바에서 `'ALL'` (전체 보기) 칩을 맨 앞에 고정한 뒤, 각 팀 칩들을 수집된 기사 숫자(`count`)가 많은 순서대로 내림차순 정렬.
- **사유:** 수집 기사 건수에 따른 시각적 직관성 및 탐색 편의성 향상.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.69/2026-07-21] - [주체: 🧹 Clean Coder & ⚙️ Backend Developer]
- **작업 내용:**
  - **마크다운(`.md`) 생성 및 파서 코드 전면 완전 삭제 ([backend/news_crawler.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/news_crawler.py#L740), [backend/main.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/main.py#L310))**:
    - 뉴스 크롤링 시 `article.md` 생성 로직 및 수식이 들어간 불필요한 마크다운 파서 코드를 전면 완전 삭제.
    - 정제된 `article.html` 파일 단일 저장 및 단일 HTML 미리보기 렌더링으로 시스템 슬림화 및 리팩토링 완료.
- **사유:** 사용자의 HTML 단일화 지시 및 불필요한 레거시 코드 제거.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.68/2026-07-21] - [주체: ⚙️ Backend Developer & 🎨 Frontend Developer]
- **작업 내용:**
  - **뉴스 미리보기 API HTML 1순위 파싱 변경 ([backend/main.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/main.py#L313))**:
    - 관리자 대시보드 미리보기 모달 렌더링 시 마크다운(`.md`)보다 원본 HTML(`article.html`)을 최우선 1순위로 로드하여 네이버 원문 웹 페이지의 레이아웃과 HTML 구조가 그대로 렌더링되도록 수정.
- **사유:** 관리자 페이지 뉴스 미리보기 시 HTML 원본 렌더링 요구사항 반영.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.67/2026-07-21] - [주체: ⚙️ Backend Developer]
- **작업 내용:**
  - **기사 본문 첨부 이미지 원문 배치 보존 알고리즘 적용 ([backend/news_crawler.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/news_crawler.py#L720))**:
    - 기존 마크다운 하단에 이미지가 몰려서 배치되던 방식을 개편하여, 기사 HTML DOM 순회 시 `<img>` 노드를 원문 단락 위치 그대로 마크다운 이미지 토큰(`![alt](./images/img_X.jpg)`)으로 인플레이스(In-place) 치환.
    - 네이버 원문 기사와 동일하게 단락 사이사이에 이미지가 배치되도록 가시성 및 가독성 개선.
- **사유:** 기사 이미지 본문 레이아웃 원문 일치화 요구사항 반영.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.66/2026-07-21] - [주체: ⚙️ Backend Developer]
- **작업 내용:**
  - **FastAPI 백엔드 런타임 오류(NameError: name 're' is not defined) 해결 ([backend/main.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/main.py#L2))**:
    - `main.py` 파일 상단에 파이썬 정규표현식 모듈 `import re` 구문 추가로 런타임 예외 크래시 전면 해결.
- **사유:** API 서버 런타임 예외 조치.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.65/2026-07-21] - [주체: 🎨 Frontend Developer]
- **작업 내용:**
  - **Vite 변수 중복 선언 구문 오류(PARSE_ERROR) 해결 ([frontend/src/App.jsx](file:///c:/Users/pnlkc/AIProject/NaverCafe/frontend/src/App.jsx#L396))**:
    - `App.jsx` 내 상단에 남아있던 구버전 `filteredArchives` 중복 변수 선언 코드를 완전히 제거하여 Vite 빌드/HMR 파싱 오류 전면 해결.
- **사유:** 프론트엔드 HMR 빌드 에러 해제.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.64/2026-07-21] - [주체: 👔 Project Manager & ⚙️ Backend Developer]
- **작업 내용:**
  - **팀 메타데이터 메인 키 티커(Ticker) 전면 단권화 ([data/teams.json](file:///c:/Users/pnlkc/AIProject/NaverCafe/data/teams.json#L1), [backend/news_crawler.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/news_crawler.py#L102))**:
    - `data/teams.json` 파일의 최상위 Key를 기존 한글명("디플러스", "젠지", "한화생명" 등)에서 공식 티커 약칭(`"DK"`, `"GEN.G"`, `"HLE"`, `"T1"`, `"KT"`, `"FOX"`, `"DNS"`, `"DRX"`, `"BRO"`, `"NS"`)으로 정규화 및 단권화.
    - 기존 한글명들은 `team_names` 검색 동의어 리스트에 포함시켜 기사 검색/수집 및 매칭 기능 100% 보장.
    - `reclassify_teams.py`를 실행하여 DB 아카이브 레코드의 소속 팀을 전면 티커 표준으로 동기화 완료.
- **사유:** 팀명 표기 방식을 공식 e스포츠 티커(Ticker) 표준으로 통일 및 직관성 향상.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.63/2026-07-21] - [주체: 👔 Project Manager & ⚙️ Backend Developer & 🎨 Frontend Developer]
- **작업 내용:**
  - **기사 다중 팀 소속(Multi-Team Tagging) 시스템 전면 도입 ([backend/news_crawler.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/news_crawler.py#L102), [backend/reclassify_teams.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/reclassify_teams.py#L11), [frontend/src/App.jsx](file:///c:/Users/pnlkc/AIProject/NaverCafe/frontend/src/App.jsx#L620))**:
    1. **다중 태그 분류 알고리즘 적용**: 기사 제목 내에 등장하는 모든 팀명/선수/코치를 수집하고 등장 순서대로 쉼표 구분 다중 팀 태그(예: `"디플러스, T1"`)를 생성하도록 `classify_article_team` 확장.
    2. **프론트엔드 다크모드 카테고리 필터링 & 배지 멀티 렌더링**:
       - 다중 태그 헬퍼 `isTeamMatch`를 구현하여 `DK` 탭이나 `T1` 탭 선택 시 해당 기사가 양쪽 탭에 모두 조회되도록 개선.
       - 보관함 기사 카드 및 미리보기 모달 상단 헤더에 `[디플러스]` `[T1]` 개별 팀 배지를 다중 렌더링하도록 UI 정비.
    3. **기존 DB 일괄 재분류 완료**: DB 내 아카이브 레코드를 재분류하여 ID 1번 기사를 포함한 기존 기사들에 `"디플러스, T1"` 등 다중 소속 태그 즉시 반영.
- **사유:** 한 기사에 여러 팀이 언급될 때 다중 태그 및 양쪽 탭 동시 조회 지원 요구사항 충족.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.62/2026-07-21] - [주체: 👔 Project Manager & 🎨 Frontend Developer]
- **작업 내용:**
  - **태그/카테고리 필터링 UI 모듈화 및 재클릭 해제(토글) 기능 구현 ([frontend/src/components/FilterChipGroup.jsx](file:///c:/Users/pnlkc/AIProject/NaverCafe/frontend/src/components/FilterChipGroup.jsx#L12), [frontend/src/App.jsx](file:///c:/Users/pnlkc/AIProject/NaverCafe/frontend/src/App.jsx#L618))**:
    1. `FilterChipGroup` 공통 컴포넌트에 토글 해제 지원(`allowToggleOff`, `defaultKey='ALL'`) 및 선택적 카운트 렌더링 지원 추가.
    2. `archives`(뉴스 보관함) 탭과 `logs`(실시간 이력) 탭의 하드코딩 인라인 필터 칩 루프를 `FilterChipGroup` 공통 컴포넌트로 통합(모듈화).
    3. `members`, `alerts`, `archives`, `logs` 등 모든 관리자 페이지의 태그/카테고리 필터 칩 재클릭 시 선택 해제('ALL' 전체 보기 상태 전환) 연동.
- **사유:** 필터 칩 CSS UI 파편화 해결 및 재클릭 토글 해제 기능 구현.
- **검증 결과:** `npm run build` 번들링 0-에러 및 `verify.js` 자가 검증 통과 완료.

## [1.1.62/2026-07-21] - [주체: 👔 Project Manager & ⚙️ Backend Developer]
- **작업 내용:**
  - **다중 팀명 포함 기사 제목 분류 알고리즘 고도화 ([backend/news_crawler.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/news_crawler.py#L102), [backend/reclassify_teams.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/reclassify_teams.py#L11))**:
    - 기존 단순 딕셔너리 순서(`teams.json` 키 순서) 기반 분류 방식에서, 제목 내 **가장 먼저 등장하는 팀명 위치(First Match Index)**를 핵심 주체로 최우선 채택하도록 `classify_article_team` 알고리즘 개선.
    - (예: `"DK에 0-3 완패... T1 잡은~"` 기사의 경우 `DK`가 앞선 위치에서 등장하므로 `T1` 대신 `디플러스`(DK) 팀으로 정밀 분류).
    - `reclassify_teams.py` 스크립트를 재구동하여 DB 내 기존 아카이브 레코드 일괄 재분류 반영 완료.
- **사유:** 여러 팀이 한 제목에 언급될 때 주체 팀 태그 매칭 정확도 향상.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.61/2026-07-21] - [주체: 🎨 Frontend Developer & ⚙️ Backend Developer]
- **작업 내용:**
  - **관리자 페이지 뉴스 미리보기 깨짐 및 UI/이미지 붕괴 현상 개선 ([backend/main.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/main.py#L286), [frontend/vite.config.js](file:///c:/Users/pnlkc/AIProject/NaverCafe/frontend/vite.config.js#L5), [frontend/src/App.jsx](file:///c:/Users/pnlkc/AIProject/NaverCafe/frontend/src/App.jsx#L1266), [frontend/src/index.css](file:///c:/Users/pnlkc/AIProject/NaverCafe/frontend/src/index.css#L240))**:
    1. **이미지 엑박 및 서빙 경로 교정 (Vite Proxy & Hotlink 방어막)**:
       - Vite 개발 서버(`vite.config.js`)에 백엔드 API 프록시(`/api` -> `http://127.0.0.1:8000`)를 연동하여 이미지 상대 경로 요청 시 발생하던 404 엑박 차단.
       - 이미지 태그에 `referrerpolicy="no-referrer"` 속성을 주입하여 네이버 서버의 Hotlinking 보호(403 Forbidden)를 우회하고, 로컬 이미지가 누락된 경우 `onerror` 방어막으로 깨진 엑박 아이콘이 지저분하게 뜨는 현상 완전 차단.
    2. **백엔드 파일 수집/파싱 우선순위 교정**: 레거시 HTML(`article.html`) 대신 마크다운 원문(`article.md`)을 최우선 탐색 및 정제 파싱하도록 교정하고, HTML만 존재하는 경우 불필요한 script/style/video/svg 태그를 안전하게 정제.
    3. **프론트엔드 다크모드 타이포그래피 및 모달 UI 개선**: 미리보기 모달 너비(`max-w-4xl`), 카테고리/팀 배지, 기사 캡션, 이미지 백그라운드 스케일 효과, 블록 쿼트 및 원문 바로가기 버튼 UI 적용.
- **사유:** 관리자 페이지 뉴스 보관함의 미리보기 모달 UI 깨짐 및 기사 이미지 엑박 문제 완전 해결.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.60/2026-07-21] - [주체: 👔 Project Manager & ⚙️ Backend Developer]
- **작업 내용:**
  - **미분류 기사 수집/알림 중복 방지 및 영구 캐시 도입 ([backend/news_crawler.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/news_crawler.py#L71))**:
    - 미분류 스킵 기사 알림 목록(`notified_unclassified_articles`)을 파일(`data/unclassified_notified.json`)로 영구 연동하도록 개선하여 백엔드 재기동 후에도 이력을 유지.
    - 뉴스 수집 직후 필터링 이전 단계에서 DB 중복 및 영구 미분류 캐시 여부를 사전 체크하도록 전진 배치하여, 이미 수집/알림 처리된 미분류 기사가 반복 재수집되거나 디스코드 경고 알림이 재발송되는 현상 완벽 방지.
- **사유:** 수집 이력 중복 처리 및 반복적 미분류 알림 재발 방지.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.59/2026-07-21] - [주체: 👔 Project Manager & ⚙️ Backend Developer]
- **작업 내용:**
  - **순수 미분류 기사 게시 차단 보강 ([backend/news_crawler.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/news_crawler.py#L503))**:
    - 기사 제목에서 팀명과 e스포츠 대회명(LCK/롤드컵/MSI 등)이 둘 다 전혀 매칭되지 않는 순수 미분류 기사의 경우, 디스코드 알림만 1회 발송하고 카페 자동 게시 대상에서 완전히 스킵(`continue`)되도록 처리 강화.
- **사유:** 비 e스포츠/노이즈 기사의 네이버 카페 무분별 게시 차단.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.58/2026-07-21] - [주체: 👔 Project Manager & 🎨 Frontend Developer & 🧹 Clean Coder]
- **작업 내용:**
  - **수집 데이터 0건 팀 칩 은닉 및 대회 동의어 데드 코드 제거 ([frontend/src/App.jsx](file:///c:/Users/pnlkc/AIProject/NaverCafe/frontend/src/App.jsx#L997), [backend/news_crawler.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/news_crawler.py#L48))**:
    1. 뉴스 보관함 탭의 카테고리 필터 칩 바에서 수집된 기사가 0건인 팀 칩은 화면에 완전히 표시되지 않도록 조건문 단순화(동적 필터 칩 표시 적용).
    2. `news_crawler.py` 내에 남아있던 대회 동의어 하드코딩 딕셔너리 `FALLBACK_TOURNAMENT_SYNONYMS` 전면 영구 삭제 및 `data/tournaments.json` 읽기 구조로 통일.
- **사유:** UI 탐색 직관성 향상 및 소스 코드 데드 코드 전면 정돈.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

## [1.1.57/2026-07-21] - [주체: 👔 Project Manager & 🧹 Clean Coder]
- **작업 내용:**
  - **하드코딩 데드 코드 제거 및 메타데이터 정돈 ([backend/news_crawler.py](file:///c:/Users/pnlkc/AIProject/NaverCafe/backend/news_crawler.py#L45))**:
    - `news_crawler.py` 소스 파일 내부에 484줄 분량으로 거대하게 하드코딩되어 있던 레거시 딕셔너리 `FALLBACK_TEAM_METADATA` 전면 영구 삭제.
    - 메타데이터 관리 주체를 단일 JSON 파일(`data/teams.json`) 및 `load_team_metadata_file()` 로직으로 통합 및 단권화.
    - 소스 코드 크기를 약 1,400줄에서 **910줄**로 약 500줄 이상 경량화 및 다이어트 성공.
- **사유:** 코드 유지보수성 향상 및 데드 코드 전면 청소.
- **검증 결과:** `verify.js` 자가 검증 통과 완료.

---

## 📂 과거 변경 이력 아카이브
* 토큰 절약 및 메모리 최적화를 위해 과거 이력은 아래 아카이브 파일에 보관되어 있습니다:
* [changelog_20260721.md](file:///C:/Users/pnlkc/AIProject/NaverCafe/.harness/archive/changelogs/changelog_20260721.md)
* [changelog_20260721.md](file:///C:/Users/pnlkc/AIProject/NaverCafe/.harness/archive/changelogs/changelog_20260721.md)
* [changelog_20260721.md](file:///C:/Users/pnlkc/AIProject/NaverCafe/.harness/archive/changelogs/changelog_20260721.md)
