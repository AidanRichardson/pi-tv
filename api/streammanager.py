import asyncio
import threading
import time
import urllib.request
from fastapi import WebSocket
from api.config import HLS_DIR
from app.db import get_domains, get_creds
from app.stream import start_ffmpeg, stop_ffmpeg


class StreamManager:
    def __init__(self):
        self.connected_clients: list[WebSocket] = []
        self.current_channel: dict = {}

    def test_url(self, url: str) -> bool:
        try:
            req = urllib.request.Request(
                url, method="GET", headers={"User-Agent": "VLC/3.0.0 LibVLC/3.0.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status == 200
        except Exception:
            return False

    def build_url(self, db, ts):
        if not self.current_channel:
            return
        domains = get_domains(db)
        creds = get_creds(db)

        for domain in domains:
            url = (
                f"http://{domain[1]}/live/{creds['username']}/{creds['password']}/{ts}"
            )
            if self.test_url(url):
                self.current_channel["url"] = url
                return

        self.current_channel["url"] = ""
        print("--- No working domain found ---")

    def clear_hls_dir(self):
        for f in HLS_DIR.glob("*"):
            f.unlink()

    def wait_for_manifest(self):
        manifest = HLS_DIR / "output.m3u8"
        while not manifest.exists():
            time.sleep(0.5)

    async def broadcast(self, message: str):
        for client in self.connected_clients:
            try:
                await client.send_text(message)
            except:
                pass

    def begin_stream(self):
        if not self.current_channel or not self.current_channel.get("url"):
            return
        stop_ffmpeg()
        self.clear_hls_dir()
        start_ffmpeg(self.current_channel["url"], HLS_DIR)
        threading.Thread(target=self._notify_when_ready, daemon=True).start()

    def _notify_when_ready(self):
        self.wait_for_manifest()
        time.sleep(2)
        asyncio.run(self.broadcast("ready"))


stream_manager = StreamManager()
