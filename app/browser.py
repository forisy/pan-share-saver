import os
from playwright.async_api import async_playwright
from .config import HEADLESS
from .logger import create_logger

class BrowserManager:
    def __init__(self) -> None:
        self._playwright = None
        self._contexts = {}
        self.logger = create_logger("browser")

    def _cleanup_profile_locks(self, base_dir: str):
        try:
            targets = {"SingletonLock", "SingletonCookie", "SingletonSocket", "DevToolsActivePort", "LOCK"}
            for root, _, files in os.walk(base_dir):
                for fname in list(files):
                    if fname in targets:
                        fpath = os.path.join(root, fname)
                        try:
                            os.remove(fpath)
                            self.logger.debug(f"Removed profile lock file: {fpath}")
                        except Exception:
                            pass
        except Exception:
            pass

    async def start(self) -> None:
        if self._playwright is None:
            self.logger.info("Starting playwright")
            self._playwright = await async_playwright().start()
            self.logger.info("Playwright started successfully")

    async def stop(self) -> None:
        self.logger.info("Stopping browser manager")
        if self._playwright is not None:
            try:
                for bdir, ctx in list(self._contexts.items()):
                    try:
                        await ctx.close()
                        self.logger.info(f"Closed browser context: {bdir}")
                    except Exception as e:
                        self.logger.error(f"Failed to close context {bdir}: {e}")
                    self._contexts.pop(bdir, None)
            except Exception as e:
                self.logger.error(f"Error during context cleanup: {e}")
            await self._playwright.stop()
            self._playwright = None
            self.logger.info("Playwright stopped")
        self.logger.info("Browser manager stopped")

    async def new_persistent_context(self, user_data_dir: str):
        base_dir = os.path.abspath(user_data_dir)
        self.logger.debug(f"Creating new persistent context for: {base_dir}")
        if base_dir and not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
            self.logger.debug(f"Created directory: {base_dir}")
        ctx = self._contexts.get(base_dir)
        if ctx is not None:
            self.logger.debug(f"Returning existing context: {base_dir}")
            return ctx
        self._cleanup_profile_locks(base_dir)
        self.logger.debug(f"Cleaned up profile locks for: {base_dir}")

        await self.start()
        ctx = await self._playwright.chromium.launch_persistent_context(user_data_dir=base_dir, headless=HEADLESS, args=["--no-default-browser-check", "--no-first-run"])
        self._contexts[base_dir] = ctx
        self.logger.info(f"Created new persistent context: {base_dir}")
        return ctx

    async def close_context(self, user_data_dir: str):
        base_dir = os.path.abspath(user_data_dir)
        self.logger.debug(f"Closing context: {base_dir}")
        ctx = self._contexts.get(base_dir)
        if ctx is not None:
            try:
                await ctx.close()
                self.logger.info(f"Context closed: {base_dir}")
            except Exception as e:
                self.logger.error(f"Failed to close context {base_dir}: {e}")
            self._contexts.pop(base_dir, None)
        else:
            self.logger.warning(f"Context not found for: {base_dir}")
        self._cleanup_profile_locks(base_dir)
        self.logger.debug(f"Cleaned up profile locks for: {base_dir}")

manager = BrowserManager()