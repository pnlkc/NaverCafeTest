import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker

# DB 파일 저장 경로
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "database.sqlite")

if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)

# SQLAlchemy 설정
DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 15})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ActionLog(Base):
    __tablename__ = "action_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String(50), nullable=False)  # JOIN_APPROVE, LEVEL_UP, NEWS_POST, ALERT, ERROR 등
    status = Column(String(20), nullable=False)       # SUCCESS, FAILED
    message = Column(Text, nullable=True)             # 상세 메시지
    created_at = Column(DateTime, default=datetime.now)

class NewsArchive(Base):
    __tablename__ = "news_archives"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    summary = Column(Text, nullable=True)
    source_url = Column(String(500), nullable=False)
    local_path = Column(String(500), nullable=True)    # 로컬 data/archive/{article_id}/ 상대경로
    cafe_article_url = Column(String(500), nullable=True)  # 네이버 카페 등록 후 아웃링크 URL
    team = Column(String(50), nullable=True)  # 소속 팀 분류 (T1, DK, 일반 등)
    published_at = Column(DateTime, nullable=True)  # 실제 카페 게시 완료 시각 (None=미발행)

class MemberAction(Base):
    __tablename__ = "member_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String(50), nullable=False)  # JOIN_APPROVE, LEVEL_UP
    nickname = Column(String(100), nullable=False)
    requested_at = Column(String(50), nullable=True)  # 유저가 신청한 시간 (가입신청일 등)
    processed_at = Column(DateTime, default=datetime.now) # 봇이 처리/승인한 시간

class BoardAlert(Base):
    __tablename__ = "board_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    board_type = Column(String(50), nullable=False)   # REPORT, SUGGESTION
    article_id = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    writer = Column(String(100), nullable=False)
    written_at = Column(String(50), nullable=False)   # 새글 등록 시간 (네이버 스포츠/카페 파싱 시각)
    checked_at = Column(DateTime, default=datetime.now) # 봇이 확인하고 알림 발송 완료한 시각
    article_url = Column(String(500), nullable=True)

# 테이블 생성
def init_db():
    Base.metadata.create_all(bind=engine)
    
    # SQLite WAL 모드 적용으로 동시성 향상
    try:
        with engine.begin() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL;"))
    except Exception as pragma_err:
        print(f"[DB WAL Warning] WAL 모드 설정 경고: {pragma_err}")
    
    # news_archives 테이블에 cafe_article_url 컬럼이 없는 경우 자동 마이그레이션 적용
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("news_archives")]
        if "cafe_article_url" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE news_archives ADD COLUMN cafe_article_url VARCHAR(500)"))
            print("[DB Migration] news_archives 테이블에 cafe_article_url 컬럼을 자동 신설했습니다.")
        if "team" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE news_archives ADD COLUMN team VARCHAR(50)"))
            print("[DB Migration] news_archives 테이블에 team 컬럼을 자동 신설했습니다.")
    except Exception as e:
        print(f"[DB Migration Warning] 마이그레이션 검사 실패: {e}")

def get_db():
    """FastAPI Dependency 용 DB 세션 획득"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def log_action(action_type: str, status: str, message: str) -> None:
    """작업 이력을 데이터베이스에 기록합니다."""
    db = SessionLocal()
    try:
        log_entry = ActionLog(
            action_type=action_type,
            status=status,
            message=message,
            created_at=datetime.now()
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[DB Log Error] DB 로그 기록 실패: {e}")
    finally:
        db.close()

def cleanup_old_logs(days: int = 30) -> int:
    """지정한 일수(기본 30일)를 초과한 오래된 action_logs 및 board_alerts 레코드를 자동 정리합니다."""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)
    db = SessionLocal()
    deleted_count = 0
    try:
        deleted_logs = db.query(ActionLog).filter(ActionLog.created_at < cutoff).delete()
        deleted_alerts = db.query(BoardAlert).filter(BoardAlert.checked_at < cutoff).delete()
        db.commit()
        deleted_count = (deleted_logs or 0) + (deleted_alerts or 0)
        if deleted_count > 0:
            print(f"[DB Cleanup] {days}일 초과 데이터 레코드 {deleted_count}건 정리를 완료했습니다.")
    except Exception as e:
        db.rollback()
        print(f"[DB Cleanup Error] 로그 cleanup 작업 실패: {e}")
    finally:
        db.close()
    return deleted_count
