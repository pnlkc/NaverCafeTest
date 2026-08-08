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

    # 2. 콘솔 핸들러 (개발 및 모니터링 콘솔 출력)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

def log_event(action_type: str, status: str, message: str) -> None:
    """
    일반인 사용자가 보기 쉬운 한글 포맷으로 텍스트 로그 파일과 DB에 기록합니다.
    """
    category_label = ACTION_LABEL_MAP.get(action_type, f"📌 {action_type}")
    status_label = STATUS_LABEL_MAP.get(status, status)
    
    log_msg = f"[{status_label}] {category_label} | {message}"
    
    if status in ["SUCCESS", "INFO"]:
        logger.info(log_msg)
    elif status == "WARNING":
        logger.warning(log_msg)
    else:
        logger.error(log_msg)
    
    # DB 로그 기록
    log_action(action_type, status, message)

