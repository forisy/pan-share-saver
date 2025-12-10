import os
from playwright.async_api import async_playwright
from .config import HEADLESS

class BrowserManager:
    def __init__(self) -> None:
        self._playwright = None
        self._contexts = {}

    def _cleanup_profile_locks(self, base_dir: str):
        try:
            targets = {"SingletonLock", "SingletonCookie", "SingletonSocket", "DevToolsActivePort", "LOCK"}
            for root, _, files in os.walk(base_dir):
                for fname in list(files):
                    if fname in targets:
                        fpath = os.path.join(root, fname)
                        try:
                            os.remove(fpath)
                        except Exception:
                            pass
        except Exception:
            pass

    async def start(self) -> None:
        if self._playwright is None:
            self._playwright = await async_playwright().start()

    async def stop(self) -> None:
        if self._playwright is not None:
            try:
                for bdir, ctx in list(self._contexts.items()):
                    try:
                        await ctx.close()
                    except Exception:
                        pass
                    self._contexts.pop(bdir, None)
            except Exception:
                pass
            await self._playwright.stop()
            self._playwright = None

    async def new_persistent_context(self, user_data_dir: str):
        base_dir = os.path.abspath(user_data_dir)
        if base_dir and not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
        ctx = self._contexts.get(base_dir)
        if ctx is not None:
            return ctx
        self._cleanup_profile_locks(base_dir)
        
        await self.start()
        ctx = await self._playwright.chromium.launch_persistent_context(user_data_dir=base_dir, headless=HEADLESS, args=["--no-default-browser-check", "--no-first-run"])
        self._contexts[base_dir] = ctx
        return ctx

    async def close_context(self, user_data_dir: str):
        base_dir = os.path.abspath(user_data_dir)
        ctx = self._contexts.get(base_dir)
        if ctx is not None:
            try:
                await ctx.close()
            except Exception:
                pass
            self._contexts.pop(base_dir, None)
        self._cleanup_profile_locks(base_dir)

manager = BrowserManager()
