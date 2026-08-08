import os
import re
import time
import httpx
import shutil
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from typing import List, Dict, Any, Optional
from backend.config import load_settings, AppSettings
from backend.logger import log_event
from backend.database import NewsArchive, SessionLocal

import json

# 아카이브 저장 폴더 및 팀 데이터 JSON 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE_DIR = os.path.join(BASE_DIR, "data", "archive")
TEAMS_JSON_PATH = os.path.join(BASE_DIR, "data", "teams.json")

def _read_json_file(path: str, default: Any = None) -> Any:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_event("CONFIG", "WARNING", f"JSON 파일({os.path.basename(path)}) 판독 실패: {str(e)}")
    return default

def _write_json_file(path: str, data: Any) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        log_event("CONFIG", "WARNING", f"JSON 파일({os.path.basename(path)}) 저장 실패: {str(e)}")
        return False

def load_team_metadata_file() -> dict:
    data = _read_json_file(TEAMS_JSON_PATH, default={})
    return data if isinstance(data, dict) else {}

def save_team_metadata_file(data: dict) -> bool:
    return _write_json_file(TEAMS_JSON_PATH, data)

# 글로벌 LoL e스포츠 팀 메타데이터 사전 (동적 수집용 메모리 보관소)
TEAM_METADATA = {}

TOURNAMENT_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tournaments.json")

def load_tournament_synonyms() -> dict:
    data = _read_json_file(TOURNAMENT_FILE_PATH, default={})
    return data if isinstance(data, dict) else {}

def save_tournament_synonyms(data: dict) -> bool:
    return _write_json_file(TOURNAMENT_FILE_PATH, data)

# 대회 및 리그 동의어 사전 (data/tournaments.json에서 동적 로드)
TOURNAMENT_SYNONYMS = load_tournament_synonyms()

UNCLASSIFIED_JSON_PATH = os.path.join(BASE_DIR, "data", "unclassified_notified.json")

def load_unclassified_notified() -> set:
    data = _read_json_file(UNCLASSIFIED_JSON_PATH, default=[])
    return set(data) if isinstance(data, list) else set()

def save_unclassified_notified(data: set) -> bool:
    return _write_json_file(UNCLASSIFIED_JSON_PATH, list(data))




# 로스터 실시간 갱신 중복 실행 방지 글로벌 락 플래그
_is_updating_roster = False
_last_roster_log_date = None

def classify_article_team(title: str) -> str:
    """
    기사 제목을 기반으로 언급된 모든 팀을 찾아 다중 티커 태깅(쉼표 구분 문자열, 예: 'DK, T1')으로 리턴합니다.
    제목에서 먼저 등장한 순서대로 정렬하여 리턴하며, 매칭되는 팀이 없으면 '일반'을 리턴합니다.
    """
    if not title:
        return "일반"
    title_lower = title.lower()

    global TEAM_METADATA
    if not TEAM_METADATA:
        loaded_data = load_team_metadata_file()
        if loaded_data:
            TEAM_METADATA.update(loaded_data)

    matched_teams_with_idx = []  # (first_match_index, team_key)

    for team_key, meta in TEAM_METADATA.items():
        team_first_idx = float('inf')

        # 1. 팀명(team_names) 매칭 체크
        for syn in meta.get("team_names", []):
            syn_lower = syn.lower()
            idx = title_lower.find(syn_lower)
            if idx != -1 and idx < team_first_idx:
                team_first_idx = idx

        # 2. 선수 닉네임 / 본명 매칭 체크
        if team_first_idx == float('inf'):
            for p in meta.get("players", []):
                nick = p.get("nickname", "").lower()
                real = p.get("real_name", "").lower()
                idx_n = title_lower.find(nick) if len(nick) >= 2 else -1
                idx_r = title_lower.find(real) if len(real) >= 2 else -1
                indices = [i for i in (idx_n, idx_r) if i != -1]
                if indices:
                    m_idx = min(indices)
                    if m_idx < team_first_idx:
                        team_first_idx = m_idx

        # 3. 코칭스태프 닉네임 / 본명 매칭 체크
        if team_first_idx == float('inf'):
            for c in meta.get("coaches", []):
                nick = c.get("nickname", "").lower()
                real = c.get("real_name", "").lower()
                idx_n = title_lower.find(nick) if len(nick) >= 2 else -1
                idx_r = title_lower.find(real) if len(real) >= 2 else -1
                indices = [i for i in (idx_n, idx_r) if i != -1]
                if indices:
                    m_idx = min(indices)
                    if m_idx < team_first_idx:
                        team_first_idx = m_idx

        if team_first_idx != float('inf'):
            matched_teams_with_idx.append((team_first_idx, team_key))

    if not matched_teams_with_idx:
        return "일반"

    # 등장 인덱스 기준 오름차순 정렬
    matched_teams_with_idx.sort(key=lambda x: x[0])
    
    # 중복 제거 (티커 기준)
    seen = set()
    result_teams = []
    for idx, team_key in matched_teams_with_idx:
        if team_key not in seen:
            seen.add(team_key)
            result_teams.append(team_key)

    return ", ".join(result_teams)

