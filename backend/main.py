import os
import asyncio
from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.config import load_settings, save_settings, AppSettings
from backend.database import init_db, get_db, ActionLog, NewsArchive, log_action
from backend.logger import log_event
from backend.naver_bot import NaverCafeBot, SESSION_PATH
from backend.news_crawler import NewsCrawler, ARCHIVE_DIR
from backend.scheduler import global_scheduler
from backend.discord_notifier import send_discord_webhook

# FastAPI 앱 기동
app = FastAPI(title="Naver Cafe Auto Manager API", version="1.0.0")

# CORS 설정 (프론트엔드 로컬 개발 시 CORS 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 초기화 및 스케줄러 자동 실행 (startup 이벤트)
@app.on_event("startup")
async def startup_event():
    init_db()
    log_event("SYSTEM", "SUCCESS", "SQLite 데이터베이스 초기화가 완료되었습니다.")
    
    # 백그라운드 스케줄러 기동
    await global_scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    # 백그라운드 스케줄러 정지
    await global_scheduler.stop()

# --- 설정 관리 API ---
@app.get("/api/settings", response_model=AppSettings)
def get_settings_api():
    return load_settings()

@app.post("/api/settings")
def update_settings_api(settings: AppSettings):
    success = save_settings(settings)
    if success:
        log_event("SYSTEM", "SUCCESS", "시스템 설정이 업데이트되었습니다.")
        return {"status": "SUCCESS", "message": "설정이 성공적으로 저장되었습니다."}
    else:
        raise HTTPException(status_code=500, detail="설정 저장 실패")

# --- 세션 관리 API ---
@app.get("/api/session/status")
async def get_session_status_api():
    bot = NaverCafeBot()
    return await bot.get_session_status()

# 수동 로그인 트리거용 백그라운드 래퍼
async def run_login_task():
    bot = NaverCafeBot()
    await bot.run_manual_login()

@app.post("/api/session/login")
def trigger_manual_login(background_tasks: BackgroundTasks):
    # 로그인 세션 획득은 브라우저 팝업을 띄우므로 비동기 백그라운드 작업으로 실행
    background_tasks.add_task(run_login_task)
    return {"status": "SUCCESS", "message": "로그인 브라우저를 백그라운드에서 기동했습니다. 서버 콘솔 혹은 팝업을 확인하세요."}

# --- 수동 제어(즉시 실행) API ---
@app.post("/api/action/join-approve")
async def run_join_approve_now():
    bot = NaverCafeBot()
    res = await bot.approve_join_requests()
    return res

@app.post("/api/action/level-up")
async def run_level_up_now():
    bot = NaverCafeBot()
    res = await bot.check_and_levelup()
    return res

@app.post("/api/action/news-publish")
async def run_news_publish_now(background_tasks: BackgroundTasks):
    # 크롤링 및 글쓰기는 시간이 걸리므로 백그라운드 태스크로 구동하고 응답 반환
    async def run_crawl():
        crawler = NewsCrawler()
        await crawler.collect_and_process_news()
        
    background_tasks.add_task(run_crawl)
    return {"status": "SUCCESS", "message": "뉴스 기사 수집 및 자동 발행 작업을 개시했습니다."}

@app.post("/api/action/test-discord")
def run_test_discord():
    fields = {
        "알림 테스트": "성공",
        "서버 시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    # 파랑/녹색 계열 Embed 테스트 발송
    success = send_discord_webhook("🔔 [시스템 알림] 디스코드 웹훅 연결 테스트 성공", fields, color=3066993)
    if success:
        return {"status": "SUCCESS", "message": "테스트 알림 발송 완료"}
    else:
        raise HTTPException(status_code=500, detail="디스코드 발송 실패 (URL 확인 요망)")

# --- 시스템 로그 및 아카이브 조회 API ---
@app.get("/api/logs")
def get_logs_api(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    action_type: str = Query(None),
    status: str = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(ActionLog)
    
    if action_type:
        query = query.filter(ActionLog.action_type == action_type)
    if status:
        query = query.filter(ActionLog.status == status)
        
    total = query.count()
    logs = query.order_by(ActionLog.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [
            {
                "id": log.id,
                "action_type": log.action_type,
                "status": log.status,
                "message": log.message,
                "created_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S")
            } for log in logs
        ]
    }

@app.get("/api/archives")
def get_archives_api(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    query = db.query(NewsArchive)
    total = query.count()
    items = query.order_by(NewsArchive.published_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [
            {
                "id": item.id,
                "article_id": item.article_id,
                "title": item.title,
                "summary": item.summary,
                "source_url": item.source_url,
                "local_path": item.local_path,
                "published_at": item.published_at.strftime("%Y-%m-%d %H:%M:%S")
            } for item in items
        ]
    }

@app.get("/api/archives/{article_id}/html")
def get_archive_html_api(article_id: str):
    """아카이빙된 뉴스 원본 HTML 문서를 반환합니다."""
    html_path = os.path.join(ARCHIVE_DIR, article_id, "article.html")
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="아카이브 파일을 찾을 수 없습니다.")
    return FileResponse(html_path)

@app.get("/api/archives/{article_id}/images/{img_name}")
def get_archive_image_api(article_id: str, img_name: str):
    """아카이빙된 로컬 이미지 리소스를 직접 서빙합니다."""
    img_path = os.path.join(ARCHIVE_DIR, article_id, "images", img_name)
    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="이미지 파일을 찾을 수 없습니다.")
    return FileResponse(img_path)

# --- 프론트엔드 정적 파일 서빙 ---
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")

if os.path.exists(FRONTEND_DIR):
    # 빌드된 dist 폴더 마운트
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")
    
    # Catch-all 라우터: API 이외의 요청에 대해 dist/index.html 반환 (SPA 라우팅 지원)
    @app.get("/{catchall:path}")
    def serve_frontend(catchall: str):
        if catchall.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "API Not Found"})
        index_file = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return JSONResponse(status_code=404, content={"detail": "Frontend Not Built"})
else:
    @app.get("/{catchall:path}")
    def serve_placeholder(catchall: str):
        if catchall.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "API Not Found"})
        return JSONResponse(
            status_code=200, 
            content={"message": "FastAPI 백엔드가 가동 중입니다. 프론트엔드 빌드 결과물(frontend/dist)이 아직 생성되지 않았습니다."}
        )
