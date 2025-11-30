import os
from typing import Optional, Dict, Any
import re
from urllib.parse import urlparse, parse_qs
from ..config import BAIDU_STORAGE_STATE, HEADLESS, BAIDU_NODE_PATH, BAIDU_TARGET_FOLDER
from ..browser import manager
from .base import ShareAdapter

 

class BaiduAdapter(ShareAdapter):
    def __init__(self):
        self._sessions = {}

    def get_qr_code(self):
        from playwright.sync_api import sync_playwright
        import uuid, time, base64, io
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=HEADLESS)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto("https://pan.baidu.com/")
        try:
            btn = page.get_by_text("去登录", exact=False)
            if btn.count():
                btn.first.click()
        except:
            pass
        try:
            btn = page.get_by_text("扫码登录", exact=False)
            if btn.count():
                btn.first.click()
        except:
            pass
        locator = page.locator(
            "img[class*='tang-pass-qrcode-img'], canvas, img[alt*=二维码], img[src*='qr']"
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
        import time, os
        session = self._sessions.get(session_id)
        if not session:
            return
        page = session["page"]
        for _ in range(60):
            try:
                btn = page.query_selector("text=去登录")
                if btn is None:
                    storage_dir = os.path.dirname(BAIDU_STORAGE_STATE)
                    if not os.path.exists(storage_dir):
                        os.makedirs(storage_dir, exist_ok=True)
                    session["ctx"].storage_state(path=BAIDU_STORAGE_STATE)
                    session["logged_in"] = True
                    return
            except Exception as e:
                print("poll error:", e)
            time.sleep(3)
        try:
            session["ctx"].close()
            session["browser"].close()
            session["pw"].stop()
        except:
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
            except:
                pass
            self._sessions.pop(session_id, None)
            return {"status": "expired"}
        if session["logged_in"]:
            try:
                session["ctx"].close()
                session["browser"].close()
                session["pw"].stop()
            except:
                pass
            self._sessions.pop(session_id, None)
            return {"status": "success"}
        return {"status": "pending"}

    @property
    def name(self) -> str:
        return "baidu"


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
        return {"url": url, "code": code}

    async def transfer(self, link: str) -> Dict[str, Any]:
        import asyncio

        def _do():
            ctx = manager.new_context(BAIDU_STORAGE_STATE)
            page = ctx.new_page()
            try:
                info = self._extract(link)
                url = (info["url"] or "").strip().strip('`"')
                print("goto login check")
                page.goto("https://pan.baidu.com/", wait_until="domcontentloaded", timeout=30000)
                if page.query_selector("text=去登录") is not None:
                    return {
                        "status": "fail",
                        "provider": self.name,
                        "share_link": url,
                        "message": "未登录，请先扫码登录后再转存",
                    }
                if not url:
                    return {
                        "status": "fail",
                        "provider": self.name,
                        "share_link": url,
                        "message": "分享链接无效",
                    }
                print(f"goto {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=40000)
                try:
                    need_pwd = page.get_by_text("提取码", exact=False)
                    print('test 提取码')
                    if need_pwd.count():
                        code = info.get("code")
                        if not code:
                            return {
                                "status": "fail",
                                "provider": self.name,
                                "share_link": url,
                                "message": "缺少提取码",
                            }
                        inp = page.query_selector("input[name*=pwd], input[aria-label*=提取码], input[type='text']")
                        if inp:
                            try:
                                inp.fill(code)
                            except Exception:
                                pass
                        btn = page.get_by_text("提取文件", exact=False)
                        if btn.count():
                            try:
                                btn.first.click()
                            except Exception:
                                pass
                        page.wait_for_load_state("domcontentloaded", timeout=30000)
                except Exception:
                    pass
                
                print('wait 保存到网盘')
                try:
                    page.wait_for_selector("text=保存到网盘", timeout=30000)
                except Exception:
                    page.wait_for_load_state("networkidle", timeout=30000)

                if BAIDU_TARGET_FOLDER:
                    print('click save-path')
                    btn_path = page.query_selector('div[class*="bottom-save-path"]') or page.query_selector('div[class*="save-path"]')
                    if btn_path:
                        try:
                            btn_path.click()
                        except Exception:
                            pass
                    try:
                        print('wait file-tree-container')
                        page.wait_for_selector("div[class*='file-tree-container'], div[class*='file-tree']", timeout=30000)
                    except Exception:
                        pass

                    print('set node-path')
                    folder = page.query_selector(f'[node-path="{BAIDU_NODE_PATH}"]')
                    if folder is None:
                        loc = page.get_by_text(BAIDU_TARGET_FOLDER, exact=False)
                        if loc.count():
                            folder = loc.first
                    if folder is not None:
                        try:
                            folder.click()
                        except Exception:
                            pass
                    page.wait_for_timeout(500)
                    print('confirm save-path')
                    confirm = page.query_selector('[node-type="confirm"]')
                    if confirm is None:
                        loc = page.get_by_text("确认", exact=False)
                        if loc.count():
                            confirm = loc.first
                    if confirm is not None:
                        try:
                            confirm.click()
                        except Exception:
                            pass
                    page.wait_for_timeout(800)
                    
                
                print('click 保存到网盘')
                save_btn = page.get_by_text("保存到网盘", exact=False)
                if save_btn.count():
                    try:
                        save_btn.first.click()
                    except Exception:
                        pass
                else:
                    alt = page.locator("text=保存")
                    if alt.count():
                        try:
                            alt.first.click()
                        except Exception:
                            pass
                page.wait_for_timeout(1000)
                return {
                    "status": "success",
                    "provider": self.name,
                    "share_link": url,
                    "target_path": None,
                    "message": "transferred",
                }
            finally:
                ctx.close()

        return await asyncio.to_thread(_do)