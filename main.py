from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from api.config import HLS_DIR, FRONTEND_DIST, IS_DEV
from api.dependencies import get_db_context
from api.streammanager import stream_manager
from api.routers import settings
from app.db import init_db, is_setup_complete, get_channel_by_id, get_last_channel
from app.stream import is_ffmpeg_running, stop_ffmpeg
from api.routers import setup
from api.routers import streaming


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    init_db()
    with get_db_context() as db:
        if is_setup_complete(db):
            stream_manager.current_channel = get_channel_by_id(db, get_last_channel(db))
            stream_manager.build_url(db, stream_manager.current_channel["ts"])
    yield
    # Shutdown tasks (Replaces atexit)
    stop_ffmpeg()


app = FastAPI(lifespan=lifespan)

# Include Organized Routers
app.include_router(setup.router)
app.include_router(streaming.router)
app.include_router(settings.router)


# Middleware guard
@app.middleware("http")
async def setup_guard(request: Request, call_next):
    with get_db_context() as db:
        if not is_setup_complete(db):
            is_allowed_path = request.url.path.startswith(("/setup", "/api", "/assets"))
            if not is_allowed_path:
                return RedirectResponse(url="/setup")
    return await call_next(request)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    stream_manager.connected_clients.append(ws)
    if not is_ffmpeg_running():
        stream_manager.begin_stream()
    try:
        while True:
            await ws.receive_text()
    except:
        stream_manager.connected_clients.remove(ws)
        if len(stream_manager.connected_clients) == 0:
            stop_ffmpeg()
            stream_manager.clear_hls_dir()


# Static Files & Frontend Routing
app.mount("/api/hls", StaticFiles(directory=HLS_DIR), name="hls")

if not IS_DEV:
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        return FileResponse(FRONTEND_DIST / "index.html")
