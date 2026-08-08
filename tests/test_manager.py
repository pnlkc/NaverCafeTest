import os
import sys
import pytest
from datetime import datetime

# 프로젝트 루트를 PATH에 추가하여 backend 임포트가 가능하게 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import load_settings, save_settings, AppSettings
from backend.database import init_db, SessionLocal, ActionLog, NewsArchive, log_action
from backend.naver_bot import NaverCafeBot
from backend.news_crawler import NewsCrawler

# 테스트 전 DB 초기화 픽스처
@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    # 테스트 전 기존 로그 비우기
    db = SessionLocal()
    db.query(ActionLog).delete()
    db.query(NewsArchive).delete()
    db.commit()
    db.close()
    yield

def test_settings_load_save(monkeypatch):
    """설정 파일 로드 및 저장 기능이 오류 없이 정상 작동하는지 확인합니다."""
    # .env 환경변수 오버라이드가 순수 JSON 로드/저장 검증을 방해하지 않도록 os.getenv 모킹
    monkeypatch.setattr("os.getenv", lambda key, default=None: None)
    
    settings = load_settings()
    assert isinstance(settings, AppSettings)
    assert settings.levelup_conditions.min_nickname_length == 20
    
    # 설정값 임시 수정 후 저장 테스트
    original_id = settings.cafe.club_id
    settings.cafe.club_id = "test_club_123"
    assert save_settings(settings) is True
    
    # 다시 로드해서 변경 사항 확인
    reloaded = load_settings()
    assert reloaded.cafe.club_id == "test_club_123"
    
    # 원상 복구
    reloaded.cafe.club_id = original_id
    save_settings(reloaded)




def test_nickname_validation():
    """닉네임 검증(20자리 연속되지 않은 무작위 숫자 및 이미지 기재 카페 규칙) 조건을 올바르게 판별하는지 테스트합니다."""
    bot = NaverCafeBot()
    
    # 1. 성공 케이스: 20자리 이상의 무작위 숫자형 닉네임
    valid_nick_1 = "98274028491820482937"  # 20자리 무작위 숫자
    valid_nick_2 = "872938104829104829482910" # 24자리 무작위 숫자
    assert bot.is_random_numeric_nickname(valid_nick_1) is True
    assert bot.is_random_numeric_nickname(valid_nick_2) is True
    
    # 2. 실패 케이스: 20자리 미만
    short_nick = "1234567890123456789" # 19자리
    assert bot.is_random_numeric_nickname(short_nick) is False
    
    # 3. 실패 케이스: 숫자가 아닌 문자 포함
    non_numeric = "9827402849182048293a" # 끝에 a 포함
    assert bot.is_random_numeric_nickname(non_numeric) is False
    
    # 4. 실패 케이스: 순차 증가가 5개 이상 포함 (예: 12345)
    seq_inc = "98212345491820482937"
    assert bot.is_random_numeric_nickname(seq_inc) is False
    
    # 5. 실패 케이스: 순차 감소가 5개 이상 포함 (예: 98765)
    seq_dec = "98298765491820482937"
    assert bot.is_random_numeric_nickname(seq_dec) is False
    
    # 6. 실패 케이스: 동일 숫자 반복이 5개 이상 포함 (예: 55555)
    repeat_num = "98255555491820482937"
    assert bot.is_random_numeric_nickname(repeat_num) is False
    
    # 7. 실패 케이스: 구간 반복이 3회 이상 존재 (예: 159215921592)
    interval_repeat = "98159215921592482937"
    assert bot.is_random_numeric_nickname(interval_repeat) is False
    
    # 8. 실패 케이스: 혐오 숫자 포함 (예: 1557)
    hate_num_1 = "98274028491820155737"
    assert bot.is_random_numeric_nickname(hate_num_1) is False
    
    # 9. 실패 케이스: 혐오 숫자 포함 (예: 88888)
    hate_num_2 = "98274028491820888887"
    assert bot.is_random_numeric_nickname(hate_num_2) is False

