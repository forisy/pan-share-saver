from typing import Optional, Dict, Any, List
from ..base import TaskAdapter
from ..adapters.registry import resolve_adapter_from_provider

class DemoAdapter(TaskAdapter):
    @property
    def name(self) -> str:
        return "demo"
    
    async def run(self, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        if not provider:
            return {
                "status": "success",
                "providers": ["baidu", "aliyun"],
            }
        p = provider.lower()
        adapter = resolve_adapter_from_provider(p)
        if not adapter:
            return {"status": "error", "message": "unknown_provider", "provider": provider}
        ctx, page = await adapter.open_context_and_page()
        return {"status": "success"}
