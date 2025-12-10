from typing import Optional, Dict
from ..base import TaskAdapter
from .demo import DemoAdapter
from .juejin_signin import JuejinSigninAdapter
from .v2ex_signin import V2exSigninAdapter
from .ptfans_signin import PtfansSigninAdapter

_TASK_REGISTRY: Dict[str, TaskAdapter] = {
    "demo": DemoAdapter(),
    "juejin_signin": JuejinSigninAdapter(),
    "v2ex_signin": V2exSigninAdapter(),
    "ptfans_signin": PtfansSigninAdapter(),
}

def resolve_task_adapter(name: str) -> Optional[TaskAdapter]:
    return _TASK_REGISTRY.get((name or "").lower())

