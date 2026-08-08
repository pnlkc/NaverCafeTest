import os
import re
import asyncio
from datetime import datetime
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
from backend.news_crawler import NewsCrawler, ARCHIVE_DIR, classify_article_team
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
    
    # 2026시즌 나무위키 실시간 로스터 동적 갱신 트리거
    try:
        crawler = NewsCrawler()
        # 서버 기동이 지연되지 않도록 백그라운드 태스크로 구동
        asyncio.create_task(crawler.update_rosters_from_namuwiki())
    except Exception as e:
        log_event("SYSTEM", "WARNING", f"시작 시점 로스터 자동 갱신 트리거 실패: {str(e)}")
        
    # 백그라운드 스케줄러 기동
    await global_scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    # 백그라운드 스케줄러 정지
    await global_scheduler.stop()

# --- 스케줄러 다음 실행 시각 조회 API ---
@app.get("/api/scheduler/status")
def get_scheduler_status_api():
    return global_scheduler.get_scheduler_status()

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

# --- 대시보드 통계 집계 API ---
@app.get("/api/stats")
def get_dashboard_stats_api(db: Session = Depends(get_db)):
    """한국 시각 기준 매일 00:00:00 이후 당일 실시간 집계 메트릭 숫자를 반환합니다."""
    from backend.database import MemberAction, BoardAlert
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 1. 오늘 실제 카페 게시 완료된 뉴스 건수 (published_at이 존재하는 건만 집계)
    today_news_count = db.query(NewsArchive).filter(
        NewsArchive.published_at >= today_start,
        NewsArchive.published_at.isnot(None)
    ).count()
    total_news_count = db.query(NewsArchive).filter(NewsArchive.published_at.isnot(None)).count()
    
    # 2. 오늘 실제 가입 자동 승인된 회원 인원수 (MemberAction 테이블 레코드 수)
    today_approve_count = db.query(MemberAction).filter(
        MemberAction.action_type == "JOIN_APPROVE",
        MemberAction.processed_at >= today_start
    ).count()
    
    # 3. 오늘 실제 회원 등업 처리된 회원 인원수 (MemberAction 테이블 레코드 수)
    today_levelup_count = db.query(MemberAction).filter(
        MemberAction.action_type == "LEVEL_UP",
        MemberAction.processed_at >= today_start
    ).count()
    
    # 4. 오늘 게시판 알림 감지 수 (신고 및 건의 알림 분리 집계)
    today_report_count = db.query(BoardAlert).filter(
        BoardAlert.board_type == "REPORT",
        BoardAlert.checked_at >= today_start
    ).count()
    today_suggestion_count = db.query(BoardAlert).filter(
        BoardAlert.board_type == "SUGGESTION",
        BoardAlert.checked_at >= today_start
    ).count()
    today_alert_count = today_report_count + today_suggestion_count
    
    return {
        "today_news_count": today_news_count,
        "total_news_count": total_news_count,
        "total_approve_count": today_approve_count,
        "total_levelup_count": today_levelup_count,
        "total_alert_count": today_alert_count,
        "today_report_count": today_report_count,
        "today_suggestion_count": today_suggestion_count
    }



# --- 시스템 로그 및 아카이브 조회 API ---
@app.get("/api/logs")
def get_logs_api(

    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    action_type: str = Query(None),
    status: str = Query(None),
    hide_noise: bool = Query(True),
    today_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    query = db.query(ActionLog)
    if today_only:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(ActionLog.created_at >= today_start)
    
    # 반복적인 자잘한 무반응/스킵 노이즈 로그 제외 처리 (실행, 완료, 오류 등 핵심 로그만 추출)
    if hide_noise:
        noise_keywords = [
            "대기 중인 가입 신청자가 없습니다",
            "등업 대상 회원이 없습니다",
            "새로운 신고 게시글이 없습니다",
            "새로운 건의 게시글이 없습니다",
            "검사를 건너뜁니다"
        ]
        for kw in noise_keywords:
            query = query.filter(~ActionLog.message.contains(kw))

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
    items = query.order_by(NewsArchive.published_at.desc().nullslast(), NewsArchive.id.desc()).offset((page - 1) * limit).limit(limit).all()
    
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
                "cafe_article_url": item.cafe_article_url,
                "team": (item.team if (item.team and item.team != "일반") else classify_article_team(item.title)),
                "published_at": item.published_at.strftime("%Y-%m-%d %H:%M:%S") if item.published_at else None
            } for item in items
        ]
    }

