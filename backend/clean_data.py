import os
import shutil
import sys

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, NewsArchive, MemberAction, BoardAlert, ActionLog
from backend.logger import log_event

def clean_data():
    print("[작업 시작] 시스템 전체 데이터 및 아카이브 초기화 작업을 시작합니다.")
    log_event("CLEAN_DATA", "INFO", "운영자에 의한 시스템 전체 데이터 수동 초기화 작업을 시작합니다.")
    
    # 1. DB 모든 레코드 삭제
    try:
        db = SessionLocal()
        deleted_news = db.query(NewsArchive).delete()
        deleted_members = db.query(MemberAction).delete()
        deleted_alerts = db.query(BoardAlert).delete()
        deleted_logs = db.query(ActionLog).delete()
        
        db.commit()
        db.close()
        
        msg = f"DB 데이터 전량 삭제 완료 (뉴스: {deleted_news}건, 회원액션: {deleted_members}건, 알림: {deleted_alerts}건, 로그: {deleted_logs}건 삭제)"
        print(f"[성공] {msg}")
        # 초기화가 끝났으므로 해당 성공 로그는 새로 기록하여 히스토리를 남김
        log_event("CLEAN_DATA", "SUCCESS", msg)
    except Exception as e:
        msg = f"DB 레코드 삭제 실패: {str(e)}"
        print(f"[실패] {msg}")
        log_event("CLEAN_DATA", "FAILED", msg)
        
    # 2. 로컬 아카이브 폴더 삭제 (data/archive/)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    archive_dir = os.path.join(base_dir, "data", "archive")
    
    if os.path.exists(archive_dir):
        try:
            for filename in os.listdir(archive_dir):
                file_path = os.path.join(archive_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"Warning: {file_path} 삭제 실패: {e}")
            msg = "로컬 data/archive/ 하위 파일 및 폴더 삭제 완료"
            print(f"[성공] {msg}")
            log_event("CLEAN_DATA", "SUCCESS", msg)
        except Exception as e:
            msg = f"로컬 아카이브 폴더 정리 실패: {str(e)}"
            print(f"[실패] {msg}")
            log_event("CLEAN_DATA", "FAILED", msg)
    else:
        print("[정보] 로컬 data/archive/ 폴더가 존재하지 않아 스킵합니다.")
        
    print("[작업 완료] 모든 데이터 및 아카이브가 깨끗하게 초기화되었습니다.")

if __name__ == "__main__":
    clean_data()
