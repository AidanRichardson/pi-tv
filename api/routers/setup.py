import json
import os
import shutil
import zlib
import anyio
import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from fastapi.responses import JSONResponse, StreamingResponse

from api.config import EPG_TEMP_PATH, M3U_TEMP_PATH
from api.dependencies import get_db_context
from api.streammanager import stream_manager
from app.epg import download_epg, parse_xml_to_db
from app.playlist import parse_m3u
from app.db import (
    set_epg_url,
    set_creds,
    add_domain,
    mark_setup_complete,
    get_channel_by_id,
    get_last_channel,
)

router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.post("/upload-m3u")
async def setup_upload_m3u(file: UploadFile = File(...)):
    if file.filename and not file.filename.endswith((".m3u", ".m3u8")):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be M3U.")
    with open(M3U_TEMP_PATH, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "success", "message": "Playlist uploaded successfully."}


@router.post("/upload-url-m3u")
async def setup_upload_m3u_from_url(request: Request):
    try:
        data = await request.json()
        url_str = str(data["url"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=400, detail="Invalid JSON body or missing 'url' key."
        )

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            async with client.stream("GET", url_str) as response:
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=400, detail="Failed to fetch file from URL."
                    )

                async with await anyio.open_file(M3U_TEMP_PATH, "wb") as buffer:
                    async_iter = response.aiter_bytes(chunk_size=8192)
                    async for chunk in async_iter:
                        await buffer.write(chunk)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=500, detail=f"Request error: {str(exc)}")

    return {"status": "success", "message": "Playlist saved successfully."}


@router.post("/upload-url-epg")
async def setup_upload_epg_from_url(request: Request):
    try:
        data = await request.json()
        url_str = str(data["url"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=400, detail="Invalid JSON body or missing 'url' key."
        )

    await download_epg(url_str)

    with get_db_context() as db:
        set_epg_url(db, url_str)

    return {"status": "success", "message": "EPG saved successfully."}


@router.get("/parse-playlist")
async def setup_parse_epg():
    if not os.path.exists(EPG_TEMP_PATH):
        raise HTTPException(status_code=400, detail="No uploaded epg found.")

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


@router.get("/parse-epg")
async def setup_parse_playlist():
    if not os.path.exists(EPG_TEMP_PATH):
        raise HTTPException(status_code=400, detail="No uploaded epg found.")

    async def generate():
        with get_db_context() as db:
            try:
                for pct in parse_xml_to_db(db, EPG_TEMP_PATH):
                    yield f"data: {json.dumps({'progress': pct})}\n\n"
                yield f"data: {json.dumps({'progress': 100, 'done': True})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            finally:
                if os.path.exists(M3U_TEMP_PATH):
                    os.unlink(M3U_TEMP_PATH)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/complete")
async def setup_complete_endpoint(request: Request):
    data = await request.json()
    with get_db_context() as db:
        set_creds(db, data["username"], data["password"])
        for domain in data["domains"]:
            domain = (
                domain.strip()
                .removeprefix("http://")
                .removeprefix("https://")
                .rstrip("/")
            )
            if domain:
                add_domain(db, domain)
        mark_setup_complete(db)

        stream_manager.current_channel = get_channel_by_id(db, get_last_channel(db))
        stream_manager.build_url(db, stream_manager.current_channel["ts"])
    return JSONResponse({"status": "ok"})
