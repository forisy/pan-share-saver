from typing import Optional, Dict, Any, List
from ..base import TaskAdapter
from ..adapters.registry import resolve_adapter_from_provider

class V2exSigninAdapter(TaskAdapter):
    @property
    def name(self) -> str:
        return "v2ex_signin"
    
    async def run(self, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        if not provider:
            return {
                "status": "success",
                "providers": ["v2ex"],
            }
        p = provider.lower()
        adapter = resolve_adapter_from_provider(p)
        if not adapter:
            return {"status": "error", "message": "unknown_provider", "provider": provider}

        import asyncio
        ctx, page = await adapter.open_context_and_page(accounts[0] if accounts else None)
        await page.goto("https://www.v2ex.com/mission/daily", wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(3)

        ant = page.get_by_text("需要先登录", exact=False)
        if await ant.count() > 0:
            return {"status": "error", "message": "需要登陆"}
        
        await page.wait_for_selector("text=领取", state="visible")
        signin = page.locator("input[type='button']", has_text="领取")
        if await signin.count() > 0:
            await signin.click()
            print('签到成功')
        else:
            print('已签到')

        await asyncio.sleep(3)

        await ctx.close()
            
        return {"status": "success"}
