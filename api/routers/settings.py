from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from app.db import (
    get_db_connection,
    get_creds,
    set_creds,
    get_domains,
    update_domains,
)
from api.streammanager import stream_manager

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/userpass")
def userpass(db=Depends(get_db_connection)):
    return get_creds(db)


@router.post("/userpass")
async def post_userpass(request: Request, db=Depends(get_db_connection)):
    data = await request.json()
    set_creds(db, data["username"], data["password"])
    return JSONResponse({"status": "ok"})


@router.get("/domains")
def domains(db=Depends(get_db_connection)):
    return get_domains(db)


@router.post("/domains")
async def post_domains(request: Request, db=Depends(get_db_connection)):
    data = await request.json()
    update_domains(db, data["domains"])
    return JSONResponse({"status": "ok"})


@router.post("/domains-test")
async def test_domains(request: Request, db=Depends(get_db_connection)):
    data = await request.json()
    creds = get_creds(db)
    results = []
    for domain in data["domains"]:
        url = f"http://{domain}/live/{creds['username']}/{creds['password']}/{stream_manager.current_channel['ts']}"
        results.append({"domain": domain, "working": stream_manager.test_url(url)})
    return JSONResponse(results)
