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
        ctx = await manager.new_persistent_context(ALIYUN_USER_DATA_DIR)
        page = await ctx.new_page()
        try:
            islogin = False
            await page.goto("https://www.alipan.com/drive/home", wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(3)
            btn = await page.query_selector("text=文件分类")
            islogin = btn is not None
            png_bytes = b""
            if not islogin:
                # try:
                #     await page.goto("https://www.alipan.com/sign/in", timeout=30000)
                # except Exception:
                #     await page.goto("https://www.aliyundrive.com/sign/in", timeout=30000)
                try:
                    btn = page.get_by_text("扫码登录", exact=False)
                    if await btn.count():
                        await btn.first.click()
                except Exception:
                    pass
                locator = page.locator(
                    "div[class*='login']"
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
        import asyncio, time
        session = self._sessions.get(session_id)
        if not session:
            return
        page = session["page"]
        for _ in range(60):
            try:
                btn = await page.query_selector("text=文件分类")
                if btn is not None:
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
            except Exception:
                pass
            self._sessions.pop(session_id, None)
            return {"status": "expired"}
        if session["logged_in"]:
            try:
                await session["ctx"].close()
            except Exception:
                pass
            self._sessions.pop(session_id, None)
            return {"status": "success"}
        return {"status": "pending"}

    @property
    def name(self) -> str:
        return "aliyun"

    def _extract(self, link: str) -> Dict[str, Optional[str]]:
        m = re.search(r'https?://[^\s\u4e00-\u9fff\uFF00-\uFFEF]+', link)
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
        ctx = await manager.new_persistent_context(ALIYUN_USER_DATA_DIR)
        page = await ctx.new_page()
        info = self._extract(link)
        url = (info["url"] or "").strip().strip('`"')
        try:
            print("[aliyun] open home")
            await page.goto("https://www.alipan.com/drive/home", timeout=30000)
            await page.wait_for_timeout(1000)
            await page.wait_for_selector("text=文件分类", timeout=30000)
            print(f"[aliyun] open share: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=40000)
            await page.wait_for_timeout(1000)
            try:
                need_pwd = page.get_by_text("分享了文件", exact=False)
                cnt = await need_pwd.count()
                print(f"[aliyun] need code: {cnt}")
                if cnt:
                    code = info.get("code")
                    if not code:
                        print("[aliyun] missing code")
                        return {
                            "status": "fail",
                            "provider": self.name,
                            "share_link": url,
                            "message": "缺少提取码",
                        }
                    inp = await page.query_selector("input[placeholder*=请输入提取码], input[type='text']")
                    if inp:
                        try:
                            await inp.fill(code)
                            print(f"[aliyun] code filled: {code}")
                        except Exception:
                            pass
                    btn = page.get_by_text("极速查看文件", exact=False)
                    btn_cnt = await btn.count()
                    print(f"[aliyun] click 极速查看文件: {btn_cnt}")
                    if btn_cnt:
                        try:
                            await btn.first.click()
                        except Exception:
                            pass
                    await page.wait_for_load_state("domcontentloaded", timeout=30000)
            except Exception:
                pass

            try:
                try:
                    btn1 = page.get_by_role("button", name="立即保存", exact=False)
                    await btn1.wait_for(state="visible", timeout=30000)
                    print("[aliyun] click 立即保存")
                    await btn1.first.click()
                except Exception:
                    try:
                        alt1 = page.get_by_text("立即保存", exact=False)
                        alt1_cnt = await alt1.count()
                        print(f"[aliyun] click 立即保存 alt: {alt1_cnt}")
                        if alt1_cnt:
                            await alt1.first.wait_for(state="visible", timeout=30000)
                            await alt1.first.click()
                        else:
                            css1 = page.locator("button:has-text('立即保存'), [class*='btn-save']")
                            css1_cnt = await css1.count()
                            print(f"[aliyun] click 立即保存 css: {css1_cnt}")
                            if css1_cnt:
                                await css1.first.wait_for(state="visible", timeout=30000)
                                await css1.first.click()
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass

            try:
                btn = page.get_by_text("保存到根目录", exact=False)
                await btn.wait_for(state="visible", timeout=30000)
                btn_root_cnt = await btn.count()
                print(f"[aliyun] click 保存到根目录: {btn_root_cnt}")
                if btn_root_cnt:
                    sbtn = page.get_by_text("来自分享", exact=False)
                    await sbtn.wait_for(state="visible", timeout=30000)
                    print("[aliyun] click 来自分享")
                    await sbtn.first.click()
            except Exception:
                pass

            try:
                btn2 = page.get_by_role("button", name="保存到此处", exact=False)
                await btn2.wait_for(state="visible", timeout=30000)
                print("[aliyun] click 保存到此处")
                await btn2.first.click()
            except Exception:
                try:
                    alt2 = page.get_by_text("保存到此处", exact=False)
                    alt2_cnt = await alt2.count()
                    print(f"[aliyun] click 保存到此处 alt: {alt2_cnt}")
                    if alt2_cnt:
                        await alt2.first.wait_for(state="visible", timeout=30000)
                        await alt2.first.click()
                    else:
                        css2 = page.locator("button:has-text('保存到此处')")
                        css2_cnt = await css2.count()
                        print(f"[aliyun] click 保存到此处 css: {css2_cnt}")
                        if css2_cnt:
                            await css2.first.wait_for(state="visible", timeout=30000)
                            await css2.first.click()
                except Exception:
                    pass

            except Exception as e:
                print(f"[aliyun] click save actions failed: {e}")

            await page.wait_for_timeout(1000)
            print("[aliyun] transfer success")
            return {
                "status": "success",
                "provider": self.name,
                "share_link": link,
                "target_path": None,
                "message": "transferred",
            }
        except Exception as e:
            print(f"[aliyun] transfer failed: {e}")
        finally:
            await ctx.close()
