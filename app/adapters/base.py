from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class ShareAdapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def transfer(self, link: str) -> Dict[str, Any]:
        ...