import os
from pathlib import Path

HLS_DIR = Path("tmp/pi-tv-hls")
FRONTEND_DIST = Path("dist")
UPLOAD_DIR = Path("/tmp/setup_uploads")
M3U_TEMP_PATH = os.path.join(UPLOAD_DIR, "pending_playlist.m3u")
EPG_TEMP_PATH = os.path.join(UPLOAD_DIR, "pending_guide.xml")


HLS_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

IS_DEV = os.environ.get("PI_TV_DEV") == "true"
