import os
from typing import Optional
from playwright.sync_api import sync_playwright
from .config import HEADLESS

class BrowserManager:
    def __init__(self) -> None:
        self._playwright = None

    def start(self) -> None:
        if self._playwright is None:
            self._playwright = sync_playwright().start()

    def stop(self) -> None:
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def new_browser(self):
        self.start()
        return self._playwright.chromium.launch(headless=HEADLESS)

    def new_context(self, storage_state: Optional[str] = None):
        browser = self.new_browser()
        if storage_state and os.path.exists(storage_state):
            ctx = browser.new_context(storage_state=storage_state)
        else:
            ctx = browser.new_context()
        return ctx

manager = BrowserManager()