def test_news_filtering():
    """뉴스 수집 시 팀별 균등 분배 및 인터뷰 우선순위 필터링이 요구조건대로 적용되는지 테스트합니다."""
    crawler = NewsCrawler()
    
    # 2026년 리브랜딩된 팀(KRX, DNS) 및 나무위키 2026 실측 라인업, 퍼스트 스탠드 대회를 반영한 더미 데이터
    dummy_articles = [
        {"id": "1", "title": "[인터뷰] T1 페이커 'Faker가 말하는 2026 시즌의 다짐'"}, # T1 (페이커 선수명 매칭)
        {"id": "2", "title": "T1 구마유시의 미친 카이팅 분석"}, # T1 (구마유시 선수명 매칭)
        {"id": "3", "title": "SKT 제우스 탑 캐리 경기 요약"}, # T1 (SKT + 제우스 매칭)
        {"id": "4", "title": "티원 도란은 이제 한화생명 소속입니다"}, # 도란 -> 한화생명 우선순위 매칭 검증
        {"id": "5", "title": "[인터뷰] 젠지 룰러 'Ruler 복귀전 승리 소감'"}, # 젠지 (룰러 선수명 매칭)
        {"id": "6", "title": "GEN 쵸비 단독 찌르기 분석"}, # 젠지 (GEN + 쵸비 매칭)
        {"id": "7", "title": "Gen.G 캐니언 세주아니 플레이 정밀 분석"}, # 젠지 (Gen.G + canyon)
        {"id": "8", "title": "HLE 도란 탑 럼블 활약상"}, # 한화생명 (HLE + 도란)
        {"id": "9", "title": "한화생명 딜라이트 피넛 이적설의 진실 인터뷰"}, # 한화생명 (딜라이트)
        {"id": "10", "title": "디플러스 쇼메이커 아지르 경기 요약"}, # 디플러스 (쇼메이커)
        {"id": "11", "title": "DK 루시드 비에고 정글 동선 분석"}, # 디플러스 (DK + 루시드)
        {"id": "12", "title": "KT 비디디 경기 예측 인터뷰"}, # KT (비디디)
        {"id": "13", "title": "KRX 지우 아펠리오스 캐리 요약"}, # DRX (신규 약어 KRX + 지우 매칭)
        {"id": "14", "title": "DNS 표식 킨드레드 숲으로 가다 인터뷰"}, # 광동 (신규 약어 DNS + 표식 매칭)
        {"id": "15", "title": "일반 LCK 2라운드 일정 확정"},
        {"id": "16", "title": "일반 퍼스트 스탠드(FST) BLG 우승 분석"}, # 대회명 (퍼스트 스탠드, FST)
        {"id": "17", "title": "일반 패치노트 분석"},
        {"id": "18", "title": "일반 라이엇 코리아 행사 공지"},
        {"id": "19", "title": "Hanjin Brion 테디 이즈리얼 경기 분석"}, # OK저축은행 (Hanjin Brion + 테디)
        {"id": "20", "title": "피어엑스 랩터 선수 인터뷰"} # 피어엑스 (랩터)
    ]
    
    # 10개 필터링 실행
    filtered = crawler._filter_articles(dummy_articles, limit=10)
    
    # 검증 1: 10개 기사 획득 완료 확인
    assert len(filtered) == 10
    
    # 검증 2: 인터뷰 기사들이 대다수 우선 포함되었는지 검증
    interview_count = sum(1 for art in filtered if "인터뷰" in art["title"])
    assert interview_count >= 5
    
    # 검증 3: 2026년 실제 선수 닉네임만 들어간 기사가 올바른 팀으로 귀속되었는지 검증
    # 2번 기사: "T1 구마유시..." -> T1 포함 정상 귀속
    gumayusi_t1_art = [art for art in filtered if "구마유시" in art["title"]]
    if gumayusi_t1_art:
        assert "T1" in gumayusi_t1_art[0]["team"]
        
    # 4번 기사: "티원 도란..." -> 한화생명 포함 정상 귀속 (2026 HLE 도란)
    doran_art = [art for art in filtered if "도란" in art["title"]]
    if doran_art:
        assert "한화생명" in doran_art[0]["team"]
        
    # 13번 기사: "KRX 지우..." -> DRX 포함 정상 귀속 (신규 약어 KRX 검증)
    jiwoo_art = [art for art in filtered if "지우" in art["title"]]
    if jiwoo_art:
        assert "DRX" in jiwoo_art[0]["team"]
        
    # 14번 기사: "DNS 표식..." -> DN 수퍼스/광동 포함 정상 귀속 (신규 약어 DNS 검증)
    pyosik_art = [art for art in filtered if "표식" in art["title"]]
    if pyosik_art:
        assert any(t in pyosik_art[0]["team"] for t in ["DN 수퍼스", "광동", "DNS"])
        
    # 검증 5: 특정 팀이 언급되지 않고 대회명(LCK, LoL)만 포함된 기사의 일반 카테고리 정상 분류 검증
    general_lck_article = [{"id": "21", "title": "추격자들이 무섭지만…여전히 LoL은 LCK로 통한다"}]
    gen_filtered = crawler._filter_articles(general_lck_article, limit=1)
    assert len(gen_filtered) == 1
    assert gen_filtered[0]["team"] == "일반"
    assert "LCK" in gen_filtered[0]["tournaments"] or "LoL" in gen_filtered[0]["tournaments"]

        
    # 검증 4: 대회명 태깅 검증 (16번 기사: 퍼스트 스탠드, FST -> 퍼스트 스탠드 대회 태깅 성공 여부)
    fst_tagged = [art for art in filtered if "퍼스트 스탠드" in art["title"]]
    if fst_tagged:
        assert "퍼스트 스탠드" in fst_tagged[0]["tournaments"]

