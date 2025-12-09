import os
from playwright.async_api import async_playwright
from .config import HEADLESS

class BrowserManager:
    def __init__(self) -> None:
        self._playwright = None

    async def start(self) -> None:
        if self._playwright is None:
            self._playwright = await async_playwright().start()

    async def stop(self) -> None:
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def new_persistent_context(self, user_data_dir: str):
        await self.start()
        base_dir = os.path.abspath(user_data_dir)
        if base_dir and not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
        return await self._playwright.chromium.launch_persistent_context(user_data_dir=base_dir, headless=HEADLESS)

manager = BrowserManager()
