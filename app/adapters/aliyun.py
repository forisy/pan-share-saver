import os
from typing import Optional, Dict, Any
import re
from urllib.parse import urlparse, parse_qs
from ..config import HEADLESS, ALIYUN_NODE_PATH, ALIYUN_TARGET_FOLDER, ALIYUN_USER_DATA_DIR
from ..browser import manager
from .base import ShareAdapter

class AliyunAdapter(ShareAdapter):
    def __init__(self):
        self._sessions = {}

    def get_qr_code(self):
        import uuid, time
        ctx = manager.new_persistent_context(ALIYUN_USER_DATA_DIR)
        page = ctx.new_page()
        try:
            page.goto("https://www.alipan.com/sign/in", timeout=30000)
        except Exception:
            page.goto("https://www.aliyundrive.com/sign/in", timeout=30000)
        try:
            btn = page.get_by_text("扫码登录", exact=False)
            if btn.count():
                btn.first.click()
        except Exception:
            pass
        locator = page.locator(
            "div[class*='login']"
        ).first
        time.sleep(2)
        png_bytes = locator.screenshot()
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "ctx": ctx,
            "page": page,
            "expires_at": time.time() + 180,
            "logged_in": False,
        }
        return session_id, png_bytes

    def poll_login_status(self, session_id):
        import time
        session = self._sessions.get(session_id)
        if not session:
            return
        page = session["page"]
        for _ in range(60):
            try:
                btn = page.query_selector("text=文件分类")
                if btn is not None:
                    session["logged_in"] = True
                    try:
                        session["ctx"].close()
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            time.sleep(3)
        self._sessions.pop(session_id, None)

    def check_login_status(self, session_id):
        import time
        session = self._sessions.get(session_id)
        if not session:
            return {"status": "not_found"}
        if time.time() > session["expires_at"]:
            try:
                session["ctx"].close()
            except Exception:
                pass
            self._sessions.pop(session_id, None)
            return {"status": "expired"}
        if session["logged_in"]:
            try:
                session["ctx"].close()
            except Exception:
                pass
            self._sessions.pop(session_id, None)
            return {"status": "success"}
        return {"status": "pending"}

    @property
    def name(self) -> str:
        return "aliyun"

    def _extract(self, link: str) -> Dict[str, Optional[str]]:
        m = re.search(r'https?://[^\s]+', link)
        url = m.group(0) if m else link
        code = None
        try:
            qs = parse_qs(urlparse(url).query)
            code = (qs.get('pwd') or qs.get('password') or qs.get('code'))
            code = code[0] if code else None
        except Exception:
            pass
        if not code:
            m2 = re.search(r'(提取码|密码)[:：\s]*([a-zA-Z0-9]{4})', link)
            if m2:
                code = m2.group(2)
                url = url.split(m2.group(1))[0]
        return {"url": url, "code": code}

    async def transfer(self, link: str) -> Dict[str, Any]:
        import asyncio

        def _do():
            ctx = manager.new_persistent_context(ALIYUN_USER_DATA_DIR)
            page = ctx.new_page()
            info = self._extract(link)
            url = (info["url"] or "").strip().strip('`"')
            print("goto login check")
            page.goto("https://www.alipan.com/drive/home", timeout=30000)
            page.wait_for_selector("text=文件分类", timeout=30000)
            print(f"goto {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=40000)
            page.wait_for_timeout(1000)
            try:
                need_pwd = page.get_by_text("分享了文件", exact=False)
                print(f'test 提取码: {need_pwd.count()}')
                if need_pwd.count():
                    code = info.get("code")
                    if not code:
                        return {
                            "status": "fail",
                            "provider": self.name,
                            "share_link": url,
                            "message": "缺少提取码",
                        }
                    inp = page.query_selector("input[placeholder*=请输入提取码], input[type='text']")
                    if inp:
                        try:
                            inp.fill(code)
                        except Exception:
                            pass
                    btn = page.get_by_text("极速查看文件", exact=False)
                    if btn.count():
                        try:
                            btn.first.click()
                        except Exception:
                            pass
                    page.wait_for_load_state("domcontentloaded", timeout=30000)
            except Exception:
                pass

            try:
                try:
                    page.wait_for_selector("text=立即保存", timeout=30000)
                except Exception:
                    page.wait_for_load_state("networkidle", timeout=30000)

                print('wait 保存到网盘')
                save_btn = page.get_by_text("立即保存", exact=False)
                if save_btn.count():
                    try:
                        save_btn.first.click()
                    except Exception:
                        pass

                save_btn = page.get_by_text("保存到此处", exact=False)
                if save_btn.count():
                    try:
                        save_btn.first.click()
                    except Exception:
                        pass
                page.wait_for_timeout(1000)
                return {
                    "status": "success",
                    "provider": self.name,
                    "share_link": link,
                    "target_path": None,
                    "message": "transferred",
                }
            finally:
                ctx.close()

        return await asyncio.to_thread(_do)