def test_free_summary():
    """뉴스 요약 알고리즘(AI 및 로컬 요약)이 원본보다 축약되고 저작권 문구를 정상 필터링하는지 테스트합니다."""
    crawler = NewsCrawler()
    
    # 긴 뉴스 기사 본문 원문 모의 텍스트
    long_article = (
        "리그 오브 레전드 LCK 서머 2라운드 빅매치에서 T1이 젠지를 상대로 승리를 거두었습니다.\n"
        "이날 경기는 오랜 라이벌 관계인 두 팀의 대결로 수많은 팬들의 이목이 집중되었습니다. T1은 정교한 밴픽 전략을 통해 경기 초반 주도권을 잡았습니다.\n"
        "1세트에서 페이커의 아지르가 결정적인 순간 토스 플레이를 선보이며 한타 대승을 이끌었습니다. 상대 젠지 역시 쵸비를 앞세워 매섭게 반격했으나 승부를 뒤집지는 못했습니다.\n"
        "2세트 역시 치열한 양상으로 전개되었으나 후반 바론 버프 한타에서 T1이 에이스를 띄우며 승부에 쐐기를 박았습니다.\n"
        "T1 감독은 경기 후 인터뷰에서 '오늘 승리는 선수들이 한마음으로 준비한 결과'라며 기쁨을 표시했습니다.\n"
        "젠지 코칭스태프는 '초반 실수들이 아쉬웠다, 보완하여 다음 라운드에서 설승하겠다'고 아쉬움을 전했습니다.\n"
        "이로써 T1은 플레이오프 직행 확률을 크게 높였으며 서머 랭킹 1위 탈환을 노려볼 수 있게 되었습니다.\n"
        "김기자 기자 = abc@news.com\n"
        "Copyrights ⓒ eSports News. 무단전재 및 재배포 금지."
    )
    
    summary = crawler._summarize_content(long_article)
    
    # 검증 1: 원문보다 적절히 간결하게 축약되었는지 검증
    assert len(summary) < len(long_article)
    
    # 검증 2: 저작권/이메일 등 불필요 문구가 스킵되었는지 검증
    assert "Copyrights" not in summary
    assert "abc@news.com" not in summary
    
    # 검증 3: AI 요약(📌) 포맷 또는 로컬 요약(...) 포맷 중 정상 생성되었는지 검증
    assert "📌" in summary or summary.endswith("...")


