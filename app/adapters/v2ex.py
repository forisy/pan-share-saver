import os
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
from ..config import HEADLESS, ALIYUN_NODE_PATH, ALIYUN_TARGET_FOLDER, V2EX_USER_DATA_DIR
from ..browser import manager
from ..base import ShareAdapter
from ..logger import create_logger

class V2exAdapter(ShareAdapter):
    def __init__(self):
        super().__init__()
        self._sessions = {}
        self.user_data_dir = V2EX_USER_DATA_DIR
        self.logger = create_logger("v2ex")

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
            self.logger.info("Opening V2EX daily mission page")
            await page.goto("https://www.v2ex.com/mission/daily", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(3)
            btn = await page.query_selector("text=每日登录奖励")
            islogin = btn is not None
            png_bytes = b""
            if not islogin:
                locator = page.locator(
                    "div[id*='Main']"
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
        import asyncio, time
        session = self._sessions.get(session_id)
        if not session:
            self.logger.warning(f"Session {session_id} not found for login polling")
            return
        page = session["page"]
        self.logger.info(f"Starting login polling for session: {session_id}")
        for i in range(60):
            try:
                btn = await page.query_selector("text=每日登录奖励")
                if btn is not None:
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
        return "v2ex"

    async def transfer(self, link: str, account: Optional[str] = None) -> Dict[str, Any]:
        # Transfer functionality not implemented for V2EX
        self.logger.warning("Transfer method called but not implemented for V2EX")
        pass