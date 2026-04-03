"""SQLite database manager for the swimming competition timer application."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "renang.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create tables if they do not exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS competitions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                year        TEXT    NOT NULL,
                date_text   TEXT    NOT NULL,
                venue       TEXT    DEFAULT '',
                num_lanes   INTEGER DEFAULT 8,
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS events (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                competition_id  INTEGER NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
                acara_number    INTEGER NOT NULL,
                seri            TEXT    DEFAULT '',
                distance_m      INTEGER DEFAULT 50,
                stroke          TEXT    DEFAULT 'GAYA BEBAS',
                gender          TEXT    DEFAULT 'PUTRA',
                description     TEXT    DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS heats (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id    INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                heat_number INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS results (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                heat_id         INTEGER NOT NULL REFERENCES heats(id) ON DELETE CASCADE,
                lane            INTEGER NOT NULL,
                athlete_name    TEXT    DEFAULT '',
                school          TEXT    DEFAULT '',
                time_ms         INTEGER DEFAULT NULL,
                notes           TEXT    DEFAULT '',
                rank            INTEGER DEFAULT NULL
            );
        """)


# ── Competition ──────────────────────────────────────────────────────────────

def add_competition(title: str, year: str, date_text: str, venue: str = "", num_lanes: int = 8) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO competitions (title, year, date_text, venue, num_lanes) VALUES (?,?,?,?,?)",
            (title, year, date_text, venue, num_lanes),
        )
        return cur.lastrowid


def get_competitions():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM competitions ORDER BY id DESC")]


def get_competition(comp_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM competitions WHERE id=?", (comp_id,)).fetchone()
        return dict(row) if row else None


def update_competition(comp_id: int, title: str, year: str, date_text: str, venue: str, num_lanes: int):
    with get_connection() as conn:
        conn.execute(
            "UPDATE competitions SET title=?, year=?, date_text=?, venue=?, num_lanes=? WHERE id=?",
            (title, year, date_text, venue, num_lanes, comp_id),
        )


def delete_competition(comp_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM competitions WHERE id=?", (comp_id,))


# ── Events (Acara) ────────────────────────────────────────────────────────────

def add_event(competition_id: int, acara_number: int, seri: str = "", distance_m: int = 50,
              stroke: str = "GAYA BEBAS", gender: str = "PUTRA", description: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO events (competition_id, acara_number, seri, distance_m, stroke, gender, description) "
            "VALUES (?,?,?,?,?,?,?)",
            (competition_id, acara_number, seri, distance_m, stroke, gender, description),
        )
        return cur.lastrowid


def get_events(competition_id: int):
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM events WHERE competition_id=? ORDER BY acara_number", (competition_id,)
        )]


def get_event(event_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        return dict(row) if row else None


def update_event(event_id: int, acara_number: int, seri: str, distance_m: int,
                 stroke: str, gender: str, description: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE events SET acara_number=?, seri=?, distance_m=?, stroke=?, gender=?, description=? WHERE id=?",
            (acara_number, seri, distance_m, stroke, gender, description, event_id),
        )


def delete_event(event_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM events WHERE id=?", (event_id,))


# ── Heats ─────────────────────────────────────────────────────────────────────

def add_heat(event_id: int, heat_number: int) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO heats (event_id, heat_number) VALUES (?,?)",
            (event_id, heat_number),
        )
        return cur.lastrowid


def get_heats(event_id: int):
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM heats WHERE event_id=? ORDER BY heat_number", (event_id,)
        )]


def get_heat(heat_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM heats WHERE id=?", (heat_id,)).fetchone()
        return dict(row) if row else None


def delete_heat(heat_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM heats WHERE id=?", (heat_id,))


# ── Results ───────────────────────────────────────────────────────────────────

def upsert_result(heat_id: int, lane: int, athlete_name: str = "", school: str = "",
                  time_ms: int = None, notes: str = "") -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM results WHERE heat_id=? AND lane=?", (heat_id, lane)).fetchone()
        if row:
            conn.execute(
                "UPDATE results SET athlete_name=?, school=?, time_ms=?, notes=? WHERE id=?",
                (athlete_name, school, time_ms, notes, row["id"]),
            )
            return row["id"]
        cur = conn.execute(
            "INSERT INTO results (heat_id, lane, athlete_name, school, time_ms, notes) VALUES (?,?,?,?,?,?)",
            (heat_id, lane, athlete_name, school, time_ms, notes),
        )
        return cur.lastrowid


def get_results(heat_id: int):
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM results WHERE heat_id=? ORDER BY lane", (heat_id,)
        )]


def update_result_time(heat_id: int, lane: int, time_ms: int):
    with get_connection() as conn:
        conn.execute(
            "UPDATE results SET time_ms=? WHERE heat_id=? AND lane=?",
            (time_ms, heat_id, lane),
        )


def update_ranks(heat_id: int):
    """Recalculate and store rank for all results in a heat."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, time_ms FROM results WHERE heat_id=? AND time_ms IS NOT NULL ORDER BY time_ms",
            (heat_id,),
        ).fetchall()
        for idx, row in enumerate(rows, start=1):
            conn.execute("UPDATE results SET rank=? WHERE id=?", (idx, row["id"]))


def get_full_results(competition_id: int):
    """Return a flat list of all results for a competition, joined with event/heat info."""
    sql = """
        SELECT
            c.title          AS comp_title,
            c.year           AS comp_year,
            c.date_text      AS comp_date,
            c.venue          AS comp_venue,
            e.acara_number,
            e.seri,
            e.distance_m,
            e.stroke,
            e.gender,
            e.description    AS event_desc,
            h.heat_number,
            r.lane,
            r.athlete_name,
            r.school,
            r.time_ms,
            r.notes,
            r.rank
        FROM results r
        JOIN heats h      ON r.heat_id      = h.id
        JOIN events e     ON h.event_id     = e.id
        JOIN competitions c ON e.competition_id = c.id
        WHERE c.id = ?
        ORDER BY e.acara_number, h.heat_number, r.lane
    """
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(sql, (competition_id,))]


# ── Utilities ─────────────────────────────────────────────────────────────────

def ms_to_str(ms: int) -> str:
    """Convert milliseconds to MM:SS.ms string."""
    if ms is None:
        return ""
    total_sec = ms / 1000
    minutes = int(total_sec // 60)
    seconds = total_sec % 60
    return f"{minutes:02d}:{seconds:06.3f}"


def str_to_ms(time_str: str) -> int:
    """Convert MM:SS.ms string to milliseconds. Returns None on failure."""
    try:
        time_str = time_str.strip()
        if ":" in time_str:
            parts = time_str.split(":")
            minutes = int(parts[0])
            seconds = float(parts[1])
        else:
            minutes = 0
            seconds = float(time_str)
        return int((minutes * 60 + seconds) * 1000)
    except (ValueError, IndexError):
        return None
