import sqlite3


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
        channel_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT,
        logo        TEXT,
        ts          TEXT,
        group_id    INTEGER,
        FOREIGN KEY(group_id) REFERENCES groups(group_id)
    );
    """

    with get_db_connection() as conn:
        cursor = conn.cursor()
        conn.execute("PRAGMA foreign_keys = ON;")

        cursor.execute(settings_table_schema)
        cursor.execute(domains_table_schema)
        cursor.execute(groups_table_schema)
        cursor.execute(channels_table_schema)

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


def save_channel(db, channel):
    cursor = db.cursor()
    group_title = channel.get("group-title", "")
    name = channel.get("tvg-name", "")
    logo = channel.get("tvg-logo", "")
    ts = channel.get("ts_id", "")

    if ts == "":
        return

    cursor.execute("INSERT OR IGNORE INTO groups (name) VALUES (?)", (group_title,))

    cursor.execute("SELECT group_id FROM groups WHERE name = ?", (group_title,))
    row = cursor.fetchone()
    group_id = row[0] if row else None

    cursor.execute(
        """
        INSERT INTO channels (name, logo, ts, group_id) 
        VALUES (?, ?, ?, ?)
    """,
        (name, logo, ts, group_id),
    )

    db.commit()


def get_last_channel(db):
    cursor = db.cursor()
    cursor.execute("SELECT last_channel_id FROM settings")
    result = cursor.fetchone()
    return result[0]


def update_last_channel(db, channel_id):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE settings SET last_channel_id= ? WHERE key='settings'", (channel_id,)
    )
    db.commit()


def get_channel_by_id(db, channel_id):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id,))
    result = cursor.fetchone()
    if result == None:
        raise KeyError
    channel = {}
    channel["id"] = result[0]
    channel["name"] = result[1]
    channel["logo"] = result[2]
    channel["ts"] = result[3]
    return channel


def get_group_channels(db, group_id):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM channels WHERE group_id = ?", (group_id,))
    return cursor.fetchall()


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
