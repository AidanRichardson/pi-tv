import httpx
import anyio
import zlib
import asyncio
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
from api.config import EPG_TEMP_PATH
from api.dependencies import get_db_context
from app.db import clear_prgrammes, save_programme, update_epg_timestamp


async def download_epg(url_str: str):
    """Downloads, decompresses (if epg is compressed), and parses EPG data into the DB."""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            async with client.stream("GET", url_str) as response:
                if response.status_code != 200:
                    print(f"[EPG Cron] Failed to fetch. Status: {response.status_code}")
                    return

                async with await anyio.open_file(EPG_TEMP_PATH, "wb") as buffer:
                    async_iter = response.aiter_bytes(chunk_size=8192)
                    try:
                        first_chunk = await anext(async_iter)
                    except StopAsyncIteration:
                        first_chunk = b""

                    is_gzip = first_chunk.startswith(b"\x1f\x8b")
                    if is_gzip:
                        decompressor = zlib.decompressobj(wbits=16 + 15)
                        if first_chunk:
                            await buffer.write(decompressor.decompress(first_chunk))
                        async for chunk in async_iter:
                            await buffer.write(decompressor.decompress(chunk))
                        remainder = decompressor.flush()
                        if remainder:
                            await buffer.write(remainder)
                    else:
                        if first_chunk:
                            await buffer.write(first_chunk)
                        async for chunk in async_iter:
                            await buffer.write(chunk)

    except Exception as exc:
        print(f"[EPG Cron] Error processing automatic EPG: {exc}")

    print(f"[EPG Cron] EPG Downloaded")


def parse_xmltv_time(
    s: str | None, target_tz: timezone | ZoneInfo = timezone.utc
) -> str:
    """Converts an XMLTV time string (e.g., "20240628120000 +0000") to a standard
    SQLite text timestamp, adjusted to the specified target timezone.
    """
    if not s:
        return ""
    dt = datetime.strptime(s, "%Y%m%d%H%M%S %z")

    return dt.astimezone(target_tz).strftime("%Y-%m-%d %H:%M:%S")


def parse_xml_to_db(db, xml_path):
    clear_prgrammes(db)

    batch = []
    batch_size = 1000

    total_size = os.path.getsize(xml_path)

    with open(xml_path, "rb") as f:
        for event, elem in ET.iterparse(f, events=("end",)):
            if elem.tag == "programme":
                channel_id = elem.get("channel")
                title_elem = elem.find("title")
                title = title_elem.text if title_elem is not None else "Unknown Title"

                start_time = parse_xmltv_time(
                    elem.get("start"), ZoneInfo("Europe/London")
                )
                stop_time = parse_xmltv_time(
                    elem.get("stop"), ZoneInfo("Europe/London")
                )

                batch.append((channel_id, title, start_time, stop_time))

                if len(batch) >= batch_size:
                    save_programme(db, batch)
                    batch = []

                    current_position = f.tell()
                    percentage = int((current_position / total_size) * 100)
                    yield percentage

                elem.clear()

        if batch:
            save_programme(db, batch)

    yield 100
    print(f"[EPG Cron] EPG parsed into database")


def _run_parsing_sync(xml_path: str):
    with get_db_context() as db:
        for progress in parse_xml_to_db(db, xml_path):
            pass

        update_epg_timestamp(db)


async def refresh_epg(url: str):
    print("[EPG Cron] Downloading EPG...")

    await download_epg(url)

    print("[EPG Cron] Starting XML parsing")
    await asyncio.to_thread(_run_parsing_sync, EPG_TEMP_PATH)

    print("[EPG Cron] EPG successfully refreshed and parsed.")