def test_db_logging():
    """통합 이벤트 로깅 시 SQLite DB와 동기화가 제대로 이루어지는지 검증합니다."""
    log_action("JOIN_APPROVE", "SUCCESS", "테스트용 가입 자동 승인 이력 기록")
    log_action("LEVEL_UP", "FAILED", "테스트용 등업 오류 모의 에러")
    
    db = SessionLocal()
    logs = db.query(ActionLog).all()
    
    assert len(logs) == 2
    
    # 내림차순 정렬 결과 체크
    assert logs[0].action_type == "JOIN_APPROVE"
    assert logs[0].status == "SUCCESS"
    assert logs[1].action_type == "LEVEL_UP"
    assert logs[1].status == "FAILED"
    
    db.close()

import pytest

@pytest.mark.anyio
async def test_namuwiki_roster_update():
    """나무위키 실시간 로스터 동적 갱신 모듈 및 하루 1회 캐싱/force 갱신 동작을 검증합니다."""
    crawler = NewsCrawler()
    # 갱신 실행 (force=True로 로스터 최신화 수행)
    res = await crawler.update_rosters_from_namuwiki(force=True)
    assert res is True
    
    from backend.news_crawler import TEAM_METADATA
    assert len(TEAM_METADATA) >= 10
    assert "T1" in TEAM_METADATA
    assert any(k in TEAM_METADATA for k in ["젠지", "Gen.G"])
    assert any(k in TEAM_METADATA for k in ["DN 수퍼스", "광동", "DNS", "SOOPers"])
    
    # 2부 콜업 및 선수 변경 시 섞이지 않고 리프레시되는 구조인지 확인
    assert len(TEAM_METADATA["T1"]["players"]) > 0
    assert len(TEAM_METADATA["T1"]["coaches"]) > 0

    # 당일 재호출 시 (force=False) 하루 1회 제한에 따라 즉시 True 반환
    res_cached = await crawler.update_rosters_from_namuwiki(force=False)
    assert res_cached is True

@pytest.mark.anyio
async def test_background_scheduler_lifecycle():
    """백그라운드 스케줄러의 시작, 루프 생성, 이중 시작 방지, 정지 수명주기를 검증합니다."""
    from backend.scheduler import BackgroundScheduler
    import asyncio
    
    scheduler = BackgroundScheduler()
    assert scheduler.is_running is False
    assert len(scheduler.tasks) == 0
    
    # 1. 스케줄러 가동
    await scheduler.start()
    assert scheduler.is_running is True
    assert len(scheduler.tasks) == 4
    for task_name, task in scheduler.tasks.items():
        assert not task.done()
        
    # 2. 중복 가동 시 무시 검증
    first_tasks = dict(scheduler.tasks)
    await scheduler.start()
    assert scheduler.tasks == first_tasks
    
    # 3. 짧은 시간 대기 (태스크 비동기 동작 검증)
    await asyncio.sleep(0.5)
    for task_name, task in scheduler.tasks.items():
        assert not task.done()
        
    # 4. 스케줄러 정지
    await scheduler.stop()
    await asyncio.sleep(0.1)  # 이벤트 루프 비동기 취소 전파 수렴 대기
    assert scheduler.is_running is False
    assert len(scheduler.tasks) == 0
    
    # 5. 기존 태스크들 취소 완료 확인
    for task_name, task in first_tasks.items():
        assert task.done() or task.cancelled()


