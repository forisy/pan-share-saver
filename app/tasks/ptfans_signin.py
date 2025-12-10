from typing import Optional, Dict, Any, List
from ..base import TaskAdapter
from ..adapters.registry import resolve_adapter_from_provider

class PtfansSigninAdapter(TaskAdapter):
    @property
    def name(self) -> str:
        return "ptfans_signin"
    
    async def run(self, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        if not provider:
            return {
                "status": "success",
                "providers": ["ptfans"],
            }
        p = provider.lower()
        adapter = resolve_adapter_from_provider(p)
        if not adapter:
            return {"status": "error", "message": "unknown_provider", "provider": provider}

        import asyncio
        ctx, page = await adapter.open_context_and_page(accounts[0] if accounts else None)
        await page.goto("https://ptfans.cc/attendance.php", wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(3)

        ant = page.get_by_text("该页面必须在登录后才能访问", exact=False)
        if await ant.count() > 0:
            return {"status": "error", "message": "需要登陆"}
        
        print('已签到')

        await asyncio.sleep(3)

        await ctx.close()
            
        return {"status": "success"}
