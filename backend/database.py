import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# DB 파일 저장 경로
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "database.sqlite")

if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)

# SQLAlchemy 설정
DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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
    published_at = Column(DateTime, default=datetime.now)

# 테이블 생성
def init_db():
    Base.metadata.create_all(bind=engine)

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
