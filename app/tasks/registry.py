from typing import Optional, Dict
from ..base import TaskAdapter
from .demo import DemoAdapter
from .juejin_signin import JuejinSigninAdapter
from .v2ex_signin import V2exSigninAdapter
from .ptfans_signin import PtfansSigninAdapter
from ..logger import create_logger

logger = create_logger("task-registry")

_TASK_REGISTRY: Dict[str, TaskAdapter] = {
    "demo": DemoAdapter(),
    "juejin_signin": JuejinSigninAdapter(),
    "v2ex_signin": V2exSigninAdapter(),
    "ptfans_signin": PtfansSigninAdapter(),
}

def resolve_task_adapter(name: str) -> Optional[TaskAdapter]:
    logger.info(f"Resolving task adapter: {name}")
    adapter = _TASK_REGISTRY.get((name or "").lower())
    if adapter is None:
        logger.warning(f"No task adapter found for: {name}")
    else:
        logger.info(f"Task adapter found: {name}")
    return adapter