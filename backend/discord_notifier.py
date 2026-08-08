import httpx
from datetime import datetime, timezone
from backend.config import load_settings
from backend.logger import log_event

def send_discord_webhook_embed(
    title: str,
    description: str,
    fields: list = None,
    color: int = 0x3498DB,
    thumbnail_url: str = None,
    webhook_type: str = "default"
) -> bool:
    """
    가독성이 대폭 향상된 프리미엄 디스코드 Rich Embed 알림을 발송합니다.
    """
    settings = load_settings()
    
    # 웹훅 종류별 분기 매핑 (비어 있으면 기본 webhook_url로 fallback)
    webhook_url = ""
    if webhook_type == "report":
        webhook_url = settings.discord.report_webhook_url or settings.discord.webhook_url
    elif webhook_type == "suggestion":
        webhook_url = settings.discord.suggestion_webhook_url or settings.discord.webhook_url
    elif webhook_type == "log":
        webhook_url = settings.discord.log_webhook_url or settings.discord.webhook_url
    else:
        webhook_url = settings.discord.webhook_url
        
    if not webhook_url:
        log_event("DISCORD_NOTIFY", "WARNING", f"디스코드 Webhook URL({webhook_type})이 설정되지 않아 알림을 건너뜁니다.")
        return False
        
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {
            "text": "Naver Cafe Auto Manager • 실시간 카페 알림 엔진"
        }
    }
    
    if fields:
        embed["fields"] = fields
        
    if thumbnail_url:
        embed["thumbnail"] = {"url": thumbnail_url}
        
    payload = {"embeds": [embed]}
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(webhook_url, json=payload)
            if response.status_code in [200, 204]:
                return True
            else:
                log_event("DISCORD_NOTIFY", "FAILED", f"디스코드 전송 실패 (상태 코드: {response.status_code})")
                return False
    except Exception as e:
        log_event("DISCORD_NOTIFY", "FAILED", f"디스코드 웹훅 전송 중 에러 발생: {str(e)}")
        return False

def notify_report(article_title: str, author: str, article_link: str, posted_at: str = "") -> bool:
    """신고 게시판 감시 알림 (시원시원한 가독성 & Crimson Red)."""
    title = "🚨 [신고 게시판] 새로운 신고글 감지"
    time_line = f"🕐 **작성 시간:** `{posted_at}`\n" if posted_at else ""
    description = (
        f"**게시글 제목**\n"
        f"> **{article_title}**\n\n"
        f"👤 **작성자:** `{author}`\n"
        f"{time_line}"
        f"🔗 **바로가기:** [👉 카페 게시글 읽기]({article_link})\n"
        f"🖥️ **대시보드:** [👉 대시보드 신고·건의 모니터링함](http://localhost:8000/#alerts)"
    )
    return send_discord_webhook_embed(
        title=title,
        description=description,
        color=0xE74C3C, # Crimson Red
        webhook_type="report"
    )

def notify_suggestion(article_title: str, author: str, article_link: str, posted_at: str = "") -> bool:
    """건의 게시판 감시 알림 (시원시원한 가독성 & Cyan Blue)."""
    title = "💡 [건의 게시판] 새로운 건의글 감지"
    time_line = f"🕐 **작성 시간:** `{posted_at}`\n" if posted_at else ""
    description = (
        f"**게시글 제목**\n"
        f"> **{article_title}**\n\n"
        f"👤 **작성자:** `{author}`\n"
        f"{time_line}"
        f"🔗 **바로가기:** [👉 카페 게시글 읽기]({article_link})\n"
        f"🖥️ **대시보드:** [👉 대시보드 신고·건의 모니터링함](http://localhost:8000/#alerts)"
    )
    return send_discord_webhook_embed(
        title=title,
        description=description,
        color=0x3498DB, # Cyan Blue
        webhook_type="suggestion"
    )

def notify_team_classification_failure(article_title: str, article_link: str, error_msg: str) -> bool:
    """팀 분류 실패 경고 알림 (Amber Gold)."""
    title = "⚠️ [뉴스 크롤러] 미분류 기사 수집 경고"
    
    # 여러 줄 메시지 가독성 정돈 (플레이라이트 Call log 등 축약)
    cleaned_msg = error_msg.strip()
    if "Call log:" in cleaned_msg:
        cleaned_msg = cleaned_msg.split("Call log:")[0].strip()
        
    msg_box = f"```\n{cleaned_msg}\n```" if "\n" in cleaned_msg else f"`{cleaned_msg}`"
    
    description = (
        f"**기사 제목**\n"
        f"> **{article_title}**\n\n"
        f"📝 **사유:**\n{msg_box}\n"
        f"🔗 **기사 바로가기:** [👉 원문 기사 바로가기]({article_link})\n"
        f"🖥️ **대시보드:** [👉 대시보드 뉴스 보관함](http://localhost:8000/#archives)"
    )
    return send_discord_webhook_embed(
        title=title,
        description=description,
        color=0xF1C40F, # Amber Gold
        webhook_type="log"
    )

