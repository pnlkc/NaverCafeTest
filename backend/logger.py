import os
import logging
from logging.handlers import RotatingFileHandler
from backend.database import log_action

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
    # 포맷 지정
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)d] - %(message)s",
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
    텍스트 로그 파일과 SQLite 데이터베이스에 이벤트를 동시에 기록합니다.
    """
    log_msg = f"[{action_type}] [{status}] {message}"
    if status in ["SUCCESS", "INFO"]:
        logger.info(log_msg)
    elif status == "WARNING":
        logger.warning(log_msg)
    else:
        logger.error(log_msg)
    
    # DB 로그 기록
    log_action(action_type, status, message)

    # 디스코드 작업 로그 채널 실시간 알림 전송 (단, 알림 자체 로그 및 루프성 로그 제외)
    if action_type not in ["DISCORD_NOTIFY", "SYSTEM", "BOARD_MONITOR"]:
        try:
            from backend.discord_notifier import notify_action_log
            notify_action_log(action_type, status, message)
        except Exception:
            pass
