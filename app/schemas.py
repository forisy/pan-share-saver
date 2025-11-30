from pydantic import BaseModel, ConfigDict
from typing import Optional

class TransferLink(BaseModel):
    url: Optional[str] = None
    model_config = ConfigDict(extra='ignore')

class TransferResult(BaseModel):
    status: str
    provider: str
    share_link: str
    message: Optional[str] = None
    target_path: Optional[str] = None