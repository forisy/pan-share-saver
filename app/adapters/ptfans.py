import os
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
from ..config import HEADLESS, ALIYUN_NODE_PATH, ALIYUN_TARGET_FOLDER, PTFANS_USER_DATA_DIR
from ..browser import manager
from ..base import ShareAdapter

class PtfansAdapter(ShareAdapter):
    def __init__(self):
        super().__init__()
        self._sessions = {}
        self.user_data_dir = PTFANS_USER_DATA_DIR 

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
            await page.goto("https://ptfans.cc/attendance.php", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(3)
            btn = await page.query_selector("text=欢迎回来")
            islogin = btn is not None
            png_bytes = b""
            if not islogin:
                locator = page.locator(
                    "form[id*='login-form']"
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
            return session_id, png_bytes, islogin
        except Exception as e:
            print(f"get_qr_code error: {e}")
            return str(uuid.uuid4()), b"", False

    async def poll_login_status(self, session_id):
        import asyncio, time
        session = self._sessions.get(session_id)
        if not session:
            return
        page = session["page"]
        for _ in range(60):
            try:
                btn = await page.query_selector("text=欢迎回来")
                if btn is not None:
                    session["logged_in"] = True
                    try:
                        await manager.close_context(session.get("user_data_dir") or ud)
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            await asyncio.sleep(3)
        self._sessions.pop(session_id, None)

    @property
    def name(self) -> str:
        return "ptfans"
    
    async def transfer(self, link: str, account: Optional[str] = None) -> Dict[str, Any]:
        pass
