from datetime import datetime, timezone
import os
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

from api.config import EPG_TEMP_PATH
from app.db import clear_prgrammes, get_epg_url, save_programme, update_epg_timestamp

import httpx
import anyio
import zlib
from datetime import datetime, timezone
from api.dependencies import get_db_context
from app.db import update_epg_timestamp  # Import your DB methods


async def download_epg(url_str: str):
    """Downloads, decompresses, and parses EPG data into the DB."""
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
        print(f"[EPG Cron] Error processing automatic EPG update: {exc}")


def parse_xmltv_time(s: str, target_tz: timezone | ZoneInfo = timezone.utc) -> str:
    """Converts an XMLTV time string (e.g., "20240628120000 +0000") to a standard
    SQLite text timestamp, adjusted to the specified target timezone.
    """
    # 1. Parse the string into a timezone-aware datetime object based on its actual offset
    dt = datetime.strptime(s, "%Y%m%d%H%M%S %z")

    # 2. Convert to the target timezone (e.g., UK time) and format for SQLite
    return dt.astimezone(target_tz).strftime("%Y-%m-%d %H:%M:%S")


def parse_xml_to_db(db, xml_path):
    clear_prgrammes(db)

    batch = []
    batch_size = 1000

    # Get total file size in bytes to calculate percentage
    total_size = os.path.getsize(xml_path)

    # Open the file manually so we can use .tell() to get the current byte position
    with open(xml_path, "rb") as f:
        # Pass the open file object to iterparse instead of the string path
        for event, elem in ET.iterparse(f, events=("end",)):
            if elem.tag == "programme":
                channel_id = elem.get("channel")
                title_elem = elem.find("title")
                title = title_elem.text if title_elem is not None else "Unknown Title"

                # Convert to normalized ISO text strings for SQLite
                start_time = parse_xmltv_time(
                    elem.get("start"), ZoneInfo("Europe/London")
                )
                stop_time = parse_xmltv_time(
                    elem.get("stop"), ZoneInfo("Europe/London")
                )

                batch.append((channel_id, title, start_time, stop_time))

                # When the batch is full, dump it into the database
                if len(batch) >= batch_size:
                    save_programme(db, batch)
                    batch = []

                    # Calculate and yield progress based on bytes processed
                    current_position = f.tell()
                    percentage = int((current_position / total_size) * 100)
                    yield percentage

                elem.clear()

        # Insert any remaining records left in the final batch
        if batch:
            save_programme(db, batch)

    # Yield 100% upon completion
    yield 100
    print("Database population complete!")


async def refresh_epg(url):
    with get_db_context() as db:
        await download_epg(url)
        # Consume the generator loop since parse_xml_to_db yields progress
        for progress in parse_xml_to_db(db, EPG_TEMP_PATH):
            pass

        # Update the 5-day tracker timestamp
        update_epg_timestamp(db)
        print("[EPG Cron] EPG successfully refreshed and parsed.")
