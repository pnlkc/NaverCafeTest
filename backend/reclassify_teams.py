import sys
import os

# 백엔드 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, NewsArchive
from backend.news_crawler import classify_article_team
from backend.logger import log_event

def reclassify_all_news_teams():
    """DB에 이미 저장된 모든 뉴스 기사 레코드의 team 값을 최신 3단계 계층 알고리즘으로 일괄 재분류(Update)합니다."""
    print("[팀 재분류 시작] DB 뉴스 레코드 점검 시작...")
    
    db = SessionLocal()
    try:
        archives = db.query(NewsArchive).all()
        updated_count = 0
        print(f"[정보] 총 {len(archives)}건의 저장된 뉴스 아카이브 레코드를 점검합니다...")
        
        for item in archives:
            old_team = item.team
            new_team = classify_article_team(item.title)
            
            if old_team != new_team:
                item.team = new_team
                updated_count += 1
                print(f"  └ [팀 변경 성공!] ID {item.id}: '{item.title[:35]}...' ({old_team} -> {new_team})")
                
        if updated_count > 0:
            db.commit()
            print(f"[재분류 완료] 총 {updated_count}건의 뉴스 기사 팀 카테고리가 최신화되었습니다.")
            log_event("TEAM_RECLASSIFY", "SUCCESS", f"DB 아카이브 {updated_count}건 기사 소속 팀 일괄 재분류 완료")
        else:
            print("[완료] 모든 기사의 팀 분류가 이미 최신 정규 상태입니다.")
            
    except Exception as e:
        db.rollback()
        print(f"[오류 발생] 재분류 실패: {str(e)}")
        log_event("TEAM_RECLASSIFY", "FAILED", f"팀 일괄 재분류 처리 중 에러: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    reclassify_all_news_teams()
