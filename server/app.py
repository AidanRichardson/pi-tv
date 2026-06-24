import atexit
import asyncio
from contextlib import contextmanager
import json
import threading
import time
import os
from pathlib import Path
import anyio
import httpx

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    WebSocket,
    Request,
    UploadFile,
    File,
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
import shutil
import urllib.request

from server.db import *
from server.playlist import parse_m3u
from server.stream import start_ffmpeg, stop_ffmpeg, is_ffmpeg_running

HLS_DIR = Path("tmp/pi-tv-hls")
FRONTEND_DIST = Path("dist")
UPLOAD_DIR = "/tmp/setup_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
M3U_TEMP_PATH = os.path.join(UPLOAD_DIR, "pending_playlist.m3u")

HLS_DIR.mkdir(parents=True, exist_ok=True)

init_db()


@contextmanager
def get_db_context():
    db = get_db_connection()
    try:
        yield db
    finally:
        db.close()


conn = get_db_connection()
SETUP = is_setup_complete(conn)

app = FastAPI()
connected_clients: list[WebSocket] = []
atexit.register(stop_ffmpeg)


def test_url(url: str) -> bool:
    try:
        req = urllib.request.Request(
            url, method="GET", headers={"User-Agent": "VLC/3.0.0 LibVLC/3.0.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status == 200
    except Exception:
        return False


def build_url(db, ts):
    domains = get_domains(db)
    creds = get_creds(db)

    for domain in domains:
        url = f"http://{domain[1]}/live/{creds['username']}/{creds['password']}/{ts}"
        if test_url(url):
            current_channel["url"] = url
            return

    current_channel["url"] = None
    print("--- No working domain found ---")


if SETUP:
    current_channel = get_channel_by_id(conn, get_last_channel(conn))
    build_url(conn, current_channel["ts"])

conn.close()


def clear_hls_dir():
    for f in HLS_DIR.glob("*"):
        f.unlink()


def wait_for_manifest():
    manifest = HLS_DIR / "output.m3u8"
    while not manifest.exists():
        time.sleep(0.5)


async def broadcast(message: str):
    for client in connected_clients:
        try:
            await client.send_text(message)
        except:
            pass


def begin_stream(url: str):
    """Stop any existing stream, clear tmp files, start fresh, notify clients when ready."""
    stop_ffmpeg()
    clear_hls_dir()
    start_ffmpeg(url, HLS_DIR)
    threading.Thread(target=notify_when_ready, daemon=True).start()


def notify_when_ready():
    wait_for_manifest()
    time.sleep(2)
    asyncio.run(broadcast("ready"))


@app.middleware("http")
async def setup_guard(request: Request, call_next):
    with get_db_context() as db:
        if not is_setup_complete(db):

            is_allowed_path = request.url.path.startswith(("/setup", "/api", "/assets"))

            if not is_allowed_path:
                return RedirectResponse(url="/setup")

    return await call_next(request)


@app.post("/api/setup/upload-m3u")
async def setup_upload_m3u(file: UploadFile = File(...)):
    if not file.filename.endswith((".m3u", ".m3u8")):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be M3U.")

    with open(M3U_TEMP_PATH, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"status": "success", "message": "Playlist uploaded successfully."}


@app.post("/api/setup/upload-url-m3u")
async def setup_upload_m3u_from_url(request: Request):
    try:
        data = await request.json()
        url_str = str(data["url"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body or missing 'url' key.",
        )

    try:
        # Stream the file download asynchronously
        async with httpx.AsyncClient(follow_redirects=True) as client:
            async with client.stream("GET", url_str) as response:
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to fetch file from URL. HTTP Status: {response.status_code}",
                    )

                # Open the file asynchronously using anyio
                # Open the file asynchronously using anyio
                async with await anyio.open_file(M3U_TEMP_PATH, "wb") as buffer:
                    # Notice 'async for' combined with 'aiter_bytes()'
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        await buffer.write(chunk)

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while requesting the URL: {str(exc)}",
        )

    return {
        "status": "success",
        "message": "Playlist downloaded and saved successfully.",
    }


@app.get("/api/setup/parse-playlist")
async def setup_parse_playlist():
    if not os.path.exists(M3U_TEMP_PATH):
        raise HTTPException(
            status_code=400, detail="No uploaded playlist found. Please upload first."
        )

    async def generate():
        with get_db_context() as db:
            try:
                for pct in parse_m3u(db, M3U_TEMP_PATH):
                    yield f"data: {json.dumps({'progress': pct})}\n\n"

                yield f"data: {json.dumps({'progress': 100, 'done': True})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

            finally:
                if os.path.exists(M3U_TEMP_PATH):
                    os.unlink(M3U_TEMP_PATH)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/setup/complete")
async def setup_complete_endpoint(request: Request):
    global current_channel
    data = await request.json()
    with get_db_context() as db:
        set_creds(db, data["username"], data["password"])
        for domain in data["domains"]:
            domain = domain.strip()
            if domain:
                domain = domain.removeprefix("http://").removeprefix("https://")
                domain = domain.rstrip("/")
                add_domain(db, domain)
        mark_setup_complete(db)
        current_channel = get_channel_by_id(db, get_last_channel(db))
        build_url(db, current_channel["ts"])
    return JSONResponse({"status": "ok"})


@app.get("/api/start")
async def start_stream():
    if is_ffmpeg_running():
        return JSONResponse({"status": "already running"})
    begin_stream(current_channel["url"])
    return JSONResponse({"status": "starting", "channel": current_channel["name"]})


@app.get("/api/stop")
async def stop_stream():
    stop_ffmpeg()
    clear_hls_dir()
    await broadcast("stopped")
    return JSONResponse({"status": "stopped"})


@app.get("/api/switch/{channel_id}")
async def switch(channel_id: int, db=Depends(get_db_connection)):
    global current_channel
    try:
        channel = get_channel_by_id(db, channel_id)
    except:
        return JSONResponse({"error": "channel not found"}, status_code=404)
    current_channel = channel
    update_last_channel(db, channel_id)
    build_url(db, channel["ts"])
    await broadcast("switching")
    begin_stream(current_channel["url"])
    return JSONResponse({"status": "switching", "channel": current_channel["name"]})


@app.get("/api/userpass")
def userpass(db=Depends(get_db_connection)):
    return get_creds(db)


@app.post("/api/userpass")
async def post_userpass(request: Request, db=Depends(get_db_connection)):
    data = await request.json()
    set_creds(db, data["username"], data["password"])
    return JSONResponse({"status": "ok"})


@app.get("/api/domains")
def domains(db=Depends(get_db_connection)):
    return get_domains(db)


@app.post("/api/domains")
async def post_domains(request: Request, db=Depends(get_db_connection)):
    data = await request.json()
    data = data["domains"]
    update_domains(db, data)
    return JSONResponse({"status": "ok"})


@app.post("/api/domains-test")
async def test_domains(request: Request, db=Depends(get_db_connection)):
    data = await request.json()
    data = data["domains"]
    creds = get_creds(db)
    results = []
    for domain in data:
        url = f"http://{domain}/live/{creds['username']}/{creds['password']}/{current_channel["ts"]}"
        results.append({"domain": domain, "working": test_url(url)})

    return JSONResponse(results)


@app.get("/api/groups")
def groups(db=Depends(get_db_connection)):
    return get_groups(db)


@app.get("/api/channels/{group_id}")
def channels(group_id: int, db=Depends(get_db_connection)):
    return get_group_channels(db, group_id)


@app.get("/api/status")
def status():
    return JSONResponse(
        {
            "channel_id": current_channel["id"],
            "channel": current_channel["name"],
            "streaming": is_ffmpeg_running(),
        }
    )


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    if not is_ffmpeg_running():
        begin_stream(current_channel["url"])
    try:
        while True:
            await ws.receive_text()
    except:
        connected_clients.remove(ws)
        if len(connected_clients) == 0:
            stop_ffmpeg()
            clear_hls_dir()


app.mount("/api/hls", StaticFiles(directory=HLS_DIR), name="hls")

if os.environ.get("PI_TV_DEV") != "true":
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        return FileResponse(FRONTEND_DIST / "index.html")
