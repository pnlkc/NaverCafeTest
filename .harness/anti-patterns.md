# 🚫 프로젝트 로컬 안티패턴 (Project-Specific Anti-Patterns)

본 문서는 Naver Cafe Auto Manager 프로젝트에서 발견된 고유의 시행착오, 비즈니스 도메인 제약사항 및 런타임 결함 사례를 기록하여 재발을 방지합니다.

---

## 1. Playwright Locator 단독 await 오용
* **[현상]:** 
  - `object Locator can't be used in 'await' expression` 런타임 에러 발생 및 스케줄러/등업 모듈 다운.
* **[원인]:** 
  - Playwright 비동기 API에서 `page.locator(...).first` 등의 Locator 객체 획득 자체는 동기적 리턴 오브젝트이므로 `await`를 사용할 수 없음.
* **[예방책]:** 
  - Locator 객체를 받아올 때는 `await` 없이 `btn = page.locator("...")` 로 참조를 획득하고, 클릭이나 입력 등 실제 액션을 가할 때 비로소 `await btn.click()` 처럼 await를 적용할 것.

## 2. 뉴스 수집 시 CSS Module 해시 클래스 의존
* **[현상]:** 
  - 네이버 e스포츠 뉴스 크롤링 시 `총 0개의 기사 후보를 수집했습니다` 경고 메시지와 함께 기사 수집 불능.
* **[원인]:** 
  - 네이버 e스포츠 페이지의 CSS 모듈 컴파일 해시값(`news_card_link__*`)이 빌드 시점에 유동적으로 변경되거나 개편되면서, 하드코딩된 해시 클래스 셀렉터가 깨짐.
* **[예방책]:** 
  - 해시가 포함된 컴파일 클래스명 대신, 기사 상세 주소 패턴인 `/article/` 또는 `/esports/article/` 등의 상시 고정 href를 포함하는 범용 CSS 속성 셀렉터(`a[href*="/article/"]:not([class*="mostview"])`)와 태그 셀렉터(`strong`)를 활용하여 크롤링 견고성을 확보할 것.

## 3. 기사 상세 본문 수집 시 모바일 및 반응형 뷰포트 셀렉터 누락
* **[현상]:**
  - 뉴스 필터링 성공 후 개별 기사 본문을 수집하는 과정에서 `기사 본문 요소를 찾지 못했습니다` 경고와 함께 기사 수집 무산.
* **[원인]:**
  - 네이버 e스포츠 상세 페이지가 모바일 반응형 페이지(`m.sports.naver.com`)로 리다이렉트되어 열리면서, 기존 PC 기반 `#newsct_article` 셀렉터 매칭이 실패하고 React 컴파일 클래스명인 `div[class*='NewsEnd_article_body']` 등으로 변경됨.
* **[예방책]:**
  - 상세 본문 추출을 수행할 때 `#newsct_article`, `.news_end` 등의 전통적 ID/클래스 외에 모바일/반응형 스포츠 랩퍼인 `div[class*='NewsEnd_article_body']`, `div[class*='article_body']`, `#newsct` 등을 합산한 광역 셀렉터를 구성하여 파싱 성공률을 제고할 것.

## 4. 나무위키 크롤러의 비동기 중복 트리거
* **[현상]:**
  - 서버 startup 이벤트 가동 시점과 스케줄러의 기사 수집 주기가 겹치면서, 동일 시점에 `update_rosters_from_namuwiki` 크롤링 태스크가 병렬로 2회 중복 실행되어 자원 낭비 및 IP 차단 위험 발생.
* **[원인]:**
  - 비동기 태스크 가동 전 상호 배제(Mutex) 처리가 설계되어 있지 않아 동일 시점의 트리거가 물리 브라우저 인스턴스를 무차별적으로 다중 실행함.
* **[예방책]:**
  - 모듈 전역 스케일의 락 플래그 `_is_updating_roster` 를 선언하여 실행 시 검사하고, 기동 중일 때는 중복 실행을 즉시 스킵(회피)한 뒤 `finally` 블록에서 플래그를 정직하게 릴리즈할 것.

## 5. 네이버 카페 구형 URL(ArticleRead.nhn 등) 의존
* **[현상]:**
  - 카페 게시판 탐색, 게시글 읽기 및 글쓰기 조작 시 302 리다이렉트 발생 또는 스마트에디터 ONE 입력 필드를 포착하지 못해 `Timeout 30000ms exceeded` 발생.