@app.post("/api/archives/{archive_id}/retry-post")
async def retry_archive_post_api(archive_id: int, db: Session = Depends(get_db)):
    """게시 실패 혹은 미발행 상태의 뉴스 기사를 네이버 카페에 재작성(포스팅)합니다."""
    item = db.query(NewsArchive).filter(NewsArchive.id == archive_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="해당 아카이브 기사를 찾을 수 없습니다.")
    
    bot = NaverCafeBot()
    # 카페 뉴스 기사 등록 수행
    post_res = await bot.write_news_article(item.title, item.summary, item.source_url, notify_discord=False)
    
    if post_res.get("status") == "SUCCESS":
        item.cafe_article_url = post_res.get("cafe_article_url")
        item.published_at = datetime.now()
        db.commit()
        log_event("NEWS_POST", "SUCCESS", f"기사 재작성 완료: {item.title}")
        return {
            "status": "SUCCESS",
            "message": "네이버 카페에 게시글 작성이 성공적으로 완료되었습니다!",
            "cafe_article_url": item.cafe_article_url
        }
    else:
        err_msg = post_res.get("message", "카페 게시글 작성 중 오류가 발생했습니다.")
        log_event("NEWS_POST", "FAILED", f"기사 재작성 실패 ({item.title}): {err_msg}")
        return {
            "status": "FAILED",
            "message": f"게시글 작성 실패: {err_msg}"
        }

