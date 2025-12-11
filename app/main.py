from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse
from .schemas import TransferLink, TransferResult, ScheduleAtReq, ScheduleBetweenReq, ScheduleWindowReq, ScheduleResult, RunTaskReq, RunTaskResult
from .tasks.scheduler import task_scheduler
from .config import TASKS_CONFIG_PATH, BAIDU_USER_DATA_DIR, ALIYUN_USER_DATA_DIR, JUEJIN_USER_DATA_DIR, V2EX_USER_DATA_DIR
from .browser import manager
from .tasks.registry import resolve_task_adapter
from .adapters.registry import resolve_adapter_from_link, resolve_adapter_from_provider

import asyncio
import os
import base64
import io
from watchfiles import awatch

# Windows Playwright 修复
if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI()

# ==============================
#       STORAGE SESSIONS
# ==============================

_LOGIN_SESSIONS = {}  # 保存二维码 session

_TRANSFER_QUEUE = asyncio.Queue()
_TRANSFER_PENDING = set()

async def _transfer_worker():
    while True:
        adapter, url = await _TRANSFER_QUEUE.get()
        try:
            try:
                await adapter.transfer(url)
            except Exception:
                pass
        finally:
            _TRANSFER_QUEUE.task_done()
            # _TRANSFER_PENDING.discard(url)

async def _tasks_config_watcher():
    watch_dir = TASKS_CONFIG_PATH or "."
    if os.path.isdir(watch_dir):
        async for changes in awatch(watch_dir):
            try:
                target = os.path.normcase(os.path.abspath(watch_dir))
                for _, changed in changes:
                    if os.path.normcase(os.path.abspath(changed)) == target:
                        try:
                            task_scheduler.reload_from_config(changed)
                        except Exception:
                            pass
                        break
            except Exception:
                pass

@app.on_event("startup")
async def _on_startup():
    asyncio.create_task(_transfer_worker())
    try:
        os.makedirs(TASKS_CONFIG_PATH or ".", exist_ok=True)
    except Exception:
        pass
    asyncio.create_task(_tasks_config_watcher())
    task_scheduler.start()
    try:
        task_scheduler.load_from_config(os.path.join(TASKS_CONFIG_PATH or ".", "tasks.json"))
    except Exception:
        pass
    try:
        for bdir in (BAIDU_USER_DATA_DIR, ALIYUN_USER_DATA_DIR, JUEJIN_USER_DATA_DIR, V2EX_USER_DATA_DIR):
            manager._cleanup_profile_locks(bdir)
    except Exception:
        pass

@app.on_event("shutdown")
async def _on_shutdown():
    try:
        await manager.stop()
    except Exception:
        pass

# ================================================
#                FASTAPI ROUTES
# ================================================
@app.get("/login/qr")
async def login_qr(provider: str = "baidu", as_image: bool = False, account: str = ""):
    adapter = resolve_adapter_from_provider(provider)
    if not hasattr(adapter, "get_qr_code"):
        raise HTTPException(status_code=400, detail="unsupported provider")
    try:
        session_id, png, islogin = await adapter.get_qr_code(account or None)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    if not islogin:
        asyncio.create_task(adapter.poll_login_status(session_id))
        if as_image:
            return StreamingResponse(io.BytesIO(png), media_type="image/png")
    return {
        "session_id": session_id,
        "image_base64": base64.b64encode(png).decode(),
        "expires_in": 180,
        "islogin": islogin,
    }

@app.get("/login/vnc")
async def login_vnc(provider: str = "baidu",  account: str = ""):
    adapter = resolve_adapter_from_provider(provider)
    if not hasattr(adapter, "get_qr_code"):
        raise HTTPException(status_code=400, detail="unsupported provider")
    try:
        session_id, _, islogin = await adapter.get_qr_code(account or None)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    if not islogin:
        asyncio.create_task(adapter.poll_login_status(session_id))
    return RedirectResponse(url="http://localhost:6080/vnc.html?autoconnect=true&resize=scale&view_clip=true")

