from typing import Optional, Dict, Any, List
from ..base import TaskAdapter
from ..adapters.registry import resolve_adapter_from_provider

class JuejinSigninAdapter(TaskAdapter):
    @property
    def name(self) -> str:
        return "juejin_signin"
    
    async def run(self, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        if not provider:
            return {
                "status": "success",
                "providers": ["juejin"],
            }
        p = provider.lower()
        adapter = resolve_adapter_from_provider(p)
        if not adapter:
            return {"status": "error", "message": "unknown_provider", "provider": provider}

        import asyncio
        ctx, page = await adapter.open_context_and_page(accounts[0] if accounts else None)
        await page.goto("https://juejin.cn/user/center/signin?from=main_page", wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(3)

        ant = page.get_by_text("连续签到天数")
        if await ant.count() == 0:
            return {"status": "error", "message": "需要登陆"}
        
        await page.wait_for_selector("text=每日签到", state="visible")
        signin = page.locator("button[class*='signin']", has_text="立即签到")
        if await signin.count() > 0:
            await signin.click()
            await page.get_by_text("签到成功").wait_for(state="visible")
            print('签到成功')
        else:
            print('已签到')

        await page.goto("https://juejin.cn/user/center/lottery?from=sign_in_success", wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(3)
        await page.wait_for_selector("div[class*='text-free']", state="visible")
        lottery = page.locator("div[class*='text-free']")
        if await lottery.count() > 0:
            await lottery.first.click()
            print('抽奖成功')
        else:
            print('已抽奖')
        await asyncio.sleep(5)

        await ctx.close()
            
        return {"status": "success"}
