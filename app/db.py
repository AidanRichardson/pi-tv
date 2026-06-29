from datetime import datetime, timezone
import sqlite3
from zoneinfo import ZoneInfo


def get_db_connection():
    """Returns a new connection for a single request/operation."""
    conn = sqlite3.connect("pi-tv.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    settings_table_schema = """
    CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        setup_complete BOOLEAN,
        provider_username TEXT,
        provider_password TEXT,
        epg_url TEXT,
        last_epg_update TEXT,
        last_channel_id INTEGER
    );
    """

    domains_table_schema = """
    CREATE TABLE IF NOT EXISTS domains (
        key   INTEGER PRIMARY KEY AUTOINCREMENT,
        domain TEXT
    );
    """

    groups_table_schema = """
    CREATE TABLE IF NOT EXISTS groups (
        group_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT UNIQUE
    );
    """

    channels_table_schema = """
    CREATE TABLE IF NOT EXISTS channels (
        id  INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id  TEXT,
        name        TEXT,
        logo        TEXT,
        ts          TEXT,
        group_id    INTEGER,
        FOREIGN KEY(group_id) REFERENCES groups(group_id)
    );
    """

    programmes_table_schema = """
        CREATE TABLE IF NOT EXISTS programmes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            title TEXT,
            start_time TEXT,
            stop_time TEXT
        )
    """

    with get_db_connection() as conn:
        cursor = conn.cursor()
        conn.execute("PRAGMA foreign_keys = ON;")

        cursor.execute(settings_table_schema)
        cursor.execute(domains_table_schema)
        cursor.execute(groups_table_schema)
        cursor.execute(channels_table_schema)
        cursor.execute(programmes_table_schema)

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_programme_times ON programmes (start_time, stop_time)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_programme_channel ON programmes (channel_id)"
        )

        cursor.execute("SELECT * FROM settings")
        result = cursor.fetchone()

        if not result:
            cursor.execute(
                "INSERT INTO settings VALUES ('settings', false, 'USERNAME','PASSWORD', 1)"
            )

        conn.commit()


def is_setup_complete(db):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM settings")
    result = cursor.fetchone()
    return bool(result[1])


def mark_setup_complete(db):
    cursor = db.cursor()
    cursor.execute("UPDATE settings SET setup_complete=true WHERE key='settings'")
    db.commit()


def set_epg_url(db, url):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE settings SET epg_url= ? WHERE key='settings'",
        (url,),
    )
    db.commit()


def get_epg_url(db):
    cursor = db.cursor()
    cursor.execute("SELECT epg_url FROM settings")
    result = cursor.fetchone()
    return {"epg_url": result[0]}


def update_epg_timestamp(db):
    """Updates the last fetched timestamp to right now."""
    cursor = db.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        "UPDATE settings SET last_epg_update = ? WHERE key='settings'",
        (now_iso,),
    )
    db.commit()


def get_epg_status(db):
    """Returns both the URL and the last update timestamp."""
    cursor = db.cursor()
    cursor.execute("SELECT epg_url, last_epg_update FROM settings WHERE key='settings'")
    result = cursor.fetchone()
    if result:
        return {"epg_url": result[0], "last_epg_update": result[1]}
    return {"epg_url": None, "last_epg_update": None}


def clear_prgrammes(db):
    cursor = db.cursor()
    cursor.execute("DELETE FROM programmes")


def save_programme(db, programme_batch):
    cursor = db.cursor()
    cursor.executemany(
        "INSERT INTO programmes (channel_id, title, start_time, stop_time) VALUES (?, ?, ?, ?)",
        programme_batch,
    )
    db.commit()


def save_channel(db, channel):
    cursor = db.cursor()
    channel_id = channel.get("tvg-id", "")
    group_title = channel.get("group-title", "")
    name = channel.get("tvg-name", "")
    logo = channel.get("tvg-logo", "")
    ts = channel.get("ts", "")

    if ts == "":
        return

    cursor.execute("INSERT OR IGNORE INTO groups (name) VALUES (?)", (group_title,))

    cursor.execute("SELECT group_id FROM groups WHERE name = ?", (group_title,))
    row = cursor.fetchone()
    group_id = row[0] if row else None

    cursor.execute(
        """
        INSERT INTO channels (channel_id, name, logo, ts, group_id) 
        VALUES (?, ?, ?, ?, ?)
    """,
        (channel_id, name, logo, ts, group_id),
    )

    db.commit()


def get_last_channel(db):
    cursor = db.cursor()
    cursor.execute("SELECT last_channel_id FROM settings")
    result = cursor.fetchone()
    return result[0]


def update_last_channel(db, id):
    cursor = db.cursor()
    cursor.execute("UPDATE settings SET last_channel_id= ? WHERE key='settings'", (id,))
    db.commit()


def get_channel_by_id(db, id):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM channels WHERE id = ?", (id,))
    result = cursor.fetchone()
    if result == None:
        raise KeyError
    channel = {}
    channel["id"] = result[0]
    channel["channel_id"] = result[1]
    channel["name"] = result[2]
    channel["logo"] = result[3]
    channel["ts"] = result[4]
    return channel


def get_live_programme(db, channel_id):
    cursor = db.cursor()
    now_str = datetime.now(ZoneInfo("Europe/London")).strftime("%Y-%m-%d %H:%M:%S")

    query = """
        SELECT title, start_time, stop_time 
        FROM programmes 
        WHERE channel_id = ? 
          AND start_time <= ? 
          AND stop_time > ?
        LIMIT 1
    """

    cursor.execute(query, (channel_id, now_str, now_str))
    result = cursor.fetchone()

    if result:
        return {
            "title": result[0],
            "start_time": result[1],
            "stop_time": result[2],
        }
    return None


def get_group_channels(db, group_id):
    # CRITICAL: This allows fetching rows as dictionary-like objects
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    cursor.execute("SELECT * FROM channels WHERE group_id = ?", (group_id,))
    channels = cursor.fetchall()

    # Convert the sqlite3.Row objects to actual mutable dicts so you can add the "programme" key
    channels_dict_list = [dict(channel) for channel in channels]

    for channel in channels_dict_list:
        channel["programme"] = get_live_programme(db, channel["channel_id"])

    return channels_dict_list


def get_groups(db):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM groups")
    return cursor.fetchall()


def add_domain(db, domain):
    cursor = db.cursor()
    cursor.execute("""INSERT INTO domains VALUES (NULL, ?)""", (domain,))
    db.commit()


def get_domains(db):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM domains")
    return cursor.fetchall()


def update_domains(db, domains_list):
    cursor = db.cursor()

    try:
        cursor.execute("DELETE FROM domains")

        for domain in domains_list:
            domain = domain.strip()
            if domain:
                domain = domain.removeprefix("http://").removeprefix("https://")
                domain = domain.rstrip("/")
            cursor.execute("""INSERT INTO domains VALUES (NULL, ?)""", (domain,))
        db.commit()

    except Exception as e:
        db.rollback()
        raise e


def set_creds(db, username, password):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE settings SET provider_username= ?, provider_password= ? WHERE key='settings'",
        (
            username,
            password,
        ),
    )
    db.commit()


def get_creds(db):
    cursor = db.cursor()
    cursor.execute("SELECT provider_username, provider_password FROM settings")
    result = cursor.fetchone()
    creds = {}
    creds["username"] = result[0]
    creds["password"] = result[1]
    return creds
