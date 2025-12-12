from typing import Optional, Dict, Any, Union
import re
from urllib.parse import urlparse, parse_qs
from ..config import BAIDU_NODE_PATH, BAIDU_TARGET_FOLDER, BAIDU_USER_DATA_DIR
from ..browser import manager
from ..base import ShareAdapter
from ..logger import create_logger


class BaiduAdapter(ShareAdapter):
    def __init__(self):
        super().__init__()
        self._sessions = {}
        self.user_data_dir = BAIDU_USER_DATA_DIR
        self.logger = create_logger("baidu")

    async def get_qr_code(self, account: Optional[str] = None):
        import uuid, time, asyncio
        try:
            for sid, s in list(self._sessions.items()):
                try:
                    ud = s.get("user_data_dir")
                    if ud:
                        await manager.close_context(ud)
                    else:
                        await s.get("ctx").close()
                except Exception:
                    pass
                self._sessions.pop(sid, None)
        except Exception:
            pass
        ud = self._resolve_user_data_dir(account)
        ctx, page = await self.open_context_and_page(account)
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
                "user_data_dir": ud,
            }
            self.logger.info(f"Generated QR code session: {session_id}, login status: {islogin}")
            return session_id, png_bytes, islogin
        except Exception as e:
            self.logger.error(f"get_qr_code error: {e}")
            return str(uuid.uuid4()), b"", False

    async def poll_login_status(self, session_id):
        import asyncio
        session = self._sessions.get(session_id)
        if not session:
            self.logger.warning(f"Session {session_id} not found for login polling")
            return
        page = session["page"]
        self.logger.info(f"Starting login polling for session: {session_id}")
        for _ in range(60):
            try:
                btn = await page.query_selector("text=去登录")
                if btn is None:
                    session["logged_in"] = True
                    self.logger.info(f"Login detected for session: {session_id}")
                    try:
                        await manager.close_context(session.get("user_data_dir"))
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            await asyncio.sleep(3)
        self.logger.warning(f"Login polling timed out for session: {session_id}")
        self._sessions.pop(session_id, None)

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

    async def transfer(self, link: str, account: Optional[str] = None, cookie_str: Optional[Any] = None) -> Dict[str, Any]:
        self.logger.info(f"Starting transfer for link: {link[:50]}..." if len(link) > 50 else f"Starting transfer for link: {link}")
        ctx, page = await self.open_context_and_page(account, cookie_str=cookie_str)
        try:
            info = self._extract(link)
            url = (info["url"] or "").strip().strip('`"')
            self.logger.info("Opening home page")
            await page.goto("https://pan.baidu.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(1000)
            need_login = await page.query_selector("text=去登录") is not None
            self.logger.info(f"Login required: {need_login}")
            if need_login:
                self.logger.warning("User not logged in, transfer cancelled")
                return {
                    "status": "fail",
                    "provider": self.name,
                    "share_link": url,
                    "message": "未登录，请先扫码登录后再转存",
                }
            if not url:
                self.logger.error("Invalid share URL")
                return {
                    "status": "fail",
                    "provider": self.name,
                    "share_link": url,
                    "message": "分享链接无效",
                }
            self.logger.info(f"Opening share page: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=40000)
            await page.wait_for_timeout(1000)
            try:
                need_pwd = page.get_by_text("提取码", exact=False)
                cnt = await need_pwd.count()
                self.logger.info(f"Need password check: {cnt}")
                if cnt:
                    code = info.get("code")
                    if not code:
                        self.logger.error("Missing code for password-protected share")
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
                            self.logger.info(f"Code filled: {code}")
                        except Exception:
                            pass
                    btn = page.get_by_text("提取文件", exact=False)
                    btn_cnt = await btn.count()
                    self.logger.info(f"Clicking '提取文件': {btn_cnt}")
                    if btn_cnt:
                        try:
                            await btn.first.click()
                        except Exception:
                            pass
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
            except Exception as e:
                self.logger.warning(f"Error during password handling: {e}")
                pass

            try:
                self.logger.info("Waiting for '保存到网盘' button")
                await page.wait_for_selector("text=保存到网盘", timeout=30000)
            except Exception:
                self.logger.info("Falling back to network idle wait")
                await page.wait_for_load_state("networkidle", timeout=30000)

            if BAIDU_TARGET_FOLDER:
                self.logger.info("Selecting save path panel")
                btn_path = await page.query_selector('div[class*="bottom-save-path"]') or await page.query_selector('div[class*="save-path"]')
                if btn_path:
                    try:
                        await btn_path.click()
                        self.logger.info("Save path panel opened")
                    except Exception:
                        self.logger.warning("Failed to open save path panel")
                try:
                    await page.wait_for_selector("div[class*='file-tree-container'], div[class*='file-tree']", timeout=30000)
                except Exception:
                    pass

                self.logger.info(f"Locating folder: {BAIDU_NODE_PATH}")
                folder = await page.query_selector(f'[node-path="{BAIDU_NODE_PATH}"]')
                if folder is None:
                    loc = page.get_by_text(BAIDU_TARGET_FOLDER, exact=False)
                    if await loc.count():
                        folder = loc.first
                if folder is not None:
                    try:
                        await folder.click()
                        self.logger.info("Folder selected")
                    except Exception:
                        self.logger.warning("Failed to select folder")
                await page.wait_for_timeout(500)
                confirm = await page.query_selector('[node-type="confirm"]')
                if confirm is None:
                    loc = page.get_by_text("确认", exact=False)
                    if await loc.count():
                        confirm = loc.first
                if confirm is not None:
                    try:
                        await confirm.click()
                        self.logger.info("Path confirmed")
                    except Exception:
                        self.logger.warning("Failed to confirm path")
                await page.wait_for_timeout(800)

            save_btn = page.get_by_text("保存到网盘", exact=False)
            save_cnt = await save_btn.count()
            self.logger.info(f"Clicking '保存到网盘': {save_cnt}")
            if save_cnt:
                try:
                    await save_btn.first.click()
                except Exception:
                    self.logger.warning("Failed to click '保存到网盘'")
            else:
                alt = page.locator("text=保存")
                alt_cnt = await alt.count()
                self.logger.info(f"Clicking '保存': {alt_cnt}")
                if alt_cnt:
                    try:
                        await alt.first.click()
                    except Exception:
                        self.logger.warning("Failed to click '保存'")
            await page.wait_for_timeout(1000)

            self.logger.info("Transfer completed successfully")
            return {
                "status": "success",
                "provider": self.name,
                "share_link": url,
                "target_path": None,
                "message": "transferred",
            }
        except Exception as e:
            self.logger.error(f"Transfer failed: {e}")
        finally:
            try:
                await manager.close_context(self._resolve_user_data_dir(account))
                self.logger.info(f"Browser context closed for account: {account}")
            except Exception:
                self.logger.warning("Failed to close browser context")
