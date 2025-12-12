from datetime import datetime, timedelta
import random
import os
import json
from typing import Optional, Dict, Any, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo
from .registry import resolve_task_adapter
from ..config import STORAGE_DIR
from ..logger import create_logger

class TaskScheduler:
    def __init__(self) -> None:
        tzname = os.getenv("TZ", "Asia/Shanghai")
        self._scheduler = AsyncIOScheduler(timezone=ZoneInfo(tzname))
        self._started = False
        self._loaded_jobs: List[str] = []
        self.logger = create_logger("scheduler")

    def start(self) -> None:
        if not self._started:
            self.logger.info("Starting task scheduler")
            self._scheduler.start()
            self._started = True
            self.logger.info("Task scheduler started successfully")
        else:
            self.logger.info("Task scheduler already started")

    def clear_loaded_jobs(self) -> None:
        if not self._started:
            self.start()
        self.logger.info(f"Clearing {len(self._loaded_jobs)} loaded jobs")
        try:
            for jid in list(self._loaded_jobs):
                try:
                    self._scheduler.remove_job(jid)
                    self.logger.info(f"Removed job: {jid}")
                except Exception as e:
                    self.logger.error(f"Failed to remove job {jid}: {e}")
        finally:
            self._loaded_jobs.clear()
            self.logger.info("All loaded jobs cleared")

    async def _run_task(self, adapter_name: str, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        self.logger.info(f"Running task: {adapter_name}, provider: {provider}, accounts: {len(accounts) if accounts else 0}")
        adapter = resolve_task_adapter(adapter_name)
        if adapter is None:
            self.logger.error(f"Adapter not found: {adapter_name}")
            return {"status": "error", "message": "adapter_not_found", "adapter": adapter_name}
        try:
            result = await adapter.run(provider, accounts)
            self.logger.info(f"Task completed: {adapter_name}, result: {result.get('status', 'unknown')}")
            return result
        except Exception as e:
            self.logger.error(f"Task failed: {adapter_name}, error: {e}")
            return {"status": "error", "message": str(e), "adapter": adapter_name}

    async def run_now(self, adapter_name: str, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        self.logger.info(f"Running task immediately: {adapter_name}")
        return await self._run_task(adapter_name, provider, accounts)

    def schedule_at(self, adapter_name: str, run_at: datetime, job_id: Optional[str] = None, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        if not self._started:
            self.start()
        job_id = job_id or f"task:{adapter_name}:{run_at.timestamp()}"
        self.logger.info(f"Scheduling task '{adapter_name}' at {run_at} with job_id: {job_id}")
        job = self._scheduler.add_job(self._run_task, "date", run_date=run_at, args=[adapter_name, provider, accounts], id=job_id)
        self._loaded_jobs.append(job_id)
        return {"job_id": job.id, "adapter": adapter_name, "scheduled_at": run_at.isoformat(), "status": "scheduled"}

    def schedule_between(self, adapter_name: str, start_at: datetime, end_at: datetime, job_id: Optional[str] = None, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        if not self._started:
            self.start()
        if end_at <= start_at:
            self.logger.error("end_at must be after start_at")
            raise ValueError("end_at must be after start_at")
        delta_seconds = int((end_at - start_at).total_seconds())
        offset = random.randint(0, delta_seconds)
        run_at = start_at + timedelta(seconds=offset)
        job_id = job_id or f"task:{adapter_name}:{run_at.timestamp()}"
        self.logger.info(f"Scheduling task '{adapter_name}' between {start_at} and {end_at}, will run at {run_at} with job_id: {job_id}")
        job = self._scheduler.add_job(self._run_task, "date", run_date=run_at, args=[adapter_name, provider, accounts], id=job_id)
        self._loaded_jobs.append(job_id)
        return {"job_id": job.id, "adapter": adapter_name, "scheduled_at": run_at.isoformat(), "status": "scheduled"}

    def schedule_window(self, adapter_name: str, base_at: datetime, window_minutes: int, job_id: Optional[str] = None, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        if not self._started:
            self.start()
        if window_minutes < 0:
            self.logger.error("window_minutes must be non-negative")
            raise ValueError("window_minutes must be non-negative")
        offset_min = random.randint(0, window_minutes)
        run_at = base_at + timedelta(minutes=offset_min)
        job_id = job_id or f"task:{adapter_name}:{run_at.timestamp()}"
        self.logger.info(f"Scheduling task '{adapter_name}' with window {window_minutes} min around {base_at}, will run at {run_at} with job_id: {job_id}")
        job = self._scheduler.add_job(self._run_task, "date", run_date=run_at, args=[adapter_name, provider, accounts], id=job_id)
        self._loaded_jobs.append(job_id)
        return {"job_id": job.id, "adapter": adapter_name, "scheduled_at": run_at.isoformat(), "status": "scheduled"}

    def schedule_cron(self, adapter_name: str, cron_fields: Dict[str, Any], job_id: Optional[str] = None, provider: Optional[str] = None, accounts: Optional[List[str]] = None) -> Dict[str, Any]:
        if not self._started:
            self.start()
        job_id = job_id or f"task:{adapter_name}:cron:{len(self._loaded_jobs)+1}"
        self.logger.info(f"Scheduling task '{adapter_name}' with cron {cron_fields} and job_id: {job_id}")
        job = self._scheduler.add_job(self._run_task, "cron", id=job_id, args=[adapter_name, provider, accounts], **cron_fields)
        self._loaded_jobs.append(job_id)
        return {"job_id": job.id, "adapter": adapter_name, "scheduled_at": "cron", "status": "scheduled"}

    def load_from_config(self, config_file_path: Optional[str] = None) -> Dict[str, Any]:
        if not self._started:
            self.start()
        self.logger.info(f"Loading tasks from config, config_file_path: {config_file_path}")
        result: Dict[str, Any] = {"status": "ok", "loaded": []}
        path_candidates: List[str] = []
        if config_file_path:
            path_candidates.append(config_file_path)
        # default location inside repository
        path_candidates.append(os.path.join(os.path.dirname(__file__), "..", "config", "tasks.json"))
        # optional storage override
        path_candidates.append(os.path.join(STORAGE_DIR, "config", "tasks.json"))
        cfg_path = next((p for p in path_candidates if os.path.exists(p)), None)
        if not cfg_path:
            self.logger.warning(f"No tasks.json found, searched: {path_candidates}")
            return {"status": "not_found", "message": "no tasks.json found", "searched": path_candidates}
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load config from {cfg_path}: {e}")
            return {"status": "error", "message": f"load_failed: {e}"}
        
        self.logger.info(f"Loading tasks from config file: {cfg_path}")
        tasks = data if isinstance(data, list) else data.get("tasks", [])
        self.logger.info(f"Found {len(tasks)} task(s) in config")
        
        for item in tasks:
            name = (item.get("name") or item.get("id") or '').strip() or None
            entry = (item.get("entry") or item.get("adapter") or '').strip()
            provider = (item.get("provider") or item.get("provider_name") or '').strip() or None
            accounts = item.get("accounts") if isinstance(item.get("accounts"), list) else None
            sched = item.get("schedule") or {}
            if not entry:
                self.logger.warning("Task entry is empty, skipping")
                continue
            job_id = name or f"task:{entry}:{len(self._loaded_jobs)+1}"
            stype = (sched.get("type") or sched.get("kind") or "cron").lower()
            try:
                if stype == "date":
                    run_at_str = sched.get("run_at") or sched.get("at")
                    if not run_at_str:
                        self.logger.warning(f"Missing run_at for date task: {entry}")
                        continue
                    run_at = datetime.fromisoformat(run_at_str)
                    self.logger.info(f"Scheduling date task '{entry}' at {run_at}")
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
                            self.logger.warning(f"Invalid crontab format for task {entry}, expected 5 parts, got {len(parts)}")
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
                        self.logger.warning(f"No valid cron fields found for task: {entry}")
                        continue
                    self.logger.info(f"Scheduling cron task '{entry}' with fields: {fields}")
                    self.schedule_cron(entry, fields, job_id=job_id, provider=provider, accounts=accounts)
                elif stype == "window":
                    base_str = sched.get("base_at") or sched.get("at")
                    minutes = int(sched.get("window_minutes") or sched.get("window") or 0)
                    if not base_str:
                        self.logger.warning(f"Missing base_at for window task: {entry}")
                        continue
                    base_at = datetime.fromisoformat(base_str)
                    self.logger.info(f"Scheduling window task '{entry}' at {base_at} with window {minutes} minutes")
                    self.schedule_window(entry, base_at, minutes, job_id=job_id, provider=provider, accounts=accounts)
                elif stype == "between":
                    start_str = sched.get("start_at") or sched.get("start")
                    end_str = sched.get("end_at") or sched.get("end")
                    if not start_str or not end_str:
                        self.logger.warning(f"Missing start_at or end_at for between task: {entry}")
                        continue
                    start_at = datetime.fromisoformat(start_str)
                    end_at = datetime.fromisoformat(end_str)
                    self.logger.info(f"Scheduling between task '{entry}' from {start_at} to {end_at}")
                    self.schedule_between(entry, start_at, end_at, job_id=job_id, provider=provider, accounts=accounts)
                else:
                    self.logger.warning(f"Unknown schedule type '{stype}' for task: {entry}")
                    continue
                result["loaded"].append({"job_id": job_id, "entry": entry, "type": stype, "provider": provider, "accounts": accounts})
            except Exception as e:
                self.logger.error(f"Failed to schedule task {entry}: {e}")
                continue
        self.logger.info(f"Config loaded successfully, {len(result['loaded'])} tasks scheduled")
        return result

    def reload_from_config(self, config_file_path: Optional[str] = None) -> Dict[str, Any]:
        self.logger.info(f"Reloading tasks from config: {config_file_path}")
        self.clear_loaded_jobs()
        # if config not found, simply return empty loaded list
        try:
            result = self.load_from_config(config_file_path)
            self.logger.info(f"Config reloaded successfully, status: {result.get('status')}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to reload config: {e}")
            return {"status": "error", "message": "reload_failed"}

task_scheduler = TaskScheduler()

