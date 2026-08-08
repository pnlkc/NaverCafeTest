import os
import logging
from logging.handlers import RotatingFileHandler
from backend.database import log_action

# 일반 사용자 친화적 한글 카테고리 매핑
ACTION_LABEL_MAP = {
    "JOIN_APPROVE": "👥 카페 가입 승인",
    "LEVEL_UP": "⭐ 회원 조건 등업",
    "NEWS_SCRAPING": "📰 뉴스 기사 수집",
    "NEWS_PUBLISH": "🚀 뉴스 자동 발행",
    "BOARD_MONITOR": "🔔 게시판 실시간 감시",
    "SCHEDULER": "⚙️ 자동 스케줄러",
    "SYSTEM": "🖥️ 시스템 제어"
}

STATUS_LABEL_MAP = {
    "SUCCESS": "성공",
    "INFO": "안내",
    "WARNING": "주의",
    "FAILED": "오류",
    "ERROR": "오류"
}

# 로그 저장 경로 설정
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

LOG_PATH = os.path.join(LOG_DIR, "app.log")

# 로거 생성
logger = logging.getLogger("naver_cafe_auto_manager")
logger.setLevel(logging.INFO)

# 이미 핸들러가 설정되어 있다면 중복 방지
if not logger.handlers:
    # 사용자 친화적 깔끔한 날짜-시간 포맷
    formatter = logging.Formatter(
        "[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. 파일 핸들러 (5MB 단위 로테이션, 최대 5개 유지)
    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    # 2. 콘솔 핸들러 (실패/오류/경고 및 주요 결과 요약만 콘솔에 출력하여 콘솔 노이즈 제거)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

def log_event(action_type: str, status: str, message: str) -> None:
    """
    텍스트 로그 파일(app.log)과 DB에는 모든 이력을 남기되,
    콘솔 터미널에는 실패/오류/경고 및 주요 요약 성공 결과만 깨끗하게 출력합니다.
    """
    category_label = ACTION_LABEL_MAP.get(action_type, f"📌 {action_type}")
    status_label = STATUS_LABEL_MAP.get(status, status)
    
    log_msg = f"[{status_label}] {category_label} | {message}"
    
    # 1. 파일 로그(app.log) 및 DB에는 모든 이력(INFO 포함) 기록
    file_handler.handle(logging.LogRecord("naver_cafe_auto_manager", logging.INFO, "", 0, log_msg, (), None))
    log_action(action_type, status, message)
    
    # 2. 콘솔 터미널 출력 필터링 (오류/경고/실패이거나, 주요 '완료/성공' 요약 메시지만 콘솔 출력)
    is_critical_or_summary = (
        status in ["WARNING", "FAILED", "ERROR"] or
        "완료" in message or "성공" in message or "발행" in message
    )
    # 자잘한 루프 진행/접속 단순 INFO 로그는 콘솔 출력 스킵
    is_routine_info = any(kw in message for kw in ["접속합니다", "확인 중", "수집을 시작합니다", "조회를 위해", "로스터 수집 중"])
    
    if is_critical_or_summary and not (is_routine_info and status == "INFO"):
        console_handler.handle(logging.LogRecord("naver_cafe_auto_manager", logging.INFO, "", 0, log_msg, (), None))

