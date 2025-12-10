from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import os
from .browser import manager

class ShareAdapter(ABC):
    def __init__(self) -> None:
        self.user_data_dir: Optional[str] = None

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def transfer(self, link: str, account: Optional[str] = None) -> Dict[str, Any]:
        ...

    def _sanitize(self, s: str) -> str:
        return ''.join(c if c.isalnum() or c in ('_', '-') else '_' for c in s)[:64]

    def _resolve_user_data_dir(self, account: Optional[str] = None) -> str:
        if not self.user_data_dir:
            raise ValueError("user_data_dir_not_set")
        base = self.user_data_dir
        if account:
            base = os.path.join(base, self._sanitize(account))
        else:
            base = os.path.join(base, "default")
        os.makedirs(base, exist_ok=True)
        return base

    async def open_context_and_page(self, account: Optional[str] = None):
        ud = self._resolve_user_data_dir(account)
        ctx = await manager.new_persistent_context(ud)
        try:
            page = await ctx.new_page()
        except Exception:
            await manager.close_context(ud)
            ctx = await manager.new_persistent_context(ud)
            page = await ctx.new_page()
        return ctx, page

class TaskAdapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def run(self, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        ...
