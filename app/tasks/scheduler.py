from datetime import datetime, timedelta
import random
import os
import json
from typing import Optional, Dict, Any, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo
from .registry import resolve_task_adapter
from ..config import STORAGE_DIR

class TaskScheduler:
    def __init__(self) -> None:
        tzname = os.getenv("TZ", "Asia/Shanghai")
        self._scheduler = AsyncIOScheduler(timezone=ZoneInfo(tzname))
        self._started = False
        self._loaded_jobs: List[str] = []

    def start(self) -> None:
        if not self._started:
            self._scheduler.start()
            self._started = True

    async def _run_task(self, adapter_name: str, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        adapter = resolve_task_adapter(adapter_name)
        if adapter is None:
            return {"status": "error", "message": "adapter_not_found", "adapter": adapter_name}
        try:
            return await adapter.run(provider, accounts)
        except Exception as e:
            return {"status": "error", "message": str(e), "adapter": adapter_name}

    async def run_now(self, adapter_name: str, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        return await self._run_task(adapter_name, provider, accounts)

    def schedule_at(self, adapter_name: str, run_at: datetime, job_id: Optional[str] = None, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        self.start()
        job = self._scheduler.add_job(self._run_task, "date", run_date=run_at, args=[adapter_name, provider, accounts], id=job_id)
        return {"job_id": job.id, "adapter": adapter_name, "scheduled_at": run_at.isoformat(), "status": "scheduled"}

    def schedule_between(self, adapter_name: str, start_at: datetime, end_at: datetime, job_id: Optional[str] = None, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        self.start()
        if end_at <= start_at:
            raise ValueError("end_at must be after start_at")
        delta_seconds = int((end_at - start_at).total_seconds())
        offset = random.randint(0, delta_seconds)
        run_at = start_at + timedelta(seconds=offset)
        job = self._scheduler.add_job(self._run_task, "date", run_date=run_at, args=[adapter_name, provider, accounts], id=job_id)
        return {"job_id": job.id, "adapter": adapter_name, "scheduled_at": run_at.isoformat(), "status": "scheduled"}

    def schedule_window(self, adapter_name: str, base_at: datetime, window_minutes: int, job_id: Optional[str] = None, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        self.start()
        if window_minutes < 0:
            raise ValueError("window_minutes must be non-negative")
        offset_min = random.randint(0, window_minutes)
        run_at = base_at + timedelta(minutes=offset_min)
        job = self._scheduler.add_job(self._run_task, "date", run_date=run_at, args=[adapter_name, provider, accounts], id=job_id)
        return {"job_id": job.id, "adapter": adapter_name, "scheduled_at": run_at.isoformat(), "status": "scheduled"}

    def schedule_cron(self, adapter_name: str, cron_fields: Dict[str, Any], job_id: Optional[str] = None, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        self.start()
        job = self._scheduler.add_job(self._run_task, "cron", id=job_id, args=[adapter_name, provider, accounts], **cron_fields)
        return {"job_id": job.id, "adapter": adapter_name, "scheduled_at": "cron", "status": "scheduled"}

    def load_from_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        self.start()
        result: Dict[str, Any] = {"status": "ok", "loaded": []}
        path_candidates: List[str] = []
        if config_path:
            path_candidates.append(config_path)
        # default location inside repository
        path_candidates.append(os.path.join(os.path.dirname(__file__), "tasks.json"))
        # optional storage override
        path_candidates.append(os.path.join(STORAGE_DIR, "tasks.json"))
        cfg_path = next((p for p in path_candidates if os.path.exists(p)), None)
        if not cfg_path:
            return {"status": "not_found", "message": "no tasks.json found", "searched": path_candidates}
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return {"status": "error", "message": f"load_failed: {e}"}
        tasks = data if isinstance(data, list) else data.get("tasks", [])
        for item in tasks:
            name = (item.get("name") or item.get("id") or '').strip() or None
            entry = (item.get("entry") or item.get("adapter") or '').strip()
            provider = (item.get("provider") or item.get("provider_name") or '').strip() or None
            accounts = item.get("accounts") if isinstance(item.get("accounts"), list) else None
            sched = item.get("schedule") or {}
            if not entry:
                continue
            job_id = name or f"task:{entry}:{len(self._loaded_jobs)+1}"
            stype = (sched.get("type") or sched.get("kind") or "cron").lower()
            try:
                if stype == "date":
                    run_at_str = sched.get("run_at") or sched.get("at")
                    if not run_at_str:
                        continue
                    run_at = datetime.fromisoformat(run_at_str)
                    self.schedule_at(entry, run_at, job_id=job_id, provider=provider, accounts=accounts)
                elif stype == "cron":
                    fields: Dict[str, Any] = {}
                    crontab = sched.get("crontab")
                    if crontab and isinstance(crontab, str):
                        parts = crontab.split()
                        if len(parts) == 5:
                            fields = {
                                "minute": parts[0],
                                "hour": parts[1],
                                "day": parts[2],
                                "month": parts[3],
                                "day_of_week": parts[4],
                            }
                        else:
                            continue
                    else:
                        for key in ("second", "minute", "hour", "day", "month", "day_of_week"):
                            if key in sched:
                                fields[key] = sched[key]
                        cron_obj = sched.get("fields") or {}
                        for key in ("second", "minute", "hour", "day", "month", "day_of_week"):
                            if key in cron_obj:
                                fields[key] = cron_obj[key]
                    if not fields:
                        continue
                    self.schedule_cron(entry, fields, job_id=job_id, provider=provider, accounts=accounts)
                elif stype == "window":
                    base_str = sched.get("base_at") or sched.get("at")
                    minutes = int(sched.get("window_minutes") or sched.get("window") or 0)
                    if not base_str:
                        continue
                    base_at = datetime.fromisoformat(base_str)
                    self.schedule_window(entry, base_at, minutes, job_id=job_id, provider=provider, accounts=accounts)
                elif stype == "between":
                    start_str = sched.get("start_at") or sched.get("start")
                    end_str = sched.get("end_at") or sched.get("end")
                    if not start_str or not end_str:
                        continue
                    start_at = datetime.fromisoformat(start_str)
                    end_at = datetime.fromisoformat(end_str)
                    self.schedule_between(entry, start_at, end_at, job_id=job_id, provider=provider, accounts=accounts)
                else:
                    continue
                self._loaded_jobs.append(job_id)
                result["loaded"].append({"job_id": job_id, "entry": entry, "type": stype, "provider": provider, "accounts": accounts})
            except Exception:
                continue
        return result

task_scheduler = TaskScheduler()

