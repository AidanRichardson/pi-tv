from fastapi import APIRouter, WebSocket, Depends
from fastapi.responses import JSONResponse
from app.db import (
    get_db_connection,
    get_channel_by_id,
    get_group_channels,
    get_groups,
    get_live_programme,
    update_last_channel,
)
from app.stream import is_ffmpeg_running, stop_ffmpeg
from api.streammanager import stream_manager

router = APIRouter(prefix="/api", tags=["streaming"])


@router.get("/start")
async def start_stream():
    if is_ffmpeg_running():
        return JSONResponse({"status": "already running"})
    stream_manager.begin_stream()
    return JSONResponse(
        {"status": "starting", "channel": stream_manager.current_channel["name"]}
    )


@router.get("/stop")
async def stop_stream():
    stop_ffmpeg()
    stream_manager.clear_hls_dir()
    await stream_manager.broadcast("stopped")
    return JSONResponse({"status": "stopped"})


@router.get("/switch/{channel_id}")
async def switch(channel_id: int, db=Depends(get_db_connection)):
    try:
        channel = get_channel_by_id(db, channel_id)
    except:
        return JSONResponse({"error": "channel not found"}, status_code=404)

    stream_manager.current_channel = channel
    update_last_channel(db, channel_id)
    stream_manager.build_url(db, channel["ts"])

    await stream_manager.broadcast("switching")
    stream_manager.begin_stream()
    return JSONResponse({"status": "switching", "channel": channel["name"]})


@router.get("/groups")
def groups(db=Depends(get_db_connection)):
    return get_groups(db)


@router.get("/channels/{group_id}")
def channels(group_id: int, db=Depends(get_db_connection)):
    return get_group_channels(db, group_id)


@router.get("/status")
def status(db=Depends(get_db_connection)):
    channel_info = get_channel_by_id(db, stream_manager.current_channel["id"])
    live_programme = get_live_programme(db, channel_info["channel_id"])
    return JSONResponse(
        {
            "id": (channel_info["id"] if channel_info else None),
            "channel": (channel_info["name"] if channel_info else None),
            "programme": (live_programme["title"] if live_programme else None),
            "started": (live_programme["start_time"] if live_programme else None),
            "ending": (live_programme["stop_time"] if live_programme else None),
            "streaming": is_ffmpeg_running(),
        }
    )
