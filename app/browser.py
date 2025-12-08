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

    def new_persistent_context(self, user_data_dir: str):
        self.start()
        base_dir = os.path.abspath(user_data_dir)
        print(f"Launching persistent context with user data dir: {base_dir}")
        if base_dir and not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
        return self._playwright.chromium.launch_persistent_context(user_data_dir=base_dir, headless=HEADLESS)

manager = BrowserManager()
