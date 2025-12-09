from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from .schemas import TransferLink, TransferResult
from .adapters.registry import resolve_adapter_from_link, resolve_adapter_from_provider

import asyncio
import os
import base64
import io

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

@app.on_event("startup")
async def _on_startup():
    asyncio.create_task(_transfer_worker())

# ================================================
#                FASTAPI ROUTES
# ================================================
@app.get("/login/qr")
async def login_qr(provider: str = "baidu", as_image: bool = False, background_tasks: BackgroundTasks = None):
    adapter = resolve_adapter_from_provider(provider)
    if not hasattr(adapter, "get_qr_code"):
        raise HTTPException(status_code=400, detail="unsupported provider")
    try:
        session_id, png, islogin = await adapter.get_qr_code()
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

@app.post("/login/status")
async def login_status(provider: str = "baidu", session_id: str = ""):
    adapter = resolve_adapter_from_provider(provider)
    if not hasattr(adapter, "check_login_status"):
        raise HTTPException(status_code=400, detail="unsupported provider")
    return await adapter.check_login_status(session_id)


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