class NewsCrawler:
    def __init__(self):
        self.settings = load_settings()
        self.stealth = Stealth()
        # 분류 실패 알림 중복 전송 방지용 캐시 (영구 파일 연동)
        self.notified_unclassified_articles = load_unclassified_notified()
        self.last_summary_method = ""
        
        # 대회명 동의어 사전 동적 로드
        global TOURNAMENT_SYNONYMS, TEAM_METADATA
        TOURNAMENT_SYNONYMS.clear()
        TOURNAMENT_SYNONYMS.update(load_tournament_synonyms())

        # 시작 시 로스터 메모리가 비어있으면 teams.json 에서 안전 충전
        if not TEAM_METADATA:
            loaded_data = load_team_metadata_file()
            if loaded_data:
                TEAM_METADATA.update(loaded_data)


    async def update_rosters_from_namuwiki(self, force: bool = False) -> bool:
        """
        나무위키 LCK, LPL, LEC 참가팀 로스터 문서를 실시간 크롤링하여 TEAM_METADATA를 최신화합니다.
        오늘 이미 파싱이 성공하여 teams.json이 최신화되었고 force=False인 경우 하루 1회 제한 정책에 따라 중복 파싱을 스킵합니다.
        성공 시 기존 데이터를 지우고 덮어쓰며, 실패 시 Fallback 데이터를 로드합니다.
        """
        global TEAM_METADATA, _is_updating_roster, _last_roster_log_date
        if _is_updating_roster:
            log_event("ROSTER_UPDATE", "INFO", "이미 실시간 로스터 업데이트 작업이 진행 중입니다. 중복 트리거를 회피합니다.")
            return False
            
        # 하루 1회 제한 검사 (force=False인 경우 오늘 갱신 완료 여부 확인)
        if not force and os.path.exists(TEAMS_JSON_PATH):
            try:
                mtime = os.path.getmtime(TEAMS_JSON_PATH)
                last_updated_date = datetime.fromtimestamp(mtime).date()
                if last_updated_date == datetime.now().date():
                    loaded_data = load_team_metadata_file()
                    if loaded_data:
                        TEAM_METADATA.clear()
                        TEAM_METADATA.update(loaded_data)
                        if _last_roster_log_date != datetime.now().date():
                            log_event("ROSTER_UPDATE", "INFO", "오늘 이미 나무위키 로스터 파싱이 완료되었습니다. (하루 1회 제한 적용 중)")
                            _last_roster_log_date = datetime.now().date()
                        return True
            except Exception as check_err:
                log_event("ROSTER_UPDATE", "WARNING", f"로스터 파싱 날짜 체크 중 경고: {str(check_err)}")

        _is_updating_roster = True
        log_event("ROSTER_UPDATE", "INFO", "나무위키 실시간 e스포츠 로스터 파싱을 개시합니다.")
        
        urls = {
            "LCK": "https://namu.wiki/w/League%20of%20Legends%20Champions%20Korea/%EC%B0%B8%EA%B0%80%ED%8C%80%20%EB%A1%9C%EC%8A%A4%ED%84%B0",
            "LPL": "https://namu.wiki/w/League%20of%20Legends%20Pro%20League/%EC%B0%B8%EA%B0%80%ED%8C%80%20%EB%A1%9C%EC%8A%A4%ED%84%B0",
            "LEC": "https://namu.wiki/w/League%20of%20Legends%20EMEA%20Championship/%EC%B0%B8%EA%B0%80%ED%8C%80%20%EB%A1%9C%EC%8A%A4%ED%84%B0"
        }
        new_metadata = {}
        success_league_count = 0
        
        try:
            async with async_playwright() as p:
                try:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=["--disable-blink-features=AutomationControlled"]
                    )
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                    await self.stealth.apply_stealth_async(context)
                    page = await context.new_page()
                    page.set_default_timeout(15000)
                    
                    for league, url in urls.items():
                        try:
                            log_event("ROSTER_UPDATE", "INFO", f"{league} 로스터 수집 중...")
                            await page.goto(url)
                            await page.wait_for_timeout(2000)
                            
                            html = await page.content()
                            soup = BeautifulSoup(html, "lxml")
                            tables = soup.find_all("table")
                            
                            for table in tables:
                                table_text = table.text.lower()
                                base_teams = load_team_metadata_file() or TEAM_METADATA
                                for key, meta in base_teams.items():
                                    if any(name.lower() in table_text for name in meta.get("team_names", [])):
                                        team_found_key = key
                                        break
                                        
                                if not team_found_key:
                                    continue
                                    
                                if team_found_key not in new_metadata:
                                    new_metadata[team_found_key] = {
                                        "team_names": base_teams[team_found_key].get("team_names", [team_found_key]),
                                        "players": [],
                                        "coaches": []
                                    }
                                    
                                for row in table.find_all("tr"):
                                    cells = row.find_all(["td", "th"])
                                    if len(cells) < 2:
                                        continue
                                        
                                    pos_text = cells[0].text.strip()
                                    cont_text = cells[1].text.strip()
                                    
                                    is_coach = any(kw in pos_text for kw in ["감독", "코치", "Coach", "Head Coach", "코칭스태프"])
                                    is_player = any(kw in pos_text for kw in ["Top", "Jungle", "Mid", "Bot", "Support", "ADC", "탑", "정글", "미드", "바텀", "서포터"])
                                    
                                    if not (is_coach or is_player):
                                        continue
                                        
                                    matches = re.findall(r"([a-zA-Z0-9_-]{2,15})\s*\(([^)]+)\)", cont_text)
                                    if not matches:
                                        parts = re.split(r"[\n/]", cont_text)
                                        if len(parts) >= 2:
                                            p_nick = re.sub(r"[^a-zA-Z0-9_-]", "", parts[0]).strip()
                                            p_real = re.sub(r"[^가-힣a-zA-Z]", "", parts[1]).strip()
                                            if len(p_nick) >= 2 and len(p_real) >= 2:
                                                matches = [(p_nick, p_real)]
                                                
                                    for nick, real in matches:
                                        item_data = {"id": nick, "nickname": nick, "real_name": real}
                                        if is_player and item_data not in new_metadata[team_found_key]["players"]:
                                            new_metadata[team_found_key]["players"].append(item_data)
                                        elif is_coach and item_data not in new_metadata[team_found_key]["coaches"]:
                                            new_metadata[team_found_key]["coaches"].append(item_data)
                             
                            success_league_count += 1
                            
                        except Exception as le:
                            log_event("ROSTER_UPDATE", "WARNING", f"{league} 리그 수집 예외 (스킵): {str(le)}")
                            
                    await browser.close()
                    
                except Exception as e:
                    log_event("ROSTER_UPDATE", "WARNING", f"나무위키 브라우저 기동 실패: {str(e)}")
        finally:
            _is_updating_roster = False
            
        # 신규 수집 데이터와 기존 2026 로스터 안전 병합
        if len(new_metadata) > 0:
            # 기존 teams.json 데이터에 새로 수집한 정보를 병합
            merged_metadata = dict(load_team_metadata_file() or TEAM_METADATA)
            for k, v in new_metadata.items():
                if v["players"] or v["coaches"]:
                    merged_metadata[k] = v
                    
            TEAM_METADATA.clear()
            TEAM_METADATA.update(merged_metadata)
            save_team_metadata_file(TEAM_METADATA)
            log_event("ROSTER_UPDATE", "SUCCESS", f"나무위키 로스터 파싱 성공! 총 {len(TEAM_METADATA)}개 팀 갱신 및 teams.json 동기화 완료.")
            return True
        else:
            TEAM_METADATA.clear()
            loaded_data = load_team_metadata_file()
            if loaded_data:
                TEAM_METADATA.update(loaded_data)
            log_event("ROSTER_UPDATE", "SUCCESS", f"로컬 2026 팀 메타데이터 사전({len(TEAM_METADATA)}개 팀)이 정상적으로 활성화되었습니다.")
            return True

    async def collect_and_process_news(self) -> int:
        """
        네이버 e스포츠 뉴스를 수집하고 필터링한 뒤, 요약 및 원문 아카이빙을 수행하여 카페에 자동 게시합니다.
        """
        self.settings = load_settings()
        target_url = self.settings.news.target_url
        
        # 0. 기사 수집 직전에 나무위키 로스터 실시간 동기화 수행 (동적 2부 콜업 및 최신 데이터 반영)
        await self.update_rosters_from_namuwiki()
        
        log_event("NEWS_SCRAPING", "INFO", "e스포츠 뉴스 수집을 시작합니다.")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            await self.stealth.apply_stealth_async(context)
            page = await context.new_page()
            
            try:
                # 1. 기사 목록 수집
                await page.goto(target_url)
                # 기사 로딩을 위해 5초 대기
                await page.wait_for_timeout(5000)
                
                # HTML 파싱
                content = await page.content()
                soup = BeautifulSoup(content, "lxml")
                
                # 뉴스 카드 링크와 제목 수집 (많이 본 뉴스 영역 파악 및 범용 추출)
                articles = []
                card_links = soup.select('a[href*="/article/"]')
                
                # 중복 방지를 위한 set
                seen_urls = set()
                
                for link in card_links:
                    href = link.get("href")
                    if not href:
                        continue
                    
                    # 상대 경로 주소 보완
                    full_url = urljoin("https://game.naver.com", href)
                    
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)
                    
                    # 많이 본 뉴스 판별 (클래스 또는 부모 태그에 mostview / rank 포함 여부)
                    parent_context = (str(link.get("class", "")) + str(link.parent)).lower()
                    is_mostview = any(k in parent_context for k in ["most", "rank", "popular", "top"])
                    
                    # 제목 추출 (카드 내부의 strong 태그 우선, 없으면 전체 텍스트)
                    title_el = link.select_one('strong')
                    title = title_el.text.strip() if title_el else link.text.strip()
                    if not title or len(title) < 5:
                        continue
                        
                    # 기사 ID 추출 (URL에서 숫자 ID 파싱)
                    article_id = "unknown"
                    id_match = re.search(r"article/(\d+/\d+|\d+)", full_url)
                    if id_match:
                        article_id = id_match.group(1).replace("/", "_")
                    else:
                        id_match_alt = re.search(r"article[?/]id=(\d+)", full_url)
                        if id_match_alt:
                            article_id = id_match_alt.group(1)
                            
                    articles.append({
                        "id": article_id,
                        "title": title,
                        "url": full_url,
                        "is_mostview": is_mostview
                    })
                    
                log_event("NEWS_SCRAPING", "INFO", f"총 {len(articles)}개의 기사 후보를 수집했습니다.")
                
                if not articles:
                    log_event("NEWS_SCRAPING", "WARNING", "수집된 기사 목록이 비어 있습니다.")
                    await browser.close()
                    return 0

                # 1-1. 이미 DB에 아카이빙 되었거나 처리/미분류 알림 전송된 기사 사전 필터링 (중복 처리 방지)
                db_pre = SessionLocal()
                new_candidate_articles = []
                try:
                    for art in articles:
                        art_identifier = art.get("url") or art.get("id") or art["title"]
                        archive_folder = os.path.join(ARCHIVE_DIR, art["id"])
                        existing_db = db_pre.query(NewsArchive).filter(
                            (NewsArchive.article_id == art["id"]) | (NewsArchive.title == art["title"])
                        ).first()
                        
                        if existing_db or os.path.exists(archive_folder):
                            log_event("NEWS_SCRAPING", "INFO", f"이미 DB/아카이브 처리 완료된 기사 사전 스킵: {art['title']}")
                            continue
                        
                        if art_identifier in self.notified_unclassified_articles:
                            log_event("NEWS_SCRAPING", "INFO", f"이미 미분류 알림 처리된 기사 사전 스킵: {art['title']}")
                            continue

                        new_candidate_articles.append(art)
                finally:
                    db_pre.close()

                log_event("NEWS_SCRAPING", "INFO", f"중복 기사를 제외한 {len(new_candidate_articles)}개의 신규 기사 후보를 검토합니다.")
                
                # 2. 필터링 로직 적용 (팀별 균등 분배 + 인터뷰 우선순위)
                filtered_articles = self._filter_articles(new_candidate_articles)
                log_event("NEWS_SCRAPING", "INFO", f"필터링을 거쳐 최종 {len(filtered_articles)}개의 기사를 선정했습니다.")
                
                # 3. 각 기사별 상세 수집, 아카이빙 및 게시
                from backend.naver_bot import NaverCafeBot
                bot = NaverCafeBot()
                
                success_count = 0
                fail_count = 0
                total_to_process = 0
                details = []
                db = SessionLocal()
                
                # 중복되지 않는 실제 처리 대상 기사 추출
                articles_to_post = []
                for art in filtered_articles:
                    # 네이버 카페 제목 80자 제한 방어 및 특수문자 공통 정제
                    cleaned_title = bot.clean_title_for_naver(art["title"])
                    if len(cleaned_title) > 78:
                        cleaned_title = cleaned_title[:75] + "..."
                    art["title"] = cleaned_title
                        
                    archive_folder = os.path.join(ARCHIVE_DIR, art["id"])
                    existing_db = db.query(NewsArchive).filter(
                        (NewsArchive.article_id == art["id"]) | (NewsArchive.title == art["title"])
                    ).first()
                    
                    if existing_db or os.path.exists(archive_folder):
                        log_event("NEWS_SCRAPING", "INFO", f"이미 처리 완료된 기사입니다. 중복 포스팅 스킵: {art['title']}")
                        continue
                    articles_to_post.append(art)
                
                total_to_process = len(articles_to_post)
                
                for art in articles_to_post:
                    # 상세 페이지 접속하여 본문 및 이미지 수집
                    detail_data = await self._scrape_article_detail(page, art["url"], art["id"])
                    if not detail_data:
                        fail_count += 1
                        details.append(f"❌ {art['title']} (상세 수집 실패)")
                        continue
                        
                    # 본문 요약 적용
                    summary = self._summarize_content(detail_data["raw_text"])
                    
                    # 네이버 카페에 기사 등록 (최대 3회 재시도 적용)
                    post_res = None
                    for post_attempt in range(1, 4):
                        post_res = await bot.write_news_article(art["title"], summary, art["url"], notify_discord=False)
                        if post_res.get("status") == "SUCCESS":
                            break
                        log_event("NEWS_SCRAPING", "WARNING", f"기사 발행 시도 실패 ({post_attempt}/3) - 사유: {post_res.get('message')}. 3초 후 재시도합니다.")
                        await page.wait_for_timeout(3000)
                    
                    # DB 아카이브 등록 (실제 카페 게시 결과에 따라 published_at 분기)
                    if post_res.get("status") == "SUCCESS":
                        archive = NewsArchive(
                            article_id=art["id"],
                            title=art["title"],
                            summary=summary,
                            source_url=art["url"],
                            local_path=detail_data["archive_path"],
                            cafe_article_url=post_res.get("cafe_article_url"),
                            team=art.get("team", "일반"),
                            published_at=datetime.now()
                        )
                        db.add(archive)
                        db.commit()
                        success_count += 1
                        log_event("NEWS_SCRAPING", "SUCCESS", f"기사 발행 완료: {art['title']}")
                        details.append(f"✅ {art['title']} [{self.last_summary_method}]")
                    else:
                        # 게시 실패 시에도 수집 기록은 남기되 published_at=None으로 발행 미완료 표시
                        archive = NewsArchive(
                            article_id=art["id"],
                            title=art["title"],
                            summary=summary,
                            source_url=art["url"],
                            local_path=detail_data["archive_path"],
                            cafe_article_url=None,
                            team=art.get("team", "일반"),
                            published_at=None
                        )
                        db.add(archive)
                        db.commit()
                        fail_count += 1
                        log_event("NEWS_SCRAPING", "FAILED", f"기사 발행 실패: {art['title']}, 사유: {post_res.get('message')}")
                        details.append(f"❌ {art['title']} (사유: {post_res.get('message')}) [{self.last_summary_method}]")
                        
                    # 카페 연속 글쓰기 사이의 미세 딜레이 및 봇 방지 (6초 대기)
                    await page.wait_for_timeout(6000)
                    
                db.close()
                await browser.close()
                return {
                    "total": total_to_process,
                    "success": success_count,
                    "failed": fail_count,
                    "details": details
                }
                
            except Exception as e:
                log_event("NEWS_SCRAPING", "FAILED", f"뉴스 수집/처리 과정 중 심각한 에러 발생: {str(e)}")
                await browser.close()
                return {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "error": str(e),
                    "details": []
                }

    def _filter_articles(self, articles: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        """
        팀별 동의어 및 대회 키워드를 정밀 판정하고, 균등 분배 및 인터뷰 우선순위를 고려하여 기사를 최종 필터링합니다.
        """
        teams = self.settings.news.teams
        interview_kws = self.settings.news.interview_keywords
        
        # 1. 각 기사에 대해 팀 소속, 대회 태그 및 인터뷰 여부 판정
        classified = []
        for art in articles:
            title = art["title"]
            title_lower = title.lower()

            # 타 종목(야구, 축구, 타 e스포츠-영문약자 및 영문명 종합 정밀 제외) 노이즈 기사 전격 제외
            other_sports = [
                # 일반 스포츠
                "야구", "프로야구", "축구", "k리그", "농구", "골프", "배구", "메이저리그", "mlb", "kbo", "손흥민", "류현진",
                # FPS / 슈팅 / 배틀로얄 (영문/약자 포함)
                "vct", "발로란트", "valorant", "배틀그라운드", "배그", "pubg", "pubgm", "pubg mobile", "pubg 모바일", "모바일 배그", "모바일배그",
                "오버워치", "owcs", "overwatch", "ow2", "에이펙스", "apex legends", "apex", "cs:go", "csgo", "cs2", "counter-strike",
                "레인보우식스", "r6s", "r6", "서든어택", "스페셜포스", "콜오브듀티", "cod", "codl", "포트나이트", "fortnite", "크로스파이어", "crossfire",
                # 격투 / RTS / 기타 (영문/약자 포함)
                "스트리트파이터", "스파5", "스파6", "sf5", "sf6", "street fighter", "sfv", "sfvi",
                "철권", "tekken", "tekken 7", "tekken 8", "tekken7", "tekken8", "길티기어", "ggst",
                "스타크래프트", "starcraft", "sc2", "스타2", "워크래프트", "warcraft", "war3", "wc3",
                # MOBA / 모바일 / 스포츠게임 / 카드 (영문/약자 포함)
                "도타", "dota", "dota 2", "dota2", "왕자영요", "honor of kings", "hok", "펜타스톰", "aov", "arena of valor",
                "모바일 레전드", "모바일레전드", "mlbb", "fc 온라인", "fc온라인", "피파온라인", "fifa online", "fo4", "eacc", "ea fc",
                "하스스톤", "hearthstone", "tft", "teamfight tactics", "전략적팀전투", "전략적 팀 전투", "룬테라", "lor", "legends of runeterra",
                "카트라이더", "kartrider", "섀도우버스", "shadowverse", "로켓리그", "rocket league"
            ]
            if any(skw in title_lower for skw in other_sports):
                log_event("NEWS_SCRAPING", "INFO", f"LoL 외 타 종목/대회 기사 스킵: {title}")
                continue
            
            # 인터뷰 여부 판별 (선수/감독명 등 정밀화)
            is_interview = any(kw in title for kw in interview_kws)
            if "[인터뷰]" in title or "인터뷰" in title or "대담" in title:
                is_interview = True
                
            # 대회 매칭 태깅 (부가 정보용)
            matched_tournaments = []
            for tour_key, tour_syns in TOURNAMENT_SYNONYMS.items():
                if any(syn.lower() in title_lower for syn in tour_syns):
                    matched_tournaments.append(tour_key)
            
            # 소속 팀 판별 (글로벌 3단계 우선순위 탐색)
            assigned_team = classify_article_team(title)
                    
            # 팀은 특정되지 않았지만 대회명(LCK/롤드컵/MSI/LoL 등)이 매칭된 경우에만 '일반' e스포츠 기사로 분류하고,
            # 팀명과 대회명 모두 매칭되지 않는 순수 미분류 기사는 게시 대상에서 제외(continue)
            if assigned_team == "일반" and not matched_tournaments:
                art_identifier = art.get("url") or art.get("id") or title
                if art_identifier not in self.notified_unclassified_articles:
                    self.notified_unclassified_articles.add(art_identifier)
                    save_unclassified_notified(self.notified_unclassified_articles)
                    try:
                        from backend.discord_notifier import notify_team_classification_failure
                        notify_team_classification_failure(
                            article_title=title,
                            article_link=art["url"],
                            error_msg="기사 제목에 매칭되는 2026시즌 e스포츠 팀명, 선수/코치 닉네임 또는 대회명(LCK/롤드컵/MSI 등)이 로스터 메타데이터 사전에 등록되어 있지 않아 게시를 스킵합니다."
                        )
                    except Exception as de:
                        log_event("NEWS_SCRAPING", "WARNING", f"디스코드 분류 실패 알림 전송 실패: {str(de)}")
                continue


            classified.append({
                **art,
                "team": assigned_team,
                "tournaments": matched_tournaments,
                "is_interview": is_interview
            })
            
        # 2. 정렬 순서: 1순위 인터뷰 기사 -> 2순위 많이 본 뉴스 -> 3순위 팀 지정 기사 최우선 배치
        classified.sort(key=lambda x: (x["is_interview"], x.get("is_mostview", False), x["team"] != "일반"), reverse=True)
        
        # 3. 팀별 균등 분배 수집 알고리즘
        # 특정 인기 팀이 도배되는 것을 방지하기 위해, 동일 팀 기사는 최대 2개로 제한
        team_counts = {}
        for team_key in TEAM_METADATA.keys():
            team_counts[team_key] = 0
        team_counts["일반"] = 0
        
        final_list = []
        for art in classified:
            team = art["team"]
            
            # 사전에 없는 기타 팀명 처리용 초기화
            if team not in team_counts:
                team_counts[team] = 0
                
            # 이미 동일 팀 기사가 2개 이상 선택되었다면 스킵 (균등 배분)
            if team != "일반" and team_counts[team] >= 2:
                continue
            # 일반 기사도 3개 이상 선택 시 스킵
            if team == "일반" and team_counts["일반"] >= 3:
                continue
                
            final_list.append(art)
            team_counts[team] += 1
            
            if len(final_list) >= limit:
                break
                
        return final_list

    async def _scrape_article_detail(self, page, url: str, article_id: str) -> Optional[Dict[str, Any]]:
        """기사 상세 페이지를 로드하여 본문 텍스트를 파싱하고 본문 내 이미지를 로컬에 저장합니다."""
        try:
            await page.goto(url)
            await page.wait_for_timeout(3000)
            
            # 본문 영역 파싱 (네이버 스포츠 PC/모바일 및 React 개편 랩퍼 전수 탐색)
            body_selector = "#newsct_article, #articeBody, .news_end, div[class*='NewsEnd_article_body'], div[class*='article_body'], #news_body_area, #newsct, div._article_body, article, section"
            body_el = await page.query_selector(body_selector)
            
            raw_text = ""
            raw_html = ""
            
            if body_el:
                raw_text = await body_el.inner_text()
                raw_html = await body_el.inner_html()
            else:
                # BeautifulSoup Fallback (DOM 전체 파싱)
                content = await page.content()
                soup = BeautifulSoup(content, "lxml")
                target_container = soup.find(id=re.compile(r"(newsct|article|news)", re.I)) or soup.find(class_=re.compile(r"(NewsEnd|article_body|news_end|newsct)", re.I)) or soup.find("article")
                if target_container:
                    raw_text = target_container.text.strip()
                    raw_html = str(target_container)
                else:
                    log_event("NEWS_SCRAPING", "WARNING", f"기사 본문 요소를 찾지 못했습니다: {url}")
                    return None
                    
            if not raw_text.strip():
                log_event("NEWS_SCRAPING", "WARNING", f"기사 본문 텍스트가 비어 있습니다: {url}")
                return None
            
            # 아카이빙 디렉터리 생성: data/archive/{article_id}/
            art_dir = os.path.join(ARCHIVE_DIR, article_id)
            img_dir = os.path.join(art_dir, "images")
            os.makedirs(img_dir, exist_ok=True)
            
            # BeautifulSoup을 통해 HTML 내부 이미지 추출, 저장 및 원문 위치 치환
            soup = BeautifulSoup(raw_html, "lxml")
            imgs = soup.find_all("img")
            
            # 이미지 다운로드 및 로컬 주소 치환
            img_counter = 1
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            # 비동기 HTTP 클라이언트 가동
            async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
                for img in imgs:
                    src = img.get("src") or img.get("data-src")
                    if not src or not src.startswith("http"):
                        continue
                        
                    try:
                        # 이미지 다운로드
                        response = await client.get(src)
                        if response.status_code == 200:
                            # 확장자 판별
                            ext = "jpg"
                            if ".png" in src.lower():
                                ext = "png"
                            elif ".gif" in src.lower():
                                ext = "gif"
                                
                            img_filename = f"img_{img_counter}.{ext}"
                            img_path = os.path.join(img_dir, img_filename)
                            
                            with open(img_path, "wb") as f:
                                f.write(response.content)
                                
                            # HTML 상의 src 주소를 로컬 경로로 변경
                            img["src"] = f"./images/{img_filename}"
                            img_counter += 1
                    except Exception as e:
                        # 이미지 개별 다운로드 실패는 전체 본문 수집 실패로 잡지 않고 무시
                        pass
            
            # 로컬 경로로 치환된 깨끗한 HTML을 article.html로 단일 저장
            modified_html = str(soup)
            html_path = os.path.join(art_dir, "article.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(f"<html><head><meta charset='UTF-8'></head><body>{modified_html}</body></html>")
                
            relative_archive_path = f"data/archive/{article_id}/article.html"
            
            return {
                "raw_text": raw_text,
                "archive_path": relative_archive_path
            }
            
        except Exception as e:
            log_event("NEWS_SCRAPING", "WARNING", f"기사 본문 상세 수집 오류 ({url}): {str(e)}")
            return None

    def _summarize_content(self, text: str) -> str:
        """기사 본문을 원본의 50% 미만으로 요약합니다. LLM 또는 무료 알고리즘 적용."""
        # 실시간 최신 설정 반영
        current_settings = load_settings()
        use_llm = current_settings.news.use_llm_summary
        llm_provider = getattr(current_settings.news, "llm_provider", "openai").lower()
        
        api_key = ""
        endpoint = ""
        headers = {}
        model = getattr(current_settings.news, "llm_model", "openrouter/free")
        
        if llm_provider == "openrouter":
            api_key = (current_settings.news.openrouter_api_key or os.getenv("OPENROUTER_API_KEY") or "").strip()
            endpoint = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "HTTP-Referer": "https://github.com/naver-cafe-auto-manager",
                "X-Title": "Naver Cafe Auto Manager"
            }
            if model == "gpt-4o-mini":
                model = "openrouter/free"
        else:
            api_key = (current_settings.news.openai_api_key or os.getenv("OPENAI_API_KEY") or "").strip()
            endpoint = "https://api.openai.com/v1/chat/completions"
            
        if use_llm and api_key:
            # 시도할 모델 체인 구성 (고성능 무료 모델 다중 배치)
            models_to_try = []
            if llm_provider == "openrouter":
                fallback_models = [
                    "openrouter/free",
                    "meta-llama/llama-3.3-70b-instruct:free",
                    "google/gemma-2-9b-it:free",
                    "mistralai/mistral-7b-instruct:free",
                    "qwen/qwen-2.5-72b-instruct:free"
                ]
                if model and model != "gpt-4o-mini" and model not in fallback_models:
                    models_to_try.append(model)
                models_to_try.extend(fallback_models)
            else:
                models_to_try = [model]

            for current_model in models_to_try:
                # 모델별 최대 3회 재시도 (Safety text 및 429 오류 대응)
                for attempt in range(1, 4):
                    try:
                        # LLM API 동기 호출 (httpx로 요청)
                        headers.update({
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        })
                        payload = {
                            "model": current_model,
                            "messages": [
                                {
                                    "role": "system", 
                                    "content": "너는 e스포츠 전문 뉴스 요약봇이야. 제시된 뉴스 기사 본문을 읽고, 첫 줄에는 반드시 '📌 기사 요약' 헤더를 붙이고 아래 예시와 동일한 불릿 포인트(-) 양식으로 3~4줄로 간결하게 핵심만 요약해줘.\n[엄격 수칙]\n1. 기사 본문이 영문(외국어)이더라도 반드시 매끄럽고 자연스러운 한국어(한글)로 번역하여 요약해.\n2. 선수, 코치, 감독의 닉네임/본명 및 대회명(EWC, LCK, MSI 등), 약어, 팀명은 문법이나 맞춤법에 맞지 않는 독특한 단어이더라도 원문 기사에 작성된 표기 철자 그대로 100% 동일하게 유지해야 해. 절대로 교정하거나 변형하지 마.\n3. 원문 기사에 없는 내용은 절대로 상상, 추측, 각색(Hallucination)하지 말고 오직 사실에만 기반하여 정확하게 작성해.\n4. 'User Safety:', 'Response Safety:' 같은 가드레일 메타 텍스트나 '**' 마크다운 문법 기호를 절대로 출력하지 마."
                                },
                                {
                                    "role": "user", 
                                    "content": "요약할 뉴스 기사 본문:\n[LCK] T1이 2024 LCK 서머 플레이오프 1라운드 경기에서 풀세트 접전 끝에 KT 롤스터를 3-2로 제압했습니다. 5세트 30분경 '페이커' 이상혁의 아지르가 결정적인 궁극기로 상대 딜러진을 배달하며 승기를 잡았습니다. 경기 후 김정균 감독은 \"선수들이 끝까지 집중력을 잃지 않고 최선을 다해줘서 고맙다\"며 2라운드 승리를 다짐했습니다."
                                },
                                {
                                    "role": "assistant", 
                                    "content": "📌 기사 요약\n- T1이 KT 롤스터와의 풀세트 접전 끝에 3대 2 승리를 거두며 플레이오프 2라운드 진출을 확정지었습니다.\n- 5세트 승부처에서 '페이커' 이상혁 선수의 아지르가 결정적인 한타 활약을 선보였습니다.\n- 김정균 감독은 경기 후 인터뷰에서 선수들의 끝까지 포기하지 않는 집중력을 칭찬하며 다음 경기 승리를 다짐했습니다."
                                },
                                {
                                    "role": "user", 
                                    "content": f"요약할 뉴스 기사 본문:\n{text}"
                                }
                            ],
                            "temperature": 0.3
                        }
                        
                        with httpx.Client(timeout=30.0) as client:
                            response = client.post(endpoint, json=payload, headers=headers)
                            if response.status_code == 200:
                                res_data = response.json()
                                summary_text = res_data["choices"][0]["message"]["content"].strip()
                                
                                # ** 마크다운 볼드 기호 전격 제거 정제
                                summary_text = summary_text.replace("**", "").replace("*", "")
                                
                                # Safety 가드레일 메타데이터 문구만 포함된 엉터리 응답 검출 시 동일 모델 0.5초 대기 후 재시도
                                if "user safety:" in summary_text.lower() or "response safety:" in summary_text.lower() or len(summary_text.strip()) < 30:
                                    log_event("NEWS_SCRAPING", "WARNING", f"AI 요약 응답이 Safety 메타데이터에 불과함 (Model: {current_model}, 시도 {attempt}/3)")
                                    time.sleep(0.5)
                                    continue
                                
                                # AI 요약 결과가 비어있지 않고 원문보다 유효할 경우 성공 처리 및 반환
                                if summary_text and len(summary_text) < len(text):
                                    log_event("NEWS_SCRAPING", "INFO", f"AI 뉴스 요약 성공 (Provider: {llm_provider.upper()}, Model: {current_model})")
                                    self.last_summary_method = f"{llm_provider.upper()}({current_model})"
                                    return summary_text
                            else:
                                log_event("NEWS_SCRAPING", "WARNING", f"{llm_provider.upper()} API 요약 호출 실패 (Model: {current_model}, 시도 {attempt}/3, Status {response.status_code}): {response.text}")
                                # 429 Rate Limit(호출 과도) 발생 시 1초 지연 후 동일 모델 재시도
                                if response.status_code == 429:
                                    time.sleep(1.0)
                                    
                    except Exception as e:
                        log_event("NEWS_SCRAPING", "WARNING", f"{llm_provider.upper()} API 요약 실패 (Model: {current_model}, 시도 {attempt}/3): {str(e)}")
                        time.sleep(0.5)
            
            # 루프가 완료되었음에도 요약 리턴이 안 된 경우 (모든 모델 시도 실패)
            if llm_provider == "openrouter":
                log_event("NEWS_SCRAPING", "WARNING", "OpenRouter의 모든 무료 AI 모델 요약에 실패했습니다. Gemini API 우회를 시도합니다.")
            else:
                log_event("NEWS_SCRAPING", "WARNING", "OpenAI API 요약에 실패했습니다. Gemini API 우회를 시도합니다.")
                
        # --- Gemini API Fallback 시도 ---
        gemini_api_key = (current_settings.news.gemini_api_key or os.getenv("GEMINI_API_KEY") or "").strip()
        if use_llm and gemini_api_key:
            log_event("NEWS_SCRAPING", "INFO", "Gemini API를 통한 요약을 시도합니다.")
            gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            # 구글 AI Studio 실측 검증 완료 3종 경량 Flash/Flash-Lite 폴백 체인 (200 OK 실측 확보)
            # 1순위: gemini-3.5-flash-lite (뉴스 요약 전용 초경량 초고속 모델 ⚡)
            # 2순위: gemini-3.5-flash (3.5세대 고성능 Flash 모델)
            # 3순위: gemini-2.5-flash-lite (2.5세대 백업 Flash-Lite 모델)
            gemini_models = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash-lite"]
            gemini_headers = {
                "Authorization": f"Bearer {gemini_api_key}",
                "Content-Type": "application/json"
            }
            
            for g_model in gemini_models:
                for attempt in range(1, 4):
                    try:
                        payload = {
                            "model": g_model,
                            "messages": [
                                {
                                    "role": "system", 
                                    "content": "너는 e스포츠 전문 뉴스 요약봇이야. 제시된 뉴스 기사 본문을 읽고, 첫 줄에는 반드시 '📌 기사 요약' 헤더를 붙이고 아래 예시와 동일한 불릿 포인트(-) 양식으로 3~4줄로 간결하게 핵심만 요약해줘.\n[엄격 수칙]\n1. 기사 본문이 영문(외국어)이더라도 반드시 매끄럽고 자연스러운 한국어(한글)로 번역하여 요약해.\n2. 선수, 코치, 감독의 닉네임/본명 및 대회명(EWC, LCK, MSI 등), 약어, 팀명은 문법이나 맞춤법에 맞지 않는 독특한 단어이더라도 원문 기사에 작성된 표기 철자 그대로 100% 동일하게 유지해야 해. 절대로 교정하거나 변형하지 마.\n3. 원문 기사에 없는 내용은 절대로 상상, 추측, 각색(Hallucination)하지 말고 오직 사실에만 기반하여 정확하게 작성해.\n4. 'User Safety:', 'Response Safety:' 같은 가드레일 메타 텍스트나 '**' 마크다운 문법 기호를 절대로 출력하지 마."
                                },
                                {
                                    "role": "user", 
                                    "content": "요약할 뉴스 기사 본문:\n[LCK] T1이 2024 LCK 서머 플레이오프 1라운드 경기에서 풀세트 접전 끝에 KT 롤스터를 3-2로 제압했습니다. 5세트 30분경 '페이커' 이상혁의 아지르가 결정적인 궁극기로 상대 딜러진을 배달하며 승기를 잡았습니다. 경기 후 김정균 감독은 \"선수들이 끝까지 집중력을 잃지 않고 최선을 다해줘서 고맙다\"며 2라운드 승리를 다짐했습니다."
                                },
                                {
                                    "role": "assistant", 
                                    "content": "📌 기사 요약\n- T1이 KT 롤스터와의 풀세트 접전 끝에 3대 2 승리를 거두며 플레이오프 2라운드 진출을 확정지었습니다.\n- 5세트 승부처에서 '페이커' 이상혁 선수의 아지르가 결정적인 한타 활약을 선보였습니다.\n- 김정균 감독은 경기 후 인터뷰에서 선수들의 끝까지 포기하지 않는 집중력을 칭찬하며 다음 경기 승리를 다짐했습니다."
                                },
                                {
                                    "role": "user", 
                                    "content": f"요약할 뉴스 기사 본문:\n{text}"
                                }
                            ],
                            "temperature": 0.3
                        }
                        
                        with httpx.Client(timeout=30.0) as client:
                            response = client.post(gemini_endpoint, json=payload, headers=gemini_headers)
                            if response.status_code == 200:
                                res_data = response.json()
                                summary_text = res_data["choices"][0]["message"]["content"].strip()
                                summary_text = summary_text.replace("**", "").replace("*", "")
                                
                                if "user safety:" in summary_text.lower() or "response safety:" in summary_text.lower() or len(summary_text.strip()) < 30:
                                    log_event("NEWS_SCRAPING", "WARNING", f"Gemini 요약 응답이 Safety 메타데이터에 불과함 (Model: {g_model}, 시도 {attempt}/3)")
                                    time.sleep(0.5)
                                    continue
                                    
                                if summary_text and len(summary_text) < len(text):
                                    log_event("NEWS_SCRAPING", "INFO", f"Gemini 뉴스 요약 성공 (Model: {g_model})")
                                    self.last_summary_method = f"Gemini({g_model})"
                                    return summary_text
                            else:
                                log_event("NEWS_SCRAPING", "WARNING", f"Gemini API 요약 호출 실패 (Model: {g_model}, 시도 {attempt}/3, Status {response.status_code}): {response.text}")
                                if response.status_code == 429:
                                    time.sleep(1.0)
                                    
                    except Exception as e:
                        log_event("NEWS_SCRAPING", "WARNING", f"Gemini API 요약 실패 (Model: {g_model}, 시도 {attempt}/3): {str(e)}")
                        time.sleep(0.5)
            
            log_event("NEWS_SCRAPING", "WARNING", "Gemini API의 모든 무료 모델 요약에 실패했습니다. 로컬 요약 알고리즘으로 대체 구동합니다.")
        elif use_llm:
            log_event("NEWS_SCRAPING", "WARNING", "모든 LLM 요약 시도에 실패했습니다. 로컬 요약 알고리즘으로 대체 구동합니다.")

        # --- 무료 알고리즘 방식 ---
        # 1. 줄 바꿈 및 마침표 기준으로 문장 추출
        # 기사의 앞부분 및 핵심 정보가 많은 상위 30% 문장을 추출하여 자연스럽게 조합
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # 기사 작성자 정보, 불필요한 저작권 정보 등 하단 스킵용 필터링
        filtered_lines = []
        for line in lines:
            if "기자 =" in line or "기자=" in line or "무단전재" in line or "배포금지" in line or "Copyrights" in line:
                continue
            filtered_lines.append(line)
            
        # 전체 문단 중 앞의 4~6개 주요 문단만 결합하여 본문 분량의 50% 미만 보장
        summary_lines = []
        current_len = 0
        max_len = len(text) * 0.45 # 최대 45%까지만 허용
        
        for line in filtered_lines:
            if current_len + len(line) < max_len:
                summary_lines.append(line)
                current_len += len(line) + 1
            else:
                break
                
        if not summary_lines:
            # 예외 대비 상위 3문장만 리턴
            summary_lines = filtered_lines[:3]
            
        summary_result = "\n\n".join(summary_lines)
        if len(summary_result) < len(text):
            summary_result += "\n\n..."
            
        self.last_summary_method = "로컬 폴백"
        return summary_result
