from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone, timedelta
from api.dependencies import get_db_context
from app.db import get_epg_status
from app.epg import refresh_epg

scheduler = AsyncIOScheduler()


async def check_and_refresh_epg():
    with get_db_context() as db:
        status = get_epg_status(db)
        url = status.get("epg_url")
        last_update_str = status.get("last_epg_update")

    if not url:
        return

    should_update = False

    if not last_update_str:
        should_update = True
    else:
        last_update = datetime.fromisoformat(last_update_str)
        if datetime.now(timezone.utc) - last_update >= timedelta(days=2):
            should_update = True

    if should_update:
        print(f"[Scheduler] EPG update triggered")
        await refresh_epg(url)
