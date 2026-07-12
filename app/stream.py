import os
import subprocess
from pathlib import Path

ffmpeg_proc = None


def start_ffmpeg(url: str, HLS_DIR: Path):
    global ffmpeg_proc

    HLS_DIR.mkdir(exist_ok=True, parents=True)
    log_file_path = HLS_DIR / "ffmpeg.log"

    print(f"--- Starting FFmpeg: {url} ---")
    print(f"--- Logging to: {log_file_path} ---")

    ffmpeg_cmd = "ffmpeg"

    with open(log_file_path, "w") as log_file:
        ffmpeg_proc = subprocess.Popen(
            [
                ffmpeg_cmd,
                "-y",
                "-loglevel",
                "info",
                "-i",
                url,
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-f",
                "hls",
                "-hls_time",
                "4",
                "-hls_list_size",
                "5",
                "-hls_flags",
                "delete_segments",
                str(HLS_DIR / "output.m3u8"),
            ],
            stdout=log_file,
            stderr=log_file,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )


def stop_ffmpeg():
    global ffmpeg_proc
    if ffmpeg_proc:
        print("--- Terminating FFmpeg ---")
        ffmpeg_proc.terminate()
        try:
            ffmpeg_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("--- Force Killing FFmpeg ---")
            ffmpeg_proc.kill()
        ffmpeg_proc = None


def is_ffmpeg_running() -> bool:
    global ffmpeg_proc
    if ffmpeg_proc is not None:
        if ffmpeg_proc.poll() is None:
            return True
        else:
            ffmpeg_proc = None
    return False
