import os
from typing import Union, Dict, List
from playwright.async_api import async_playwright
from .config import HEADLESS
from .logger import create_logger
from .utils.cookies import parse_cookie_string

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

    async def new_persistent_context(self, user_data_dir: str, cookie_str: Union[str, Dict, List] = None):
        """
        Creates a new persistent browser context, optionally with cookies from a string, dict, or list.
        
        Args:
            user_data_dir: Path to the user data directory
            cookie_str: Optional cookie data to set in the context (string, dict, or list)
        """
        base_dir = os.path.abspath(user_data_dir)
        self.logger.debug(f"Creating new persistent context for: {base_dir}")
        if base_dir and not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
            self.logger.debug(f"Created directory: {base_dir}")
        ctx = self._contexts.get(base_dir)
        if ctx is not None:
            self.logger.debug(f"Returning existing context: {base_dir}")
            # If a cookie string is provided for an existing context, set the cookies
            if cookie_str:
                await self._set_cookies_from_string(ctx, cookie_str)
            return ctx
        self._cleanup_profile_locks(base_dir)
        self.logger.debug(f"Cleaned up profile locks for: {base_dir}")

        await self.start()
        ctx = await self._playwright.chromium.launch_persistent_context(user_data_dir=base_dir, headless=HEADLESS, args=["--no-default-browser-check", "--no-first-run"])
        self._contexts[base_dir] = ctx
        self.logger.info(f"Created new persistent context: {base_dir}")
        
        # Set cookies if provided
        if cookie_str:
            await self._set_cookies_from_string(ctx, cookie_str)
        
        return ctx

    async def _set_cookies_from_string(self, context, cookie_str: str):
        """
        Sets cookies in the browser context from a cookie string.
        
        Args:
            context: The browser context to set cookies for
            cookie_str: Cookie string in format "key1=value1; key2=value2" or JSON format
        """
        try:
            cookies = parse_cookie_string(cookie_str)
            
            # Add cookies to context if any were parsed
            if cookies:
                await context.add_cookies(cookies)
                self.logger.info(f"Set {len(cookies)} cookies from string in context")
            else:
                self.logger.warning("No cookies could be parsed from the provided cookie string")
                
        except Exception as e:
            self.logger.error(f"Failed to set cookies from string: {e}")

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