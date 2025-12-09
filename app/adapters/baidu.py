import os
from typing import Optional, Dict, Any
import re
from urllib.parse import urlparse, parse_qs
from ..config import HEADLESS, BAIDU_NODE_PATH, BAIDU_TARGET_FOLDER, BAIDU_USER_DATA_DIR
from ..browser import manager
from .base import ShareAdapter


class BaiduAdapter(ShareAdapter):
    def __init__(self):
        self._sessions = {}

    async def get_qr_code(self):
        import uuid, time, asyncio
        try:
            for sid, s in list(self._sessions.items()):
                try:
                    await s.get("ctx").close()
                except Exception:
                    pass
                self._sessions.pop(sid, None)
        except Exception:
            pass
        ctx = await manager.new_persistent_context(BAIDU_USER_DATA_DIR)
        page = await ctx.new_page()
        try:
            islogin = False
            await page.goto("https://pan.baidu.com/", timeout=30000)
            await asyncio.sleep(3)
            btn = await page.query_selector("text=我的文件")
            islogin = btn is not None
            png_bytes = b""
            if not islogin:
                try:
                    btn = page.get_by_text("去登录", exact=False)
                    if await btn.count():
                        await btn.first.click()
                except:
                    pass
                try:
                    btn = page.get_by_text("扫码登录", exact=False)
                    if await btn.count():
                        await btn.first.click()
                except:
                    pass
                locator = page.locator(
                    "div[class*='pass-login-pop-form'], img[class*='tang-pass-qrcode-img'], canvas, img[alt*=二维码], img[src*='qr']"
                ).first
                await asyncio.sleep(2)
                png_bytes = await locator.screenshot()
            session_id = str(uuid.uuid4())
            self._sessions[session_id] = {
                "ctx": ctx,
                "page": page,
                "expires_at": time.time() + 180,
                "logged_in": islogin,
            }
            return session_id, png_bytes, islogin
        except Exception as e:
            print(f"get_qr_code error: {e}")
            return str(uuid.uuid4()), b"", False

    async def poll_login_status(self, session_id):
        import asyncio
        session = self._sessions.get(session_id)
        if not session:
            return
        page = session["page"]
        for _ in range(60):
            try:
                btn = await page.query_selector("text=去登录")
                if btn is None:
                    session["logged_in"] = True
                    try:
                        await session["ctx"].close()
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            await asyncio.sleep(3)
        self._sessions.pop(session_id, None)

    async def check_login_status(self, session_id):
        import time
        session = self._sessions.get(session_id)
        if not session:
            return {"status": "not_found"}
        if time.time() > session["expires_at"]:
            try:
                await session["ctx"].close()
            except:
                pass
            self._sessions.pop(session_id, None)
            return {"status": "expired"}
        if session["logged_in"]:
            try:
                await session["ctx"].close()
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
                url = url.split(m2.group(1))[0]
        return {"url": url, "code": code}

    async def transfer(self, link: str) -> Dict[str, Any]:
        ctx = await manager.new_persistent_context(BAIDU_USER_DATA_DIR)
        page = await ctx.new_page()
        try:
            info = self._extract(link)
            url = (info["url"] or "").strip().strip('`"')
            print("[baidu] open home")
            await page.goto("https://pan.baidu.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(1000)
            need_login = await page.query_selector("text=去登录") is not None
            print(f"[baidu] login required: {need_login}")
            if need_login:
                return {
                    "status": "fail",
                    "provider": self.name,
                    "share_link": url,
                    "message": "未登录，请先扫码登录后再转存",
                }
            if not url:
                print("[baidu] invalid share url")
                return {
                    "status": "fail",
                    "provider": self.name,
                    "share_link": url,
                    "message": "分享链接无效",
                }
            print(f"[baidu] open share: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=40000)
            await page.wait_for_timeout(1000)
            try:
                need_pwd = page.get_by_text("提取码", exact=False)
                cnt = await need_pwd.count()
                print(f"[baidu] need code: {cnt}")
                if cnt:
                    code = info.get("code")
                    if not code:
                        print("[baidu] missing code")
                        return {
                            "status": "fail",
                            "provider": self.name,
                            "share_link": url,
                            "message": "缺少提取码",
                        }
                    inp = await page.query_selector("input[name*=pwd], input[aria-label*=提取码], input[type='text']")
                    if inp:
                        try:
                            await inp.fill(code)
                            print(f"[baidu] code filled: {code}")
                        except Exception:
                            pass
                    btn = page.get_by_text("提取文件", exact=False)
                    btn_cnt = await btn.count()
                    print(f"[baidu] click 提取文件: {btn_cnt}")
                    if btn_cnt:
                        try:
                            await btn.first.click()
                        except Exception:
                            pass
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
            except Exception:
                pass

            try:
                print("[baidu] wait 保存到网盘")
                await page.wait_for_selector("text=保存到网盘", timeout=30000)
            except Exception:
                await page.wait_for_load_state("networkidle", timeout=30000)

            if BAIDU_TARGET_FOLDER:
                print("[baidu] select save path panel")
                btn_path = await page.query_selector('div[class*="bottom-save-path"]') or await page.query_selector('div[class*="save-path"]')
                if btn_path:
                    try:
                        await btn_path.click()
                        print("[baidu] save path panel opened")
                    except Exception:
                        pass
                try:
                    await page.wait_for_selector("div[class*='file-tree-container'], div[class*='file-tree']", timeout=30000)
                except Exception:
                    pass

                print(f"[baidu] locate folder: {BAIDU_NODE_PATH}")
                folder = await page.query_selector(f'[node-path="{BAIDU_NODE_PATH}"]')
                if folder is None:
                    loc = page.get_by_text(BAIDU_TARGET_FOLDER, exact=False)
                    if await loc.count():
                        folder = loc.first
                if folder is not None:
                    try:
                        await folder.click()
                        print("[baidu] folder selected")
                    except Exception:
                        pass
                await page.wait_for_timeout(500)
                confirm = await page.query_selector('[node-type="confirm"]')
                if confirm is None:
                    loc = page.get_by_text("确认", exact=False)
                    if await loc.count():
                        confirm = loc.first
                if confirm is not None:
                    try:
                        await confirm.click()
                        print("[baidu] confirm path")
                    except Exception:
                        pass
                await page.wait_for_timeout(800)

            save_btn = page.get_by_text("保存到网盘", exact=False)
            save_cnt = await save_btn.count()
            print(f"[baidu] click 保存到网盘: {save_cnt}")
            if save_cnt:
                try:
                    await save_btn.first.click()
                except Exception:
                    pass
            else:
                alt = page.locator("text=保存")
                alt_cnt = await alt.count()
                print(f"[baidu] click 保存: {alt_cnt}")
                if alt_cnt:
                    try:
                        await alt.first.click()
                    except Exception:
                        pass
            await page.wait_for_timeout(1000)

            print("[baidu] transfer success")
            return {
                "status": "success",
                "provider": self.name,
                "share_link": url,
                "target_path": None,
                "message": "transferred",
            }
        except Exception as e:
            print(f"[baidu] transfer failed: {e}")
        finally:
            await ctx.close()
