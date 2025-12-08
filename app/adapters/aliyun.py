import os
from typing import Optional, Dict, Any
import re
from urllib.parse import urlparse, parse_qs
from ..config import ALIYUN_STORAGE_STATE, HEADLESS, ALIYUN_NODE_PATH, ALIYUN_TARGET_FOLDER
from ..browser import manager
from .base import ShareAdapter

class AliyunAdapter(ShareAdapter):
    def __init__(self):
        self._sessions = {}

    def get_qr_code(self):
        from playwright.sync_api import sync_playwright
        import uuid, time
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=HEADLESS)
        ctx = browser.new_context()
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
            "pw": pw,
            "browser": browser,
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
                    storage_dir = os.path.dirname(ALIYUN_STORAGE_STATE)
                    if not os.path.exists(storage_dir):
                        os.makedirs(storage_dir, exist_ok=True)
                    session["ctx"].storage_state(path=ALIYUN_STORAGE_STATE)
                    session["logged_in"] = True
                    return
            except Exception:
                pass
            time.sleep(3)
        try:
            session["ctx"].close()
            session["browser"].close()
            session["pw"].stop()
        except Exception:
            pass
        self._sessions.pop(session_id, None)

    def check_login_status(self, session_id):
        import time
        session = self._sessions.get(session_id)
        if not session:
            return {"status": "not_found"}
        if time.time() > session["expires_at"]:
            try:
                session["ctx"].close()
                session["browser"].close()
                session["pw"].stop()
            except Exception:
                pass
            self._sessions.pop(session_id, None)
            return {"status": "expired"}
        if session["logged_in"]:
            try:
                session["ctx"].close()
                session["browser"].close()
                session["pw"].stop()
            except Exception:
                pass
            self._sessions.pop(session_id, None)
            return {"status": "success"}
        return {"status": "pending"}

    @property
    def name(self) -> str:
        return "aliyun"

    async def transfer(self, link: str) -> Dict[str, Any]:
        import asyncio

        def _do():
            ctx = manager.new_context(ALIYUN_STORAGE_STATE)
            page = ctx.new_page()
            print("goto login check")
            print(f"goto {link}")
            try:
                page.goto(link, wait_until="domcontentloaded", timeout=40000)
                try:
                    page.wait_for_selector("text=立即保存", timeout=30000)
                except Exception:
                    page.wait_for_load_state("networkidle", timeout=30000)

                print('wait 保存到网盘')
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
