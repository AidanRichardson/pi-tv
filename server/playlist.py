import re

from server.db import save_channel


def parse_m3u(db, path: str):
    with open(path) as f:
        lines = f.readlines()

    total = sum(1 for l in lines if "#EXTINF" in l)
    count = 0

    for i, line in enumerate(lines):
        if "#EXTINF" in line:
            x = re.findall(r'([\w][\w-]*)="([^"]*)"', line)
            channel = {}
            for value in x:
                channel[value[0]] = value[1]
            url_split = lines[i + 1].strip().split("/")
            channel["ts_id"] = (
                lines[i + 1].strip().split("/")[6] if len(url_split) >= 7 else ""
            )
            save_channel(db, channel)
            count += 1
            yield int((count / total) * 100)
