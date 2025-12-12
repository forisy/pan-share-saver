from typing import Optional, Dict, Any, List
from ..base import TaskAdapter
from ..adapters.registry import resolve_adapter_from_provider
from ..logger import create_logger

class DemoAdapter(TaskAdapter):
    @property
    def name(self) -> str:
        return "demo"

    async def run(self, provider: Optional[str] = None, accounts: Optional[List[str]] = None, cookies: Optional[Any] = None) -> Dict[str, Any]:
        logger = create_logger("demo")
        logger.info(f"Starting demo task, provider: {provider}, accounts: {len(accounts) if accounts else 0}")

        if not provider:
            logger.info("No provider specified, returning available providers")
            return {
                "status": "success",
                "providers": ["baidu", "alipan"],
            }
        p = provider.lower()
        adapter = resolve_adapter_from_provider(p)
        if not adapter:
            logger.error(f"Unknown provider: {provider}")
            return {"status": "error", "message": "unknown_provider", "provider": provider}
        logger.info(f"Opening context and page for provider: {p}")
        ctx, page = await adapter.open_context_and_page(cookie_str=cookies)
        logger.info("Demo task completed successfully")
        return {"status": "success"}