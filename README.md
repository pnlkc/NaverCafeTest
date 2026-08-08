# ☕ Naver Cafe Auto Manager (네이버 카페 자동 관리 시스템)

LCK e스포츠 네이버 카페 관리를 자동화하는 종합 관리 시스템입니다.  
회원 가입 승인, 조건별 등업, 신고/건의 게시글 실시간 디스코드 알림, LCK 뉴스 자동 수집 및 포스팅 기능과 한눈에 현황을 파악할 수 있는 **웹 대시보드**를 제공합니다.

---

## 📌 주요 기능

* **자동 가입 승인**: 질문/답변 조건 검사 후 대기 중인 회원 자동 승인
* **자동 회원 등업**: 조건(방문 횟수, 덧글 수, 작성글 수 등) 충족 회원 자동 등업
* **실시간 게시판 감시**: 신고 게시판 및 건의 사항 게시판 실시간 모니터링 및 디스코드 웹훅 알림
* **LCK 뉴스 수집 & 자동 포스팅**: 네이버 스포츠 LCK 기사 수집, 팀별 분류, 3줄 요약 생성 및 카페 자동 게시
* **웹 대시보드 UI**: 실시간 당일 집계 메트릭, 스케줄러 상태, 시스템 작업 로그 및 기사 아카이브 조회

---

## 📁 프로젝트 구조

```text
NaverCafe/
├── backend/                  # Python FastAPI 백엔드
│   ├── main.py               # API 엔드포인트 및 서버 메인 entrypoint
│   ├── naver_bot.py          # Playwright 기반 네이버 카페 자동화 봇
│   ├── news_crawler.py       # 네이버 스포츠 LCK 뉴스 크롤러 및 요약기
│   ├── scheduler.py          # 백그라운드 주기적 작업 스케줄러
│   ├── database.py           # SQLite DB 모델 및 세션 관리
│   └── logger.py             # 시스템 로그 관리 모듈
├── data/                     # DB 파일 및 크롤링 아카이브 (공유 대상 제외)
├── watchdog.py               # 서버 프로세스 감시 및 자동 재기동 래퍼
├── run.bat                   # 윈도우(Windows) 전용 원클릭 실행 스크립트
├── run.sh                    # 맥(macOS / Linux) 전용 실행 스크립트
├── requirements.txt          # 파이썬 의존성 패키지 목록
├── .env.example              # 환경변수 설정 템플릿 파일
└── README.md                 # 프로젝트 문서
```

---

## ⚙️ 사전 준비사항 (Prerequisites)

* **Python**: 3.10 이상 권장
* **Git**

---

## 🚀 환경 설정 (.env)

1. 저장소를 클론(Clone)하거나 다운로드합니다.
2. 프로젝트 루트에 있는 `.env.example` 파일을 복사하여 `.env` 파일을 생성합니다.
   ```bash
   cp .env.example .env   # macOS / Linux
   copy .env.example .env # Windows CMD
   ```
3. `.env` 파일을 열어 본인의 네이버 계정 정보, 디스코드 Webhook URL, 카페 게시판 ID 등을 설정합니다.

---

## 💻 OS별 실행 방법

### 🪟 Windows (윈도우)

1. **의존성 패키지 및 크롤링 브라우저 설치**:
   터미널(CMD 또는 PowerShell)을 열고 아래 명령어를 실행합니다.
   ```cmd
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **서버 및 대시보드 실행**:
   * **방법 1 (원클릭)**: 프로젝트 폴더의 `run.bat` 파일 더블 클릭
   * **방법 2 (터미널)**:
     ```cmd
     run.bat
     ```
     또는
     ```cmd
     python watchdog.py
     ```

---

### 🍎 macOS (맥)

1. **의존성 패키지 및 크롤링 브라우저 설치**:
   터미널(Terminal)을 열고 아래 명령어를 실행합니다.
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **`run.sh` 실행 권한 부여** (최초 1회 실행):
   ```bash
   chmod +x run.sh
   ```

3. **서버 및 대시보드 실행**:
   ```bash
   ./run.sh
   ```
   또는
   ```bash
   python3 watchdog.py
   ```

---

## 🌐 대시보드 접속

시스템이 정상 구동되면 브라우저에서 아래 주소로 접속합니다.

* **🖥️ 웹 대시보드 UI**: [http://localhost:5173](http://localhost:5173) (또는 `http://localhost:5173/#dashboard`)
* **📑 백엔드 API 문서**: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
  *(※ 8000번 포트는 백엔드 API 전용 서버로, UI 접속은 5173 포트를 이용하시면 됩니다)*

---

## 🔒 보안 및 주의사항

* `.env` 파일 및 `session.json`, `data/` 디렉터리에는 개인 네이버 로그인 세션 쿠키와 디스코드 Webhook URL 등의 민감한 정보가 포함되므로 **Git 저장소나 외부에 공유되지 않도록 주의**하세요. (기본적으로 `.gitignore`에 등록되어 있습니다)
