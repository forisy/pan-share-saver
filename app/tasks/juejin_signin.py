from typing import Optional, Dict, Any, List
from ..base import TaskAdapter
from ..adapters.registry import resolve_adapter_from_provider
from ..logger import create_logger

class JuejinSigninAdapter(TaskAdapter):
    @property
    def name(self) -> str:
        return "juejin_signin"

    async def run(self, provider: Optional[str] = None, accounts: Optional[List[str]] = None, cookies: Optional[Any] = None) -> Dict[str, Any]:
        logger = create_logger("juejin_signin")
        logger.info(f"Starting Juejin signin task, provider: {provider}, accounts: {len(accounts) if accounts else 0}")

        if not provider:
            logger.info("No provider specified, returning available providers")
            return {
                "status": "success",
                "providers": ["juejin"],
            }
        p = provider.lower()
        adapter = resolve_adapter_from_provider(p)
        if not adapter:
            logger.error(f"Unknown provider: {provider}")
            return {"status": "error", "message": "unknown_provider", "provider": provider}

        import asyncio
        ctx, page = await adapter.open_context_and_page(accounts[0] if accounts else None, cookie_str=cookies)
        logger.info("Navigating to Juejin signin page")
        await page.goto("https://juejin.cn/user/center/signin?from=main_page", wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(3)

        ant = page.get_by_text("连续签到天数")
        if await ant.count() == 0:
            logger.warning("Login required for Juejin signin")
            return {"status": "error", "message": "需要登陆"}

        await page.wait_for_selector("text=每日签到", state="visible")
        signin = page.locator("button[class*='signin']", has_text="立即签到")
        if await signin.count() > 0:
            await signin.click()
            await page.get_by_text("签到成功").wait_for(state="visible")
            logger.info('Juejin签到成功')
        else:
            logger.info('Juejin已签到')

        logger.info("Navigating to Juejin lottery page")
        await page.goto("https://juejin.cn/user/center/lottery?from=sign_in_success", wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(3)
        await page.wait_for_selector("div[class*='text-free']", state="visible")
        lottery = page.locator("div[class*='text-free']")
        if await lottery.count() > 0:
            await lottery.first.click()
            logger.info('Juejin抽奖成功')
        else:
            logger.info('Juejin已抽奖')
        await asyncio.sleep(5)

        await ctx.close()
        logger.info("Juejin signin task completed")

        return {"status": "success"}