def notify_action_log(action_type: str, status: str, message: str) -> bool:
    """통합 자동화 작업 로그 알림 (Emerald Green / Alizarin Red)."""
    is_success = status.upper() == "SUCCESS"
    
    # 가입 승인 및 회원 등업 성공 로그 중 실제 건수가 0명(대기자 없음)인 무반응 로그는 디스코드 알림 발송 억제
    if action_type in ["JOIN_APPROVE", "LEVEL_UP"] and is_success:
        if "0명" in message or "없습니다" in message or "0건" in message:
            return True
            
    title = f"🟢 [작업 로그] {action_type} 성공" if is_success else f"🔴 [작업 로그] {action_type} 실패"
    color = 0x2ECC71 if is_success else 0xE74C3C
    
    # 세분화 탭 딥링크 매핑
    dashboard_tab_url = "http://localhost:8000/#logs"
    tab_name = "실시간 작업 이력"
    if "JOIN_APPROVE" in action_type or "LEVEL_UP" in action_type:
        dashboard_tab_url = "http://localhost:8000/#members"
        tab_name = "회원 가입/등업 내역"
    elif "NEWS_PUBLISH" in action_type:
        dashboard_tab_url = "http://localhost:8000/#archives"
        tab_name = "뉴스 기사 보관함"
    elif "BOARD_MONITOR" in action_type:
        dashboard_tab_url = "http://localhost:8000/#alerts"
        tab_name = "신고·건의 모니터링함"


    # 가독성 정돈 및 복잡한 플레이라이트 스택 축약
    cleaned_msg = message.strip()
    if "Call log:" in cleaned_msg:
        cleaned_msg = cleaned_msg.split("Call log:")[0].strip()
        
    msg_box = f"```\n{cleaned_msg}\n```" if "\n" in cleaned_msg else f"> **{cleaned_msg}**"
    
    description = (
        f"📝 **상세 메시지**\n"
        f"{msg_box}\n\n"
        f"⚙️ **상태:** `{status}`\n"
        f"🖥️ **대시보드:** [👉 대시보드 {tab_name} 바로가기]({dashboard_tab_url})"
    )
    return send_discord_webhook_embed(
        title=title,
        description=description,
        color=color,
        webhook_type="log"
    )


def send_discord_webhook(title: str, content_fields: dict, color: int = 0x3498DB) -> bool:
    """하위 호환성을 위한 래퍼 함수입니다."""
    desc_lines = []
    for k, v in content_fields.items():
        desc_lines.append(f"**{k}:** {v}")
    description = "\n".join(desc_lines)
    return send_discord_webhook_embed(title=title, description=description, color=color, webhook_type="default")


def send_discord_webhook_with_file(
    title: str,
    description: str,
    file_path: str,
    color: int = 0xE74C3C,
    webhook_type: str = "log"
) -> bool:
    """
    로컬 파일(스크린샷 등)을 첨부하여 프리미엄 디스코드 웹훅 알림을 전송합니다.
    첨부된 파일은 Embed의 메인 이미지로 바인딩되어 출력됩니다.
    """
    import os
    import json
    if not os.path.exists(file_path):
        log_event("DISCORD_NOTIFY", "WARNING", f"첨부할 파일이 존재하지 않아 일반 웹훅 전송으로 대체합니다: {file_path}")
        return send_discord_webhook_embed(title=title, description=description, color=color, webhook_type=webhook_type)
        
    settings = load_settings()
    webhook_url = ""
    if webhook_type == "report":
        webhook_url = settings.discord.report_webhook_url or settings.discord.webhook_url
    elif webhook_type == "suggestion":
        webhook_url = settings.discord.suggestion_webhook_url or settings.discord.webhook_url
    elif webhook_type == "log":
        webhook_url = settings.discord.log_webhook_url or settings.discord.webhook_url
    else:
        webhook_url = settings.discord.webhook_url
        
    if not webhook_url:
        log_event("DISCORD_NOTIFY", "WARNING", f"디스코드 Webhook URL이 설정되지 않아 파일 알림을 건너뜁니다.")
        return False
        
    file_name = os.path.basename(file_path)
    
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "image": {"url": f"attachment://{file_name}"},
        "footer": {
            "text": "Naver Cafe Auto Manager • 실시간 오류 추적 모듈"
        }
    }
    
    payload = {"embeds": [embed]}
    
    try:
        with open(file_path, "rb") as f:
            files = {
                "file": (file_name, f, "image/png")
            }
            data = {
                "payload_json": json.dumps(payload)
            }
            
            with httpx.Client(timeout=15.0) as client:
                response = client.post(webhook_url, data=data, files=files)
                if response.status_code in [200, 204]:
                    return True
                else:
                    log_event("DISCORD_NOTIFY", "FAILED", f"디스코드 파일 전송 실패 (상태 코드: {response.status_code})")
                    return False
    except Exception as e:
        log_event("DISCORD_NOTIFY", "FAILED", f"디스코드 파일 웹훅 전송 중 에러 발생: {str(e)}")
        return False


def notify_news_post_failure_with_screenshot(article_title: str, article_link: str, error_msg: str, screenshot_path: str) -> bool:
    """뉴스 게시글 3회 발행 재시도 최종 실패 시 스크린샷과 함께 디스코드에 알립니다."""
    title = "🚨 [뉴스 발행 최종 실패] 네이버 카페 자동 포스팅 장애 감지"
    
    cleaned_msg = error_msg.strip()
    if "Call log:" in cleaned_msg:
        cleaned_msg = cleaned_msg.split("Call log:")[0].strip()
        
    msg_box = f"```\n{cleaned_msg}\n```" if "\n" in cleaned_msg else f"`{cleaned_msg}`"
    
    description = (
        f"**발행 시도한 뉴스 제목**\n"
        f"> **{article_title}**\n\n"
        f"🔴 **장애 세부 정보:**\n{msg_box}\n"
        f"⏱️ **처리 내역:** `자동 재작성 3회 전수 실패`\n"
        f"🔗 **기사 출처:** [👉 원문 링크]({article_link})\n"
        f"🖥️ **대시보드:** [👉 대시보드 뉴스 보관함](http://localhost:8000/#archives)\n\n"
        f"⬇️ **최종 시도 시점 브라우저 스크린샷:**"
    )
    
    return send_discord_webhook_with_file(
        title=title,
        description=description,
        file_path=screenshot_path,
        color=0xE74C3C,
        webhook_type="log"
    )