@app.get("/api/archives/{archive_id}")
def get_archive_detail_api(archive_id: int, db: Session = Depends(get_db)):
    """아카이브 기사 상세 내용을 반환합니다."""
    item = db.query(NewsArchive).filter(NewsArchive.id == archive_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="해당 아카이브를 찾을 수 없습니다.")
    
    content_html = ""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    candidate_files = []
    
    if item.local_path:
        abs_local_path = os.path.join(project_root, item.local_path.replace("/", os.sep))
        if os.path.isfile(abs_local_path):
            candidate_files.append(abs_local_path)
        else:
            candidate_files.append(os.path.join(abs_local_path, "article.html"))
            
    if item.article_id:
        art_dir = os.path.join(ARCHIVE_DIR, item.article_id)
        candidate_files.append(os.path.join(art_dir, "article.html"))

    # 2. 후보 파일 중 존재하는 최우선 파일 파싱
    for file_path in candidate_files:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_content = f.read()
                    
                # article.html 레거시 처리: 불필요한 script, style, video, svg 태그 정제
                cleaned = re.sub(r'<script.*?>.*?</script>', '', raw_content, flags=re.DOTALL | re.IGNORECASE)
                cleaned = re.sub(r'<style.*?>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
                cleaned = re.sub(r'<video.*?>.*?</video>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
                cleaned = re.sub(r'<svg.*?>.*?</svg>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
                cleaned = re.sub(r'<iframe.*?>.*?</iframe>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
                
                # _article_content 내부 콘텐츠만 추출 시도
                content_match = re.search(r'<div[^>]*class=["\'].*?_article_content.*?["\'][^>]*>(.*?)</div>', cleaned, flags=re.DOTALL | re.IGNORECASE)
                if content_match:
                    content_html = content_match.group(1)
                else:
                    # body 내부만 추출 시도
                    body_match = re.search(r'<body[^>]*>(.*?)</body>', cleaned, flags=re.DOTALL | re.IGNORECASE)
                    content_html = body_match.group(1) if body_match else cleaned
                        
                if content_html and content_html.strip():
                    break
            except Exception:
                continue

    # 3. 로컬 파일이 없거나 읽기 실패 시 DB summary 기반 고품질 Fallback HTML 생성
    if not content_html:
        summary_text = (item.summary or "기사 요약 정보가 없습니다.").replace("\n", "<br/>")
        content_html = f"""
        <div class="article-fallback-card">
            <h3 class="fallback-header">📰 기사 본문 요약</h3>
            <p class="fallback-body">{summary_text}</p>
            <div class="fallback-footer">
                <a href="{item.source_url or '#'}" target="_blank" rel="noreferrer" class="fallback-link">
                    🔗 네이버 스포츠 원문 기사 보러가기 ↗
                </a>
            </div>
        </div>
        """

    # 이미지 경로를 서빙 가능한 API URL로 변환 (./images/img_1.jpg 또는 images/img_1.jpg → /api/archive-image/...)
    if content_html and item.article_id:
        target_api_url = f'/api/archive-image/{item.article_id}/'
        # 상대 경로 치환
        content_html = content_html.replace('./images/', target_api_url).replace('images/', target_api_url)
        # 이미지 태그에 referrerpolicy 및 onerror 방어막 적용 (네이버 핫링크 403 차단 및 엑박 방지)
        content_html = re.sub(
            r'<img([^>]+)src=["\']([^"\']+)["\']([^>]*)>',
            lambda m: f'<img{m.group(1)}src="{m.group(2)}"{m.group(3)} referrerpolicy="no-referrer" onerror="this.onerror=null; this.style.display=\'none\';" />' if 'referrerpolicy' not in m.group(0) else m.group(0),
            content_html
        )
    
    return {
        "id": item.id,
        "article_id": item.article_id,
        "title": item.title,
        "summary": item.summary,
        "source_url": item.source_url,
        "team": item.team or "일반",
        "cafe_article_url": item.cafe_article_url,
        "published_at": item.published_at.strftime("%Y-%m-%d %H:%M:%S") if item.published_at else None,
        "content_html": content_html
    }

@app.get("/api/archive-image/{article_id}/{filename}")
def get_archive_image(article_id: str, filename: str):
    """아카이브 기사의 로컬 이미지 파일을 서빙합니다."""
    image_path = os.path.join(ARCHIVE_DIR, article_id, "images", filename)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    return FileResponse(image_path)

@app.get("/api/member-actions")
def get_member_actions_api(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    action_type: str = Query(None), # JOIN_APPROVE, LEVEL_UP
    today_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    from backend.database import MemberAction
    query = db.query(MemberAction)
    if action_type:
        query = query.filter(MemberAction.action_type == action_type)
    if today_only:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(MemberAction.processed_at >= today_start)
        
    total = query.count()
    items = query.order_by(MemberAction.processed_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [
            {
                "id": item.id,
                "action_type": item.action_type,
                "nickname": item.nickname,
                "requested_at": item.requested_at,
                "processed_at": item.processed_at.strftime("%Y-%m-%d %H:%M:%S")
            } for item in items
        ]
    }

@app.get("/api/board-alerts")
def get_board_alerts_api(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    board_type: str = Query(None), # REPORT, SUGGESTION
    today_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    from backend.database import BoardAlert
    query = db.query(BoardAlert)
    if board_type:
        query = query.filter(BoardAlert.board_type == board_type)
    if today_only:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(BoardAlert.checked_at >= today_start)
        
    total = query.count()
    items = query.order_by(BoardAlert.checked_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [
            {
                "id": item.id,
                "board_type": item.board_type,
                "article_id": item.article_id,
                "title": item.title,
                "writer": item.writer,
                "written_at": item.written_at,
                "checked_at": item.checked_at.strftime("%Y-%m-%d %H:%M:%S"),
                "article_url": item.article_url
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