* **[원인]:**
  - 네이버 카페가 개편된 신형 FE 웹 구조(`https://cafe.naver.com/f-e/cafes/...`)로 마이그레이션되었음에도 불구하고 과거 모바일/PC 구형 주소(`ArticleRead.nhn`, `ArticleList.nhn`, `ArticleWrite.nhn`)에 의존함.
* **[예방책]:**
  - 카페 게시판/게시글/글쓰기 URL 주소 구성 시 구형 nhn 주소 대신 공식 신형 FE 규격인 `https://cafe.naver.com/f-e/cafes/{club_id}/menus/{menu_id}`, `https://cafe.naver.com/f-e/cafes/{club_id}/articles/{article_id}` 및 신형 에디터 뷰(`https://cafe.naver.com/ca-fe/web/cafes/{club_id}/menus/{menu_id}/articles/write`)를 우선 적용하고 `config.py` 빌더에서 통일 보장할 것.

## 6. 네이버 로그인 CAPTCHA/OTP 자동화 우회 시도
* **[현상]:**
  - 네이버 계정/비밀번호를 사용하여 Playwright로 완전 자동 로그인을 시도할 때 지속적으로 기기 인증 및 캡차 차단 발생.
## 7. 스마트에디터 ONE 등록 클릭 후 조기 브라우저 종료 (글 유실/임시저장함 유입)
* **[현상]:**
  - 로그상에는 기사 등록 성공 메시지가 표시되지만, 실제 카페에는 게시글이 작성되지 않고 임시저장함에 들어감.
* **[원인]:**
  - 스마트에디터 ONE의 등록 버튼 클릭 후 백엔드 AJAX/Form 제출 및 페이지 전환이 완료되기 전 `browser.close()`가 조기 호출되어 미완료 처리됨.
* **[예방책]:**
  - 등록 버튼 클릭 후 `page.wait_for_function("() => !location.href.includes('write')", timeout=7000)` 및 `wait_for_timeout`을 통해 페이지 이동 또는 서버 제출 완수를 반드시 보장하고 브라우저를 닫을 것.

## 8. '등록' 텍스트 부분 매칭(has-text)으로 인한 '임시등록' 버튼 오클릭
* **[현상]:**
  - 게시글 등록 시 `button:has-text('등록')` 지정 시, 우측의 정식 [등록] 버튼 대신 왼쪽/중간의 [임시등록] 버튼을 누르는 불상사 발생.
* **[원인]:**
  - '임시등록' 문자열 내에 '등록' 서브스트링이 포함되어 있어 Playwright의 `has-text` 지정 시 임시등록 버튼이 먼저 매칭됨.
* **[예방책]:**
  - 등록 버튼 지정 시 반드시 `:not(:has-text('임시'))` 제척 조건 또는 정식 클래스명(`button.BaseButton--skinGreen`)을 결합하여 정식 [등록] 버튼만을 핀포인트 타겟팅할 것.

## 9. 스마트에디터 ONE 비가시 클립보드 div (`aria-hidden="true"`) 타겟팅으로 인한 입력 실패
* **[현상]:**
  - 본문 `[contenteditable='true']` 셀렉터 지정 시 `Outside of viewport` 및 본문 미입력 상태 발생.
* **[원인]:**
  - 스마트에디터 ONE의 맨 앞 DOM 요소로 `aria-hidden="true"` 인 클립보드 전용 숨김 div가 존재하여 `.first` 선택 시 비가시 요소를 조작하려 함.
## 10. URL 접두어 검약 시 이모지 서브스트링 누락으로 인한 링크 생략
* **[현상]:**
  - 뉴스 본문 하단에 원문 출처 링크가 생성되지 않고 이모지 기호만 남음.
* **[원인]:**
  - `line.startswith("http")` 검사 시 라인 맨 앞에 이모지(`🔗 `)가 붙어 있어 서브스트링 조건이 `False`로 취급되어 URL 키보드 입력을 스킵함.
* **[예방책]:**
  - URL 검사 시 `startswith` 대신 `"http://" in line` 또는 `"https://" in line` 서브스트링 포함 검사를 활용하여 이모지가 포함된 라인에서도 URL을 100% 추출할 것.

