from typing import Optional, Dict, Any, List
from ..base import TaskAdapter
from ..adapters.registry import resolve_adapter_from_provider
from ..logger import create_logger

class PtfansSigninAdapter(TaskAdapter):
    @property
    def name(self) -> str:
        return "ptfans_signin"

    async def run(self, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        logger = create_logger("ptfans_signin")
        logger.info(f"Starting Ptfans signin task, provider: {provider}, accounts: {len(accounts) if accounts else 0}")
        
        if not provider:
            logger.info("No provider specified, returning available providers")
            return {
                "status": "success",
                "providers": ["ptfans"],
            }
        p = provider.lower()
        adapter = resolve_adapter_from_provider(p)
        if not adapter:
            logger.error(f"Unknown provider: {provider}")
            return {"status": "error", "message": "unknown_provider", "provider": provider}

        import asyncio
        ctx, page = await adapter.open_context_and_page(accounts[0] if accounts else None)
        logger.info("Navigating to Ptfans attendance page")
        await page.goto("https://ptfans.cc/attendance.php", wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(3)

        ant = page.get_by_text("该页面必须在登录后才能访问", exact=False)
        if await ant.count() > 0:
            logger.warning("Login required for Ptfans signin")
            return {"status": "error", "message": "需要登陆"}

        logger.info('Ptfans已签到')

        await asyncio.sleep(3)
        await ctx.close()
        logger.info("Ptfans signin task completed")

        return {"status": "success"}