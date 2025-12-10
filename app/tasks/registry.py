from typing import Optional, Dict
from ..base import TaskAdapter
from .demo import DemoAdapter
from .juejin_signin import JuejinSigninAdapter

_TASK_REGISTRY: Dict[str, TaskAdapter] = {
    "demo": DemoAdapter(),
    "juejin_signin": JuejinSigninAdapter(),
}

def resolve_task_adapter(name: str) -> Optional[TaskAdapter]:
    return _TASK_REGISTRY.get((name or "").lower())

