import os
import re
import json
import time
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Page, BrowserContext
from playwright_stealth import Stealth

from backend.config import (
    load_settings,
    get_join_approve_url,
    get_member_network_view_url,
    get_mobile_board_url,
    get_member_manage_url,
    get_mobile_write_url
)
from backend.logger import log_event

# 세션 파일 저장 경로
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SESSION_PATH = os.path.join(DATA_DIR, "session.json")

class NaverCafeBot:
    def __init__(self):
        self.settings = load_settings()
        self.stealth = Stealth()

    async def _apply_stealth(self, context: BrowserContext):
        """Playwright 컨텍스트에 Stealth 설정을 적용하여 봇 감지를 우회합니다."""
        # 봇 탐지 우회를 위한 기본 설정 추가
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        await self.stealth.apply_stealth_async(context)

    async def get_session_status(self) -> Dict[str, Any]:
        """현재 로그인 세션 파일의 유효성 여부 및 정보를 반환합니다."""
        if not os.path.exists(SESSION_PATH):
            return {"logged_in": False, "message": "로그인 세션 파일이 존재하지 않습니다."}
        
        try:
            with open(SESSION_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            # 쿠키 중 네이버 로그인 정보(NID_SES, NID_AUT) 존재 여부 확인
            cookies = state.get("cookies", [])
            has_session_cookie = any(c.get("name") in ["NID_SES", "NID_AUT"] for c in cookies)
            
            if has_session_cookie:
                file_time = os.path.getmtime(SESSION_PATH)
                updated_at = datetime.fromtimestamp(file_time).strftime("%Y-%m-%d %H:%M:%S")
                return {
                    "logged_in": True, 
                    "updated_at": updated_at,
                    "message": "로그인 세션이 저장되어 있습니다."
                }
            else:
                return {"logged_in": False, "message": "세션 파일은 있으나 로그인 쿠키가 유효하지 않습니다."}
        except Exception as e:
            return {"logged_in": False, "message": f"세션 파일 판독 실패: {str(e)}"}

    async def run_manual_login(self) -> Dict[str, Any]:
        """
        사용자 수동 로그인을 위한 브라우저 창(헤드풀)을 띄우고,
        로그인이 감지되면 세션 상태를 저장합니다.
        """
        log_event("SYSTEM", "INFO", "사용자 수동 로그인을 위한 브라우저 실행을 시작합니다.")
        
        async with async_playwright() as p:
            # 사용자가 로그인할 수 있도록 헤드풀 모드로 크롬 실행
            browser = await p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            # 컨텍스트 생성 (실제 사용자와 유사한 User-Agent 설정)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            await self._apply_stealth(context)
            page = await context.new_page()
            
            # 네이버 로그인 페이지로 이동
            await page.goto("https://nid.naver.com/nidlogin.login")
            
            # 로그인 성공 여부를 주기적으로 체크 (최대 3분 대기)
            login_success = False
            timeout = 180  # 초
            start_time = time.time()
            
            log_event("SYSTEM", "INFO", "네이버 로그인 대기 중... 브라우저 창에서 로그인을 완료해주세요 (제한시간 3분)")
            
            while time.time() - start_time < timeout:
                try:
                    # 로그인 완료 후 네이버 홈이나 네이버 서비스로 주소가 변경되었고 쿠키가 확보되었는지 확인
                    current_url = page.url
                    cookies = await context.cookies()
                    has_session = any(c.get("name") == "NID_SES" for c in cookies)
                    
                    if has_session and ("nidlogin.login" not in current_url):
                        # 로그인 성공 감지
                        login_success = True
                        # 세션 파일 저장
                        os.makedirs(DATA_DIR, exist_ok=True)
                        await context.storage_state(path=SESSION_PATH)
                        log_event("SYSTEM", "SUCCESS", "네이버 로그인 세션이 성공적으로 저장되었습니다.")
                        break
                except Exception as e:
                    # 브라우저가 수동으로 닫히거나 에러가 난 경우
                    break
                
                await asyncio.sleep(2)
            
            await browser.close()
            
            if login_success:
                return {"status": "SUCCESS", "message": "로그인 세션 저장 완료"}
            else:
                log_event("SYSTEM", "FAILED", "네이버 로그인 세션 획득에 실패하였습니다 (시간 초과 또는 중단)")
                return {"status": "FAILED", "message": "로그인 대기 시간 초과 또는 실패"}

    async def _get_logged_in_context(self, p, headless: bool = True) -> Optional[BrowserContext]:
        """저장된 세션을 사용하여 로그인된 브라우저 컨텍스트를 반환합니다."""
        if not os.path.exists(SESSION_PATH):
            log_event("SYSTEM", "FAILED", "로그인 세션 파일이 없습니다. 수동 로그인을 먼저 완료해야 합니다.")
            return None
            
        # 헤드리스/헤드풀 모드로 크롬 기동
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # 저장된 세션 상태 로드
        context = await browser.new_context(
            storage_state=SESSION_PATH,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        return context

    async def approve_join_requests(self) -> Dict[str, Any]:
        """카페 가입 신청 대기 목록을 조회하고 전체 자동 승인 처리합니다."""
        self.settings = load_settings()
        club_id = self.settings.cafe.club_id
        
        if not club_id:
            log_event("JOIN_APPROVE", "FAILED", "네이버 카페 Club ID가 설정되지 않았습니다.")
            return {"status": "FAILED", "message": "Club ID 미설정"}

        url = get_join_approve_url(club_id)
        
        async with async_playwright() as p:
            context = await self._get_logged_in_context(p)
            if not context:
                return {"status": "FAILED", "message": "로그인 세션 없음"}
                
            browser = context.browser
            await self._apply_stealth(context)
            page = await context.new_page()
            
            try:
                log_event("JOIN_APPROVE", "INFO", "가입 승인 관리자 페이지에 접속합니다.")
                await page.goto(url)
                await page.wait_for_load_state("networkidle")
                
                # "가입을 신청한 멤버가 없습니다" 안내 문구가 있는지 확인
                no_member_indicator = await page.query_selector("td.no_member")
                if no_member_indicator:
                    text_content = await no_member_indicator.inner_text()
                    if "가입을 신청한 멤버가 없습니다" in text_content:
                        log_event("JOIN_APPROVE", "SUCCESS", "대기 중인 가입 신청자가 없습니다.")
                        await browser.close()
                        return {"status": "SUCCESS", "message": "가입 신청 대기자 없음"}
                
                # 가입 대기 회원 체크박스들이 있는지 확인 (input[name="memberId"])
                checkboxes = await page.query_selector_all("input[name='memberId']")
                if not checkboxes:
                    log_event("JOIN_APPROVE", "SUCCESS", "승인할 대기 멤버 체크박스가 발견되지 않았습니다.")
                    await browser.close()
                    return {"status": "SUCCESS", "message": "대기자 없음"}
                
                # 전체 선택 체크박스 클릭
                all_check = await page.query_selector("input#allCheck")
                if all_check:
                    await all_check.click()
                else:
                    # 없을 경우 루프 돌면서 개별 체크박스 모두 클릭
                    for cb in checkboxes:
                        if not await cb.is_checked():
                            await cb.click()
                
                # 승인 버튼 클릭 (a._clickApprove 또는 a:has-text("승인"))
                # 보통 '승인' 버튼은 a.btn_type1, a._clickApprove 등의 클래스를 가짐
                approve_btn = await page.query_selector("a._clickApprove")
                if not approve_btn:
                    approve_btn = page.locator("a:has-text('승인')").first
                    
                if approve_btn:
                    # 클릭 시 경고창(Alert) 발생 대응
                    # "선택한 멤버를 가입 승인하시겠습니까?" 와 같은 Alert 자동 수락 설정
                    page.on("dialog", lambda dialog: dialog.accept())
                    
                    await approve_btn.click()
                    await page.wait_for_timeout(3000)  # 처리 대기
                    
                    count = len(checkboxes)
                    log_event("JOIN_APPROVE", "SUCCESS", f"가입 신청자 {count}명을 전체 자동 승인 처리하였습니다.")
                    await browser.close()
                    return {"status": "SUCCESS", "message": f"{count}명 승인 완료"}
                else:
                    log_event("JOIN_APPROVE", "FAILED", "승인 버튼을 찾지 못했습니다.")
                    await browser.close()
                    return {"status": "FAILED", "message": "승인 버튼 미발견"}
                    
            except Exception as e:
                log_event("JOIN_APPROVE", "FAILED", f"가입 승인 처리 중 에러 발생: {str(e)}")
                await browser.close()
                return {"status": "FAILED", "message": str(e)}

    def is_random_numeric_nickname(self, nickname: str, min_len: int = 20) -> bool:
        """
        20자리 이상의 '연속되지 않은 무작위 숫자'로 구성된 닉네임인지 확인합니다.
        (이미지에 기재된 네이버 카페 공식 가이드라인 5대 규칙 반영)
        
        1. 구간 반복이 없어야 한다. (예: 159215921592... 등 2~10자리 패턴이 3회 이상 연속 반복)
        2. 특정 선수의 생일 등 의미있는 숫자는 가능하나 1번을 위배해서는 안 됨
        3. 혐오 숫자가 들어가서는 안 된다. (예: 1557, 88888 등)
        4. 5자리 이상 이어지는 숫자는 안 된다. (예: 12345 등 오름/내림차순 연속)
        5. 5자리 이상 같은 숫자 역시 안 된다. (예: 55555 등 연속 동일숫자)
        """
        if not nickname.isdigit():
            return False
        if len(nickname) < min_len:
            return False
            
        # 규칙 3. 혐오 숫자 필터링 (1557, 88888)
        hate_numbers = ["1557", "88888"]
        if any(hn in nickname for hn in hate_numbers):
            return False
            
        # 규칙 5. 5자리 이상 같은 숫자 차단
        for i in range(10):
            if str(i) * 5 in nickname:
                return False
                
        # 규칙 1. 구간 반복 차단 (2자리 이상 10자리 이하의 서브패턴이 3회 이상 연속 부착 반복)
        import re
        if re.search(r"(\d{2,10})\1{2,}", nickname):
            return False
            
        # 규칙 4. 5자리 이상 이어지는 숫자(순차 증가/감소) 차단 (예: 12345, 54321)
        for i in range(len(nickname) - 4):
            slice_seq = [int(x) for x in nickname[i:i+5]]
            # 증가 패턴
            is_increasing = all(slice_seq[j] + 1 == slice_seq[j+1] for j in range(4))
            # 감소 패턴
            is_decreasing = all(slice_seq[j] - 1 == slice_seq[j+1] for j in range(4))
            if is_increasing or is_decreasing:
                return False
                
        return True

    async def check_and_levelup(self) -> Dict[str, Any]:
        """
        멤버 관리 페이지를 탐색하여 4가지 조건을 충족한 회원을 자동 등업 처리합니다.
        1) 20자리 이상의 무작위 숫자형 닉네임
        2) 댓글 수 5회 이상
        3) 방문 횟수 3회 이상
        4) 가입인사 게시판에 글을 작성했는지 여부
        """
        self.settings = load_settings()
        club_id = self.settings.cafe.club_id
        cond = self.settings.levelup_conditions
        
        if not club_id:
            log_event("LEVEL_UP", "FAILED", "네이버 카페 Club ID가 설정되지 않았습니다.")
            return {"status": "FAILED", "message": "Club ID 미설정"}
            
        # 1단계: 가입인사 게시판 글 작성자들 수집
        # 가입인사 작성 여부를 빠르게 검사하기 위해 가입인사 게시판의 최근 글 작성자 목록을 추출합니다.
        # 모바일 버전 게시판 주소가 파싱이 쉽고 가볍습니다.
        welcome_board_writers = set()
        
        async with async_playwright() as p:
            context = await self._get_logged_in_context(p)
            if not context:
                return {"status": "FAILED", "message": "로그인 세션 없음"}
                
            browser = context.browser
            await self._apply_stealth(context)
            page = await context.new_page()
            
            try:
                # 1. 가입인사 게시판 조회하여 가입인사 작성자들 리스트 확보
                # 게시판 이름을 바탕으로 메뉴 ID를 찾거나, 대시보드 설정을 기반으로 menu ID가 필요함.
                # 우선 PC 카페 메인에서 메뉴 목록의 '가입인사' 메뉴 링크를 파싱하여 menu ID를 알아냅니다.
                log_event("LEVEL_UP", "INFO", "가입인사 게시판 조회를 위해 카페 메인에 접속합니다.")
                await page.goto(f"https://cafe.naver.com/MyCafeIntro.nhn?clubid={club_id}")
                await page.wait_for_load_state("domcontentloaded")
                
                # 가입인사 게시판 메뉴 ID 파싱
                # a 태그 중 텍스트에 "가입인사"가 들어간 요소 검색
                # 예: <a href="/ArticleList.nhn?search.clubid=...&search.menuid=123">가입인사</a>
                # menu_id_match = None
                menu_id = None
                content = await page.content()
                soup = BeautifulSoup(content, "lxml")
                
                # 가입인사 / 등업 게시판 메뉴 ID 파싱 (단어 매칭)
                search_kws = [cond.welcome_board_name, "가입인사", "등업"]
                for a in soup.find_all("a"):
                    text = a.text.strip()
                    href = a.get("href", "")
                    if any(kw in text for kw in search_kws if kw):
                        match = re.search(r"(?:menuid|search\.menuid|menus/)=(\d+)", href)
                        if match:
                            menu_id = match.group(1)
                            break
                            
                if not menu_id:
                    log_event("LEVEL_UP", "WARNING", f"'{cond.welcome_board_name}' 게시판 메뉴 ID를 자동 획득하지 못했습니다. 기본 파싱으로 전환합니다.")
                else:
                    # 가입인사 글쓴이 수집 (최근 5페이지 탐색)
                    for page_num in range(1, 4):
                        welcome_url = get_mobile_board_url(club_id, menu_id, page_num)
                        await page.goto(welcome_url)
                        
                        # iframe 내부에 게시판 목록이 렌더링되므로, iframe 요소 확인
                        # PC 버전의 경우 'cafe_main' 이라는 iframe 내에 게시글 목록이 위치함
                        iframe_element = await page.query_selector("iframe#cafe_main")
                        if iframe_element:
                            frame = await iframe_element.content_frame()
                            # 작성자 닉네임이 있는 td.td_name a.html 혹은 class="m-tcol-c" 파싱
                            # PC 카페 게시판 작성자 셀렉터: `td.td_name a` 또는 `td.td_name div.pers_nick_area`
                            # 모바일 주소(`https://m.cafe.naver.com/ArticleList.nhn?search.clubid={club_id}&search.menuid={menu_id}`)가 iframe이 없어 훨씬 안정적임
                            pass
                        
                        # 더 간단하고 안전한 모바일 버전으로 게시판 조회
                        m_welcome_url = get_mobile_board_url(club_id, menu_id, page_num)
                        await page.goto(m_welcome_url)
                        await page.wait_for_load_state("networkidle")
                        
                        # 모바일 카페 글 목록에서 작성자 정보 추출 (DOM & BeautifulSoup 다중 검색)
                        content = await page.content()
                        soup = BeautifulSoup(content, "lxml")
                        
                        # 1) BeautifulSoup 기반 닉네임 셀렉터
                        for nick_el in soup.select("span.user, em.nick, .nick, .user_name, .ellip, div.pers_nick_area"):
                            nick_text = nick_el.text.strip()
                            if nick_text and len(nick_text) < 30 and nick_text not in ["댓글", "좋아요", "조회"]:
                                welcome_board_writers.add(nick_text)
                                
                        # 2) Playwright query_selector Fallback
                        nick_elements = await page.query_selector_all("span.user, em.nick, .nick, .user_name")
                        for el in nick_elements:
                            try:
                                nick = await el.inner_text()
                                nick = nick.strip()
                                if nick and nick not in ["댓글", "좋아요", "조회"]:
                                    welcome_board_writers.add(nick)
                            except Exception:
                                pass
                                
                    log_event("LEVEL_UP", "INFO", f"가입인사 게시판 작성자 {len(welcome_board_writers)}명 수집 완료.")

                # 2. 전체 회원 관리 페이지로 이동하여 조건 체크 및 등업 처리
                # PC 카페 멤버 관리 URL: `https://cafe.naver.com/ManageMemberRowList.nhn?clubid={club_id}`
                member_manage_url = get_member_manage_url(club_id)
                await page.goto(member_manage_url)
                await page.wait_for_load_state("networkidle")
                
                # 멤버 목록 테이블 행 파싱
                # 테이블 선택: `table.tbl_type` 혹은 멤버 행 `tr`들
                # 각 tr에서 닉네임, 등급, 방문수, 게시글수, 댓글수, 가입일 등을 추출
                # 멤버 리스트 tr들의 셀렉터는 보통 `tr[id^="member_"]` 또는 관리자용 멤버 테이블의 `tbody tr`
                # 여기서는 테이블 내 tr들을 루프
                # 네이버 카페 관리자 페이지 닉네임 위치: `td.name a` 또는 `div.pers_nick_area a`
                # 방문수: `td` 중 방문수 텍스트를 포함하는 영역
                # 댓글수: `td` 중 댓글 텍스트
                
                # 등업 대상 회원을 모아서 등업 처리를 요청할 체크박스를 체크합니다.
                tr_elements = await page.query_selector_all("form[name='frm'] table.tbl_type tbody tr")
                
                levelup_candidates = []
                
                for tr in tr_elements:
                    # 닉네임 파싱
                    nick_el = await tr.query_selector("td.name a, td.nick a")
                    if not nick_el:
                        continue
                    nickname = await nick_el.inner_text()
                    nickname = nickname.strip()
                    
                    # 닉네임 무작위 숫자 검증
                    if not self.is_random_numeric_nickname(nickname, cond.min_nickname_length):
                        continue
                        
                    # 현재 멤버의 등급이 이미 정회원 이상인지 확인하기 위해 등급 필드 파싱
                    # 관리자 페이지 테이블 열 구조: 
                    # 1. 체크박스, 2. 아이디, 3. 닉네임, 4. 등급, 5. 가입일, 6. 최종방문일, 7. 방문수, 8. 게시글수, 9. 댓글수 등
                    # 브라우저 요소에서 td 텍스트 추출
                    tds = await tr.query_selector_all("td")
                    if len(tds) < 8:
                        continue
                        
                    grade_text = await tds[3].inner_text()  # 등급 열
                    grade_text = grade_text.strip()
                    
                    # 이미 등업이 완료된 회원이면 스킵 (예: '정회원' 이상)
                    # 보통 '새싹멤버' 또는 '가입회원'이 등업 대상
                    if "새싹" not in grade_text and "가입" not in grade_text:
                        continue
                        
                    visit_text = await tds[6].inner_text()  # 방문수 열
                    visit_count = int(re.sub(r"\D", "", visit_text)) if visit_text else 0
                    
                    comment_text = await tds[8].inner_text()  # 댓글수 열
                    comment_count = int(re.sub(r"\D", "", comment_text)) if comment_text else 0
                    
                    # 방문 횟수 및 댓글 수 충족 검증
                    if visit_count < cond.min_visit_count or comment_count < cond.min_comment_count:
                        continue
                        
                    # 가입인사 게시판 작성 여부 검증
                    if cond.check_welcome_post and (nickname not in welcome_board_writers):
                        continue
                        
                    # 모든 조건을 충족한 등업 대상자 확정
                    levelup_candidates.append({
                        "nickname": nickname,
                        "tr": tr,
                        "checkbox": await tr.query_selector("input[type='checkbox']")
                    })
                
                if not levelup_candidates:
                    log_event("LEVEL_UP", "SUCCESS", "등업 기준을 충족하는 신규 회원이 없습니다.")
                    await browser.close()
                    return {"status": "SUCCESS", "message": "등업 대상 회원 없음"}
                
                # 대상자들 체크박스 클릭
                count = 0
                for candidate in levelup_candidates:
                    cb = candidate["checkbox"]
                    if cb and not await cb.is_checked():
                        await cb.click()
                        count += 1
                        log_event("LEVEL_UP", "INFO", f"등업 대상자 체크 완료: {candidate['nickname']}")
                
                if count > 0:
                    # 등업 처리 진행
                    # 등급변경 단추: `등급변경` 텍스트를 가진 버튼 클릭
                    # 등업 다이얼로그나 드롭다운 조작 필요
                    # 관리자 페이지 등급변경 방식: '등급변경' 버튼 클릭 시 레이어가 뜨거나 변경 다이얼로그 노출
                    # 셀렉터: `a:has-text('등급변경')` 또는 `button:has-text('등급변경')`
                    change_grade_btn = page.locator("a:has-text('등급변경'), button:has-text('등급변경')").first
                    if change_grade_btn:
                        await change_grade_btn.click()
                        await page.wait_for_timeout(2000)
                        
                        # 등급 선택 Select 드롭다운 선택 (일반적으로 등급변경 레이어 내 Select box)
                        # 변경할 등급 (예: "정회원" 또는 "일반멤버") 선택
                        # 2번째 옵션 등으로 변경 처리
                        select_box = await page.query_selector("select#changeGradeLevel, select[name='gradeLevel']")
                        if select_box:
                            # 2등급(정회원 등)을 밸류나 텍스트로 선택. 대개 밸류가 등급 레벨(예: "2", "3")
                            # 여기서는 첫 번째 등업 등급을 안전하게 선택
                            await select_box.select_option(index=1) # 첫번째 등업 대상 등급
                            
                        # '적용' 또는 '변경' 확인 버튼 클릭
                        confirm_btn = page.locator("a:has-text('변경'), button:has-text('변경'), a:has-text('적용')").first
                        if confirm_btn:
                            page.on("dialog", lambda dialog: dialog.accept()) # 경고창 수락
                            await confirm_btn.click()
                            await page.wait_for_timeout(3000)
                            
                            log_event("LEVEL_UP", "SUCCESS", f"회원 {count}명에 대한 자동 등업 처리를 완료했습니다.")
                            await browser.close()
                            return {"status": "SUCCESS", "message": f"{count}명 등업 완료"}
                            
                    log_event("LEVEL_UP", "FAILED", "등급변경 버튼 또는 레이어를 제어하지 못했습니다.")
                    await browser.close()
                    return {"status": "FAILED", "message": "변경 제어 실패"}
                
                await browser.close()
                return {"status": "SUCCESS", "message": "등업 처리 완료"}
                
            except Exception as e:
                log_event("LEVEL_UP", "FAILED", f"등업 처리 중 에러 발생: {str(e)}")
                await browser.close()
                return {"status": "FAILED", "message": str(e)}

    async def write_news_article(self, title: str, content: str, source_url: str, headless: bool = True) -> Dict[str, Any]:
        """
        카페의 뉴스 게시판에 가공된 뉴스 기사를 자동으로 작성합니다.
        """
        self.settings = load_settings()
        club_id = self.settings.cafe.club_id
        board_id = self.settings.news.publish_board_id
        
        if not club_id:
            log_event("NEWS_POST", "FAILED", "네이버 카페 Club ID가 설정되지 않았습니다.")
            return {"status": "FAILED", "message": "Club ID 미설정"}
        if not board_id:
            log_event("NEWS_POST", "FAILED", "발행 대상 뉴스 게시판 ID(publish_board_id)가 설정되지 않았습니다.")
            return {"status": "FAILED", "message": "게시판 ID 미설정"}
            
        # 출처 표기 추가
        # 요청하신 정확한 기사 원문 표기 양식 (📌 기사 원문)
        full_content = (
            f"{content.strip()}\n\n"
            f"📌 기사 원문\n"
            f"{source_url}"
        )
        
        # 네이버 카페 정식 최신 웹 글쓰기 URL (boardType=L)
        write_url = f"https://cafe.naver.com/ca-fe/cafes/{club_id}/menus/{board_id}/articles/write?boardType=L"
        
        async with async_playwright() as p:
            context = await self._get_logged_in_context(p, headless=headless)
            if not context:
                return {"status": "FAILED", "message": "로그인 세션 없음"}
                
            browser = context.browser
            await self._apply_stealth(context)
            page = await context.new_page()
            
            try:
                log_event("NEWS_POST", "INFO", f"정식 카페 글쓰기 페이지에 접속합니다. (제목: {title[:20]}...)")
                await page.goto(write_url)
                await page.wait_for_timeout(3000)
                
                # 로그인 세션 만료로 로그인 페이지로 리다이렉트 되었는지 확인
                curr_url = page.url
                if "nidlogin" in curr_url or "login" in curr_url:
                    log_event("NEWS_POST", "FAILED", "네이버 로그인 세션이 만료되었습니다. 대시보드에서 [수동 로그인]을 1회 진행해 주세요.")
                    await browser.close()
                    return {"status": "FAILED", "message": "로그인 세션 만료 (수동 로그인 필요)"}
                    
                # 모바일/PC 글쓰기 뷰 입력 필드 분석 (다중 셀렉터 지원)
                # 제목 입력창 파싱
                title_selector = "textarea.write_title, input#subject, input.subject, textarea#subject, input[name='subject'], input[placeholder*='제목'], textarea[placeholder*='제목']"
                subject_el = await page.query_selector(title_selector)
                
                if subject_el:
                    try:
                        await subject_el.focus()
                    except Exception:
                        await subject_el.click(force=True)
                    await subject_el.fill(title)
                else:
                    # 스마트에디터 ONE 모바일/PC fallback
                    title_loc = page.locator("textarea[class*='title'], input[class*='title'], [placeholder*='제목']").first
                    if await title_loc.is_visible(timeout=3000):
                        await title_loc.click(force=True)
                        await title_loc.fill(title)
                    else:
                        raise Exception("카페 글쓰기 페이지에서 제목 입력란을 찾지 못했습니다. (로그인 세션 확인 필요)")
                    
                # 본문 입력창 파싱 (스마트에디터 ONE 숨김 클립보드 div 제척 및 가시 에디터 타겟팅)
                editor_loc = page.locator("div.se-content [contenteditable='true'], div[contenteditable='true']:not([aria-hidden='true']), p.se-text-paragraph").first
                if await editor_loc.is_visible(timeout=3000):
                    await editor_loc.click(force=True)
                    await page.wait_for_timeout(500)
                    
                    # 줄바꿈(\n) 단위로 나누어 Enter 입력으로 스마트에디터 ONE 정식 단락 구성
                    lines = full_content.split("\n")
                    for idx, line in enumerate(lines):
                        if line.strip():
                            # 유니코드 이모지(📌)와 한글 텍스트 분리 타이핑하여 이모지 뒤 한글 텍스트 누락 100% 예방
                            if "📌" in line:
                                await page.keyboard.insert_text("📌 ")
                                await page.keyboard.insert_text(line.replace("📌", "").strip())
                            else:
                                await page.keyboard.insert_text(line)
                                
                            # URL 주소 입력 직후 Enter 및 Space를 눌러 스마트에디터 ONE 하이퍼링크/미리보기 카드 즉시 생성
                            if "http://" in line or "https://" in line:
                                await page.wait_for_timeout(300)
                                await page.keyboard.press("Enter")
                                await page.wait_for_timeout(300)
                        if idx < len(lines) - 1:
                            await page.keyboard.press("Enter")
                            await page.wait_for_timeout(100)
                else:
                    content_el = await page.query_selector("textarea.write_content, textarea#content, textarea[placeholder*='내용']")
                    if content_el:
                        await content_el.click(force=True)
                        await content_el.fill(full_content)
                    else:
                        raise Exception("카페 글쓰기 페이지에서 본문 입력 에디터를 찾지 못했습니다.")
                
                await page.wait_for_timeout(1000)
                
                # 경고/확인 팝업 자동 수락 (등록 확인 다이얼로그 등)
                page.on("dialog", lambda dialog: dialog.accept())
                
                # 스마트에디터 ONE 신형 우측 '등록' 버튼 (a.BaseButton--skinGreen 및 클래식 btn_register 모두 커버)
                submit_btn = page.locator("a.BaseButton--skinGreen, button.BaseButton--skinGreen, button.btn_register, a:has-text('등록'):not(:has-text('임시'))").first
                
                if await submit_btn.is_visible(timeout=5000):
                    # 확실하게 엘리먼트가 준비될 때까지 대기 후 클릭
                    await submit_btn.scroll_into_view_if_needed()
                    await submit_btn.click(force=True)
                    await page.wait_for_timeout(4000)
                    
                    # 실시간 클릭 직후 상태 스크린샷 저장 (오류 및 팝업 파악용)
                    await page.screenshot(path="data/submit_check.png")
                    
                    # 등록 처리 완료 대기 (최대 10초 대기하며 URL이 write에서 게시글 상세로 리다이렉트 되었는지 감시)
                    success_published = False
                    article_id = None
                    
                    try:
                        await page.wait_for_function("() => !location.href.includes('write')", timeout=10000)
                        final_url = page.url
                        # ArticleRead 또는 articles/로 이동했으면 등록 성공으로 확정
                        if "ArticleRead" in final_url or "articles/" in final_url:
                            success_published = True
                            # 글 ID 추출 시도
                            id_match = re.search(r"(?:articleid|articles)[\=/](\d+)", final_url, re.I)
                            if id_match:
                                article_id = id_match.group(1)
                    except Exception:
                        pass
                        
                    # 만약 리다이렉트가 명확하지 않은 경우, 모바일 게시판 목록으로 직접 이동하여 실시간 등록 확인 교차 검증 수행
                    if not success_published:
                        try:
                            list_url = f"https://m.cafe.naver.com/ca-fe/web/cafes/{club_id}/menus/{board_id}"
                            log_event("NEWS_POST", "INFO", f"리다이렉션 감지 실패로 인해, 게시판 목록({list_url})에서 교차 확인을 수행합니다.")
                            await page.goto(list_url)
                            await page.wait_for_timeout(3000)
                            
                            # 게시판 목록의 최근 글 제목들 수집
                            latest_titles = await page.evaluate("""() => {
                                const elements = document.querySelectorAll('a.mainLink, a.article');
                                return Array.from(elements).map(el => el.innerText.trim());
                            }""")
                            
                            # 작성한 제목이 목록 내에 존재하는지 확인
                            clean_title = title.strip()
                            if any(clean_title in t or t in clean_title for t in latest_titles):
                                success_published = True
                                log_event("NEWS_POST", "INFO", "게시판 목록 교차 검증을 통해 글이 정상 게재되었음을 성공적으로 판독했습니다.")
                        except Exception as list_err:
                            log_event("NEWS_POST", "WARNING", f"게시판 목록 교차 확인 중 오류: {str(list_err)}")
                            
                    if success_published:
                        msg = f"카페 뉴스 기사 등록 완료 및 실측 검증 성공: {title} (ID: {article_id or '확인 불가'})"
                        log_event("NEWS_POST", "SUCCESS", msg)
                        try:
                            from backend.discord_notifier import notify_action_log
                            notify_action_log("NEWS_POST", "SUCCESS", msg)
                        except Exception:
                            pass
                        await browser.close()
                        return {"status": "SUCCESS", "message": "뉴스 기사 게시 및 최종 검증 완료"}
                    else:
                        # 등록 실패 스크린샷 추가 저장
                        await page.screenshot(path="data/submit_failed.png")
                        raise Exception("글 등록 버튼을 누른 후 리다이렉션 및 게시판 목록 검증에 모두 실패하였습니다 (등록 유실 추정).")
                else:
                    raise Exception("카페 글쓰기 화면에서 등록 버튼을 찾지 못했습니다.")
                    
            except Exception as e:
                err_msg = f"뉴스 자동 게시 중 에러 발생: {str(e)}"
                log_event("NEWS_POST", "FAILED", err_msg)
                try:
                    from backend.discord_notifier import notify_action_log
                    notify_action_log("NEWS_POST", "FAILED", err_msg)
                except Exception:
                    pass
                await browser.close()
                return {"status": "FAILED", "message": str(e)}
