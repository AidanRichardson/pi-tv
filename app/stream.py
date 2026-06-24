import subprocess
from pathlib import Path

ffmpeg_proc = None


def start_ffmpeg(url: str, HLS_DIR: Path):
    global ffmpeg_proc
    HLS_DIR.mkdir(exist_ok=True, parents=True)

    log_file_path = HLS_DIR / "ffmpeg.log"

    print(f"--- Starting FFmpeg: {url} ---")
    print(f"--- Logging to: {log_file_path} ---")

    log_file = open(log_file_path, "w")

    ffmpeg_proc = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "info",
            "-i",
            url,
            "-c",
            "copy",
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
    )


def stop_ffmpeg():
    global ffmpeg_proc
    if ffmpeg_proc:
        print("--- Terminating FFmpeg ---")
        ffmpeg_proc.terminate()
        try:
            ffmpeg_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            ffmpeg_proc.kill()
        ffmpeg_proc = None


def is_ffmpeg_running() -> bool:
    return ffmpeg_proc is not None
