import asyncio
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from backend.config import load_settings
from backend.logger import log_event
from backend.config import get_member_network_view_url, get_mobile_board_url, get_pc_article_url
from backend.naver_bot import NaverCafeBot, SESSION_PATH
from backend.news_crawler import NewsCrawler
from backend.discord_notifier import notify_report, notify_suggestion

# 백그라운드 태스크 관리 객체
class BackgroundScheduler:
    def __init__(self):
        self.bot = NaverCafeBot()
        self.crawler = NewsCrawler()
        self.stealth = Stealth()
        self.tasks = {}
        self.is_running = False
        
        # 중복 알림 방지용 캐시 (게시글 ID 보관)
        self.seen_articles = set()
        
    async def start(self):
        """스케줄러의 모든 주기 태스크를 백그라운드에서 실행합니다."""
        if self.is_running:
            return
        
        self.is_running = True
        log_event("SCHEDULER", "INFO", "백그라운드 스케줄러 엔진을 가동합니다.")
        
        # 각 태스크 비동기 기동
        self.tasks["join_approve"] = asyncio.create_task(self._loop_join_approve())
        self.tasks["level_up"] = asyncio.create_task(self._loop_level_up())
        self.tasks["news_publish"] = asyncio.create_task(self._loop_news_publish())
        self.tasks["board_monitor"] = asyncio.create_task(self._loop_board_monitor())

    async def stop(self):
        """실행 중인 모든 백그라운드 태스크를 취소하고 정지합니다."""
        self.is_running = False
        for name, task in self.tasks.items():
            if not task.done():
                task.cancel()
        self.tasks.clear()
        log_event("SCHEDULER", "INFO", "백그라운드 스케줄러 엔진을 정지했습니다.")

    async def _loop_join_approve(self):
        """카페 가입 자동 승인 루프"""
        from backend.discord_notifier import notify_action_log
        while self.is_running:
            settings = load_settings()
            interval = settings.intervals.join_approve
            
            try:
                status = await self.bot.get_session_status()
                if status["logged_in"]:
                    res = await self.bot.approve_join_requests()
                    # 실제로 승인 완료된 인원이 있는 경우에만 성공 알림 1회 발송
                    if res.get("status") == "SUCCESS" and "완료" in res.get("message", ""):
                        notify_action_log("JOIN_APPROVE", "SUCCESS", res.get("message"))
                else:
                    log_event("JOIN_APPROVE", "WARNING", "로그인 세션이 비활성화 상태여서 승인 검사를 건너뜁니다.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                err_msg = f"가입 승인 루프 내 에러 발생: {str(e)}"
                log_event("JOIN_APPROVE", "ERROR", err_msg)
                notify_action_log("JOIN_APPROVE", "FAILED", err_msg)
                
            await asyncio.sleep(max(10, interval))

    async def _loop_level_up(self):
        """회원 등업 조건 자동 검증 루프"""
        from backend.discord_notifier import notify_action_log
        while self.is_running:
            settings = load_settings()
            interval = settings.intervals.level_up
            
            try:
                status = await self.bot.get_session_status()
                if status["logged_in"]:
                    res = await self.bot.check_and_levelup()
                    # 실제로 등업 처리 완료된 인원이 있는 경우에만 성공 알림 1회 발송
                    if res.get("status") == "SUCCESS" and "완료" in res.get("message", ""):
                        notify_action_log("LEVEL_UP", "SUCCESS", res.get("message"))
                else:
                    log_event("LEVEL_UP", "WARNING", "로그인 세션이 비활성화 상태여서 등업 검사를 건너뜁니다.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                err_msg = f"등업 루프 내 에러 발생: {str(e)}"
                log_event("LEVEL_UP", "ERROR", err_msg)
                notify_action_log("LEVEL_UP", "FAILED", err_msg)
                
            await asyncio.sleep(max(30, interval))

    async def _loop_news_publish(self):
        """뉴스 자동 기사 수집 및 자동 등록 루프 (하루 1회 기본값)"""
        from backend.discord_notifier import notify_action_log
        last_publish_day = None
        
        while self.is_running:
            settings = load_settings()
            interval = settings.intervals.news_publish
            
            try:
                status = await self.bot.get_session_status()
                current_day = datetime.now().date()
                
                if status["logged_in"] and (last_publish_day != current_day):
                    res = await self.crawler.collect_and_process_news()
                    if res > 0:
                        last_publish_day = current_day
                        msg = f"오늘의 뉴스 {res}개 배포 처리를 마쳤습니다."
                        log_event("NEWS_PUBLISH", "SUCCESS", msg)
                        notify_action_log("NEWS_PUBLISH", "SUCCESS", msg)
                elif not status["logged_in"]:
                    log_event("NEWS_PUBLISH", "WARNING", "로그인 세션이 없어 뉴스 게시를 건너뜁니다.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                err_msg = f"뉴스 게시 루프 내 에러 발생: {str(e)}"
                log_event("NEWS_PUBLISH", "ERROR", err_msg)
                notify_action_log("NEWS_PUBLISH", "FAILED", err_msg)
                
            await asyncio.sleep(max(60, interval))

    async def _loop_board_monitor(self):
        """
        신고 게시판 & 건의 사항 게시판 실시간 모니터링 및 디스코드 알림 발송 루프
        """
        # 첫 실행인지를 기록하여 첫 탐색 기사들은 알림 없이 캐싱만 수행
        is_first_run = True
        
        while self.is_running:
            settings = load_settings()
            club_id = settings.cafe.club_id
            
            # 신고/건의 주기 중 더 짧은 쪽을 루프 주기로 잡고 내부에서 게시판마다 시간 비교
            interval = min(settings.intervals.report_alert, settings.intervals.suggestion_alert)
            
            if not club_id:
                await asyncio.sleep(10)
                continue
                
            status = await self.bot.get_session_status()
            if not status["logged_in"]:
                log_event("BOARD_MONITOR", "WARNING", "로그인 세션이 비활성화 상태여서 게시판 모니터링을 건너뜁니다.")
                await asyncio.sleep(max(30, interval))
                continue
                
            try:
                # Playwright를 이용해 모바일 게시판 조회
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=["--disable-blink-features=AutomationControlled"]
                    )
                    try:
                        context = await browser.new_context(
                            storage_state=SESSION_PATH,
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        )
                        await self.stealth.apply_stealth_async(context)
                        page = await context.new_page()
                        
                        # 1. 카페 메인 접속을 통한 메뉴 ID 자동 탐색
                        report_menu_id = settings.discord.report_board_id or None
                        suggest_menu_id = settings.discord.suggestion_board_id or None
                        
                        # 메뉴 ID 미지정 시 자동 파싱 시도 (모바일/PC 카페 메인 다단 시도)
                        if not report_menu_id or not suggest_menu_id:
                            menu_urls = [
                                f"https://cafe.naver.com/ca-fe/web/cafes/{club_id}/menus",
                                f"https://m.cafe.naver.com/ca-fe/web/cafes/{club_id}/menus",
                                f"https://m.cafe.naver.com/ca-fe/web/cafes/{club_id}",
                                f"https://cafe.naver.com/MyCafeIntro.nhn?clubid={club_id}"
                            ]
                            for m_url in menu_urls:
                                try:
                                    await page.goto(m_url)
                                    await page.wait_for_timeout(2000)
                                    content = await page.content()
                                    soup = BeautifulSoup(content, "lxml")
                                    
                                    for a in soup.find_all("a"):
                                        text = a.get_text(strip=True)
                                        href = a.get("href", "")
                                        if not href:
                                            continue
                                            
                                        match = re.search(r"(?:menuid|search\.menuid|menus|menuId)[\=/](\d+)", href, re.I)
                                        if match:
                                            m_id = match.group(1)
                                            if not report_menu_id and ("신고" in text or "신고게시판" in text):
                                                report_menu_id = m_id
                                                log_event("BOARD_MONITOR", "INFO", f"신고 게시판 메뉴 ID 탐색 성공: {m_id}")
                                            if not suggest_menu_id and ("건의" in text or "건의게시판" in text):
                                                suggest_menu_id = m_id
                                                log_event("BOARD_MONITOR", "INFO", f"건의 게시판 메뉴 ID 탐색 성공: {m_id}")
                                    if report_menu_id and suggest_menu_id:
                                        break
                                except Exception:
                                    pass

                        # 2. 각 게시판 글 목록 수집 및 알림 발송
                        if report_menu_id:
                            await self._check_board_and_notify(
                                page, club_id, report_menu_id, "REPORT", is_first_run
                            )
                        else:
                            log_event("BOARD_MONITOR", "WARNING", f"'{settings.discord.report_board_name}' 메뉴 ID를 찾지 못해 신고 게시판 감시를 스킵했습니다. (설정에서 report_board_id 지정 가능)")
                            
                        if suggest_menu_id:
                            await self._check_board_and_notify(
                                page, club_id, suggest_menu_id, "SUGGESTION", is_first_run
                            )
                        else:
                            log_event("BOARD_MONITOR", "WARNING", f"'{settings.discord.suggestion_board_name}' 메뉴 ID를 찾지 못해 건의 게시판 감시를 스킵했습니다.")
                    finally:
                        try:
                            await browser.close()
                        except Exception:
                            pass
                    
                # 첫 루프 종료 후 플래그 변경
                is_first_run = False
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_event("BOARD_MONITOR", "ERROR", f"게시판 모니터링 루프 중 에러 발생: {str(e)}")
                
            await asyncio.sleep(max(30, interval))

    async def _check_board_and_notify(self, page, club_id: str, menu_id: str, board_type: str, is_first_run: bool):
        """게시판 페이지를 긁어 새 글을 파악하고 디스코드로 보냅니다.
        
        모바일 카페 SPA (m.cafe.naver.com/ca-fe/web/cafes/...) 기반 DOM 추출.
        li.ListItem 내 a.mainLink의 innerText 구조:
          '{제목}\\n{작성자닉네임}\\n{날짜}\\n조회 {N}'
        """
        # 모바일 URL 사용 (li.ListItem 렌더링 보장, PC f-e URL은 미렌더링)
        url = f"https://m.cafe.naver.com/ca-fe/web/cafes/{club_id}/menus/{menu_id}"
        try:
            await page.goto(url)
            await page.wait_for_timeout(4000)
            
            # SPA 렌더링 대기 (a.mainLink가 게시글 링크)
            try:
                await page.wait_for_selector("a.mainLink", timeout=6000)
            except Exception:
                pass
            
            # 동적 무한 스크롤 스캐닝 루프 (최대 4회 스크롤 다운 수행)
            articles_data = []
            max_scrolls = 4
            
            for scroll_idx in range(max_scrolls + 1):
                # Playwright JS 실행으로 렌더링된 Vue.js SPA DOM에서 게시글 목록 직접 추출
                current_articles = await page.evaluate("""() => {
                    const results = [];
                    const items = document.querySelectorAll('li.ListItem');
                    items.forEach(item => {
                        const linkEl = item.querySelector('a.mainLink');
                        if (!linkEl) return;
                        
                        const href = linkEl.getAttribute('href') || '';
                        const idMatch = href.match(/(?:articleid|articles)[=\\/](\\d+)/i);
                        if (!idMatch) return;
                        
                        const lines = linkEl.innerText.trim().split('\\n').map(l => l.trim()).filter(Boolean);
                        const title = lines[0] || '';
                        const author = lines[1] || '';
                        const postedAt = lines[2] || '';
                        
                        results.push({
                            articleId: idMatch[1],
                            title: title,
                            author: author,
                            postedAt: postedAt
                        });
                    });
                    return results;
                }""")
                
                articles_data = current_articles
                
                # 수집된 글이 없으면 더 이상 스크롤할 필요 없음
                if not articles_data:
                    break
                    
                # 최하단 글이 이미 본 글인지 검사
                last_art = articles_data[-1]
                last_key = f"{board_type}_{last_art['articleId']}"
                
                # 만약 최하단 글이 이미 본 글이라면, 더 예전 글들을 추가로 불러올 필요가 없으므로 루프 즉시 중단
                if last_key in self.seen_articles:
                    break
                    
                # 최하단 글마저 새 글이고, 아직 최대 스크롤 횟수에 도달하지 않았다면 스크롤 다운 수행
                if scroll_idx < max_scrolls:
                    log_event("BOARD_MONITOR", "INFO", f"[{board_type}] 목록 하단 유실 방지를 위해 추가 스크롤 다운을 수행합니다. (현재 {len(articles_data)}개 스캔)")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)
            
            found_count = len(articles_data)
            new_articles_to_notify = []
            
            for art in articles_data:
                article_id = art["articleId"]
                article_key = f"{board_type}_{article_id}"
                
                title = art["title"]
                title = re.sub(r"^\s*(?:NEW|\[공지\]|\[안내\])\s*", "", title)
                title = re.sub(r"NEW\s*$", "", title).strip()
                if not title:
                    continue
                
                author = art["author"] if art["author"] else "카페 회원"
                # 날짜/조회수 등이 닉네임으로 잘못 잡히는 경우 필터링
                if re.match(r"^\d{2}\.\d{2}\.\d{2}", author) or author.startswith("조회"):
                    author = "카페 회원"
                
                # 작성 시간 파싱 (당일: "10:48" → "2026.07.20 10:48", 이전: "26.07.19." → "2026.07.19")
                raw_time = art.get("postedAt", "")
                if re.match(r"^\d{1,2}:\d{2}$", raw_time):
                    from datetime import datetime, timezone, timedelta
                    kst = timezone(timedelta(hours=9))
                    today_str = datetime.now(kst).strftime("%Y.%m.%d")
                    posted_at = f"{today_str} {raw_time}"
                elif re.match(r"^\d{2}\.\d{2}\.\d{2}\.$", raw_time):
                    parts = raw_time.rstrip(".").split(".")
                    posted_at = f"20{parts[0]}.{parts[1]}.{parts[2]}"
                else:
                    posted_at = raw_time or "알 수 없음"
                
                pc_article_link = get_pc_article_url(club_id, article_id)
                
                if article_key not in self.seen_articles:
                    self.seen_articles.add(article_key)
                    new_articles_to_notify.append({
                        "title": title,
                        "author": author,
                        "link": pc_article_link,
                        "posted_at": posted_at
                    })
            
            # 새로 발견된 미발송 게시물 전체에 대해 디스코드 알림 발송
            for art in new_articles_to_notify:
                if board_type == "REPORT":
                    res = notify_report(art["title"], art["author"], art["link"], art["posted_at"])
                    log_event("REPORT_ALERT", "SUCCESS" if res else "FAILED", f"신고글 탐지 디스코드 발송 ({res}): {art['title']} [작성자: {art['author']}] [작성시간: {art['posted_at']}]")
                elif board_type == "SUGGESTION":
                    res = notify_suggestion(art["title"], art["author"], art["link"], art["posted_at"])
                    log_event("SUGGESTION_ALERT", "SUCCESS" if res else "FAILED", f"건의글 탐지 디스코드 발송 ({res}): {art['title']} [작성자: {art['author']}] [작성시간: {art['posted_at']}]")

            log_event("BOARD_MONITOR", "INFO", f"[{board_type}] 게시판 글 {found_count}개 감지 및 디스코드 모니터링 완료.")
        except Exception as e:
            log_event("BOARD_MONITOR", "ERROR", f"[{board_type}] 게시판 감시 중 예외 발생: {str(e)}")

# 전역 스케줄러 인스턴스
global_scheduler = BackgroundScheduler()
