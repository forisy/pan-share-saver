from typing import Optional, Dict, Any, List
from ..base import TaskAdapter
from ..adapters.registry import resolve_adapter_from_provider
from ..logger import create_logger

class V2exSigninAdapter(TaskAdapter):
    @property
    def name(self) -> str:
        return "v2ex_signin"

    async def run(self, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        logger = create_logger("v2ex_signin")
        logger.info(f"Starting V2EX signin task, provider: {provider}, accounts: {len(accounts) if accounts else 0}")
        
        if not provider:
            logger.info("No provider specified, returning available providers")
            return {
                "status": "success",
                "providers": ["v2ex"],
            }
        p = provider.lower()
        adapter = resolve_adapter_from_provider(p)
        if not adapter:
            logger.error(f"Unknown provider: {provider}")
            return {"status": "error", "message": "unknown_provider", "provider": provider}

        import asyncio
        ctx, page = await adapter.open_context_and_page(accounts[0] if accounts else None)
        logger.info("Navigating to V2EX daily mission page")
        await page.goto("https://www.v2ex.com/mission/daily", wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(3)

        ant = page.get_by_text("需要先登录", exact=False)
        if await ant.count() > 0:
            logger.warning("Login required for V2EX signin")
            return {"status": "error", "message": "需要登陆"}

        await page.wait_for_selector("text=领取", state="visible")
        signin = page.locator("input[type='button']", has_text="领取")
        if await signin.count() > 0:
            await signin.click()
            logger.info('V2EX签到成功')
        else:
            logger.info('V2EX已签到')
            
        await asyncio.sleep(3)
        await ctx.close()
        logger.info("V2EX signin task completed")

        return {"status": "success"}