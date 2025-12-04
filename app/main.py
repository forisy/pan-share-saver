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

# ================================================
#                FASTAPI ROUTES
# ================================================
@app.get("/login/qr")
async def login_qr(provider: str = "baidu", as_image: bool = False, background_tasks: BackgroundTasks = None):
    adapter = resolve_adapter_from_provider(provider)
    if not hasattr(adapter, "get_qr_code"):
        raise HTTPException(status_code=400, detail="unsupported provider")
    session_id, png = await asyncio.to_thread(adapter.get_qr_code)
    background_tasks.add_task(asyncio.to_thread, adapter.poll_login_status, session_id)
    if as_image:
        return StreamingResponse(io.BytesIO(png), media_type="image/png")
    return {
        "session_id": session_id,
        "image_base64": base64.b64encode(png).decode(),
        "expires_in": 180,
    }

@app.post("/login/status")
async def login_status(provider: str = "baidu", session_id: str = ""):
    adapter = resolve_adapter_from_provider(provider)
    if not hasattr(adapter, "check_login_status"):
        raise HTTPException(status_code=400, detail="unsupported provider")
    return await asyncio.to_thread(adapter.check_login_status, session_id)


@app.post("/transfer", response_model=TransferResult)
async def transfer(req: TransferLink):
    print(req.model_dump_json())
    adapter = resolve_adapter_from_link(req.url)
    if adapter is None:
        raise HTTPException(status_code=400, detail="unsupported provider")
    try:
        result = await adapter.transfer(req.url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