@app.post("/transfer", response_model=TransferResult)
async def transfer(req: TransferLink):
    print(req.model_dump_json())
    adapter = resolve_adapter_from_link(req.url)
    if adapter is None:
        raise HTTPException(status_code=400, detail="unsupported provider")
    url = (req.url or "").strip().strip('`"')
    if url in _TRANSFER_PENDING:
        return {
            "status": "ignored",
            "provider": getattr(adapter, "name", "unknown"),
            "share_link": url,
            "target_path": None,
            "message": "duplicate",
        }
    _TRANSFER_PENDING.add(url)
    await _TRANSFER_QUEUE.put((adapter, url))
    return {
        "status": "accepted",
        "provider": getattr(adapter, "name", "unknown"),
        "share_link": url,
        "target_path": None,
        "message": "queued",
    }

@app.post("/tasks/schedule_at", response_model=ScheduleResult)
async def schedule_at(req: ScheduleAtReq):
    if resolve_task_adapter(req.adapter) is None:
        raise HTTPException(status_code=400, detail="adapter_not_found")
    result = task_scheduler.schedule_at(req.adapter, req.run_at, provider=req.provider, accounts=req.accounts)
    return {
        "job_id": result["job_id"],
        "adapter": result["adapter"],
        "scheduled_at": result["scheduled_at"],
        "status": result["status"],
    }

@app.post("/tasks/schedule_between", response_model=ScheduleResult)
async def schedule_between(req: ScheduleBetweenReq):
    if resolve_task_adapter(req.adapter) is None:
        raise HTTPException(status_code=400, detail="adapter_not_found")
    try:
        result = task_scheduler.schedule_between(req.adapter, req.start_at, req.end_at, provider=req.provider, accounts=req.accounts)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "job_id": result["job_id"],
        "adapter": result["adapter"],
        "scheduled_at": result["scheduled_at"],
        "status": result["status"],
    }

@app.post("/tasks/schedule_window", response_model=ScheduleResult)
async def schedule_window(req: ScheduleWindowReq):
    if resolve_task_adapter(req.adapter) is None:
        raise HTTPException(status_code=400, detail="adapter_not_found")
    try:
        result = task_scheduler.schedule_window(req.adapter, req.base_at, req.window_minutes, provider=req.provider, accounts=req.accounts)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "job_id": result["job_id"],
        "adapter": result["adapter"],
        "scheduled_at": result["scheduled_at"],
        "status": result["status"],
    }

@app.post("/tasks/run_now", response_model=RunTaskResult)
async def run_now(req: RunTaskReq):
    if resolve_task_adapter(req.adapter) is None:
        raise HTTPException(status_code=400, detail="adapter_not_found")
    result = await task_scheduler.run_now(req.adapter, provider=req.provider, accounts=req.accounts)
    return {
        "status": result.get("status"),
        "adapter": req.adapter,
        "message": result.get("message"),
    }

@app.get("/adapters/enabled")
async def adapters_enabled():
    from .adapters import registry as adapters_registry
    providers = sorted(list(adapters_registry._REGISTRY.keys()))
    adapters = sorted({getattr(a, "name", k) for k, a in adapters_registry._REGISTRY.items()})
    return {"providers": providers, "adapters": adapters}

@app.get("/tasks/enabled")
async def tasks_enabled():
    from .tasks import registry as tasks_registry
    names = sorted(list(tasks_registry._TASK_REGISTRY.keys()))
    jobs = []
    try:
        for job in task_scheduler._scheduler.get_jobs():
            adapter_name = None
            try:
                if job.args and len(job.args) >= 1:
                    adapter_name = job.args[0]
            except Exception:
                pass
            jobs.append({
                "job_id": job.id,
                "adapter": adapter_name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            })
    except Exception:
        pass
    return {"tasks": names, "scheduled_jobs": jobs}
