import os
import json
from pydantic import BaseModel, Field
from typing import List, Optional

# 설정 파일 저장 경로
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

class MonitorIntervals(BaseModel):
    join_approve: int = Field(default=60, description="가입 승인 확인 주기 (초)")
    level_up: int = Field(default=300, description="자동 등업 확인 주기 (초)")
    report_alert: int = Field(default=60, description="신고 게시판 모니터링 주기 (초)")
    suggestion_alert: int = Field(default=300, description="건의 사항 모니터링 주기 (초)")
    news_publish: int = Field(default=86400, description="뉴스 기사 수집 및 게시 주기 (초, 하루 1회)")

class LevelUpConditions(BaseModel):
    min_nickname_length: int = Field(default=20, description="닉네임 최소 길이")
    min_comment_count: int = Field(default=5, description="최소 댓글 작성 횟수")
    min_visit_count: int = Field(default=3, description="최소 방문 횟수")
    check_welcome_post: bool = Field(default=True, description="가입인사 글 작성 여부 체크")
    welcome_board_name: str = Field(default="등업 게시판", description="가입인사 게시판 이름") # 실측 기본값 반영

class NewsScrapingConfig(BaseModel):
    target_url: str = Field(
        default="https://game.naver.com/esports/League_of_Legends/news/lol",
        description="뉴스 수집 대상 URL"
    )
    teams: List[str] = Field(
        default=["T1", "젠지", "한화생명", "디플러스", "KT", "피어엑스", "광동", "DRX", "OK저축은행", "농심"],
        description="팀별 균등 분배용 LCK 팀 키워드 목록"
    )
    interview_keywords: List[str] = Field(
        default=["인터뷰", "감독", "코치", "선수", "소감", "다짐", "포부"],
        description="인터뷰 우선순위 판정 키워드 목록"
    )
    use_llm_summary: bool = Field(default=False, description="OpenAI API 요약 사용 여부")
    openai_api_key: str = Field(default="", description="OpenAI API 키")
    publish_board_id: str = Field(default="4", description="카페 뉴스 게시판 ID (글 작성 위치)") # 실측 기본값 반영

class DiscordConfig(BaseModel):
    webhook_url: str = Field(default="", description="디스코드 Webhook URL (기본값)")
    report_webhook_url: str = Field(default="", description="신고 알림 전용 디스코드 Webhook URL")
    suggestion_webhook_url: str = Field(default="", description="건의 알림 전용 디스코드 Webhook URL")
    log_webhook_url: str = Field(default="", description="작업 로그 전용 디스코드 Webhook URL")
    report_board_name: str = Field(default="신고 게시판", description="모니터링할 신고 게시판 이름") # 실측 기본값 일치
    suggestion_board_name: str = Field(default="자유 게시판", description="모니터링할 건의 사항 게시판 이름") # 실측 기본값 반영
    report_board_id: str = Field(default="", description="신고 게시판 수동 메뉴 ID (자동 탐색 실패 시 사용)")
    suggestion_board_id: str = Field(default="", description="건의 사항 게시판 수동 메뉴 ID (자동 탐색 실패 시 사용)")

class CafeConfig(BaseModel):
    club_id: str = Field(default="31759124", description="네이버 카페 Club ID") # 실측 기본값 반영
    naver_id: str = Field(default="", description="관리자 네이버 ID")

    @property
    def naver_cafe_numeric_id(self) -> str:
        return self.club_id

class AppSettings(BaseModel):
    cafe: CafeConfig = Field(default_factory=CafeConfig)
    intervals: MonitorIntervals = Field(default_factory=MonitorIntervals)
    levelup_conditions: LevelUpConditions = Field(default_factory=LevelUpConditions)
    news: NewsScrapingConfig = Field(default_factory=NewsScrapingConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)

    @property
    def naver_cafe_numeric_id(self) -> str:
        return self.cafe.club_id

# 호환성을 위한 EnvSettings 클래스 별칭
EnvSettings = AppSettings

def load_settings() -> AppSettings:
    """JSON 파일로부터 설정을 로드합니다. 파일이 없으면 기본 설정을 생성하여 저장 후 리턴합니다."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
    if not os.path.exists(CONFIG_PATH):
        default_settings = AppSettings()
        save_settings(default_settings)
        return default_settings

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return AppSettings.model_validate(data)
    except Exception as e:
        print(f"[Config] 설정 로드 오류 (기본값 사용): {e}")
        return AppSettings()

def save_settings(settings: AppSettings) -> bool:
    """설정을 JSON 파일에 저장합니다."""
    try:
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, exist_ok=True)
            
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            # Pydantic v2 모델의 딕셔너리 변환 및 JSON 저장
            json.dump(settings.model_dump(), f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"[Config] 설정 저장 오류: {e}")
        return False

# ==========================================
# 네이버 카페 전역 URL 중앙 관리 빌더 (신형 FE 규격 반영)
# ==========================================
def get_pc_article_url(club_id: str, article_id: str, menu_id: str = "") -> str:
    """신형 FE 규격 카페 게시글 상세 페이지 URL을 생성합니다."""
    if menu_id:
        return f"https://cafe.naver.com/f-e/cafes/{club_id}/articles/{article_id}?menuid={menu_id}&referrerAllArticles=false"
    return f"https://cafe.naver.com/f-e/cafes/{club_id}/articles/{article_id}"

def get_mobile_article_url(club_id: str, article_id: str) -> str:
    """카페 게시글 모바일/FE 상세 페이지 URL을 생성합니다."""
    return f"https://cafe.naver.com/f-e/cafes/{club_id}/articles/{article_id}"

def get_join_approve_url(club_id: str) -> str:
    """가입 승인 관리 페이지 URL을 생성합니다."""
    return f"https://cafe.naver.com/ManageMemberJoinApproveList.nhn?clubid={club_id}"

def get_member_manage_url(club_id: str) -> str:
    """전체 회원 관리 페이지 URL을 생성합니다."""
    return f"https://cafe.naver.com/ManageMemberRowList.nhn?clubid={club_id}"

def get_mobile_board_url(club_id: str, menu_id: str, page: int = 1) -> str:
    """PC 정식 카페 게시판 글 목록 URL을 생성합니다."""
    return f"https://cafe.naver.com/ArticleList.nhn?search.clubid={club_id}&search.menuid={menu_id}"

def get_mobile_write_url(club_id: str, menu_id: str) -> str:
    """신형 FE 규격 카페 글쓰기 페이지 URL을 생성합니다."""
    return f"https://cafe.naver.com/ca-fe/cafes/{club_id}/menus/{menu_id}/articles/write?boardType=L"

def get_member_network_view_url(club_id: str) -> str:
    """카페 멤버 네트워크 메뉴 목록 URL을 생성합니다."""
    return f"https://cafe.naver.com/CafeMemberNetworkView.nhn?m=view&clubid={club_id}"
