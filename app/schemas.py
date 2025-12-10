from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class TransferLink(BaseModel):
    url: Optional[str] = None
    account: Optional[str] = None
    model_config = ConfigDict(extra='ignore')

class TransferResult(BaseModel):
    status: str
    provider: str
    share_link: str
    message: Optional[str] = None
    target_path: Optional[str] = None

class ScheduleAtReq(BaseModel):
    adapter: str
    run_at: datetime
    provider: Optional[str] = None
    accounts: Optional[List[str]] = None


class ScheduleBetweenReq(BaseModel):
    adapter: str
    start_at: datetime
    end_at: datetime
    provider: Optional[str] = None
    accounts: Optional[List[str]] = None


class ScheduleWindowReq(BaseModel):
    adapter: str
    base_at: datetime
    window_minutes: int
    provider: Optional[str] = None
    accounts: Optional[List[str]] = None


class ScheduleResult(BaseModel):
    job_id: str
    adapter: str
    scheduled_at: datetime
    status: str
