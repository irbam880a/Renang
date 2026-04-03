'use strict';
const { DatabaseSync } = require('node:sqlite');
const path = require('path');

const DB_PATH = path.join(__dirname, 'renang.db');
const db = new DatabaseSync(DB_PATH);

db.exec('PRAGMA journal_mode = WAL');
db.exec('PRAGMA foreign_keys = ON');

// ─── Schema ───────────────────────────────────────────────────────────────────

db.exec(`
  CREATE TABLE IF NOT EXISTS meets (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    nama             TEXT    NOT NULL,
    jumlah_lintasan  INTEGER NOT NULL DEFAULT 8 CHECK(jumlah_lintasan BETWEEN 1 AND 16),
    tanggal          TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
  );

  CREATE TABLE IF NOT EXISTS events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    meet_id  INTEGER NOT NULL REFERENCES meets(id) ON DELETE CASCADE,
    no       INTEGER NOT NULL,
    judul    TEXT,
    jarak    TEXT,
    gaya     TEXT
  );

  CREATE TABLE IF NOT EXISTS heats (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id  INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    heat      INTEGER NOT NULL DEFAULT 1,
    lintasan  INTEGER
  );

  CREATE TABLE IF NOT EXISTS entries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    heat_id      INTEGER NOT NULL REFERENCES heats(id) ON DELETE CASCADE,
    lane         INTEGER NOT NULL CHECK(lane BETWEEN 1 AND 16),
    name         TEXT    NOT NULL DEFAULT '',
    club         TEXT    DEFAULT '',
    country      TEXT    DEFAULT '',
    seed         TEXT    DEFAULT '',
    result_time  TEXT    DEFAULT '',
    result_rank  INTEGER,
    UNIQUE(heat_id, lane)
  );
`);

// ─── Meets ────────────────────────────────────────────────────────────────────

const stmts = {
  listMeets:   db.prepare('SELECT * FROM meets ORDER BY id DESC'),
  getMeet:     db.prepare('SELECT * FROM meets WHERE id = ?'),
  insertMeet:  db.prepare('INSERT INTO meets (nama, jumlah_lintasan, tanggal) VALUES (@nama, @jumlah_lintasan, @tanggal)'),
  updateMeet:  db.prepare('UPDATE meets SET nama=@nama, jumlah_lintasan=@jumlah_lintasan, tanggal=@tanggal WHERE id=@id'),
  deleteMeet:  db.prepare('DELETE FROM meets WHERE id = ?'),

  // Events
  listEvents:  db.prepare('SELECT * FROM events WHERE meet_id = ? ORDER BY no'),
  getEvent:    db.prepare('SELECT * FROM events WHERE id = ?'),
  insertEvent: db.prepare('INSERT INTO events (meet_id, no, judul, jarak, gaya) VALUES (@meet_id, @no, @judul, @jarak, @gaya)'),
  updateEvent: db.prepare('UPDATE events SET no=@no, judul=@judul, jarak=@jarak, gaya=@gaya WHERE id=@id'),
  deleteEvent: db.prepare('DELETE FROM events WHERE id = ?'),

  // Heats
  listHeats:   db.prepare('SELECT * FROM heats WHERE event_id = ? ORDER BY heat'),
  getHeat:     db.prepare('SELECT * FROM heats WHERE id = ?'),
  insertHeat:  db.prepare('INSERT INTO heats (event_id, heat, lintasan) VALUES (@event_id, @heat, @lintasan)'),
  updateHeat:  db.prepare('UPDATE heats SET heat=@heat, lintasan=@lintasan WHERE id=@id'),
  deleteHeat:  db.prepare('DELETE FROM heats WHERE id = ?'),

  // Entries
  listEntries:   db.prepare('SELECT * FROM entries WHERE heat_id = ? ORDER BY lane'),
  insertEntry:   db.prepare('INSERT INTO entries (heat_id, lane, name, club, country, seed) VALUES (@heat_id, @lane, @name, @club, @country, @seed)'),
  updateEntry:   db.prepare('UPDATE entries SET name=@name, club=@club, country=@country, seed=@seed WHERE id=@id'),
  deleteEntry:   db.prepare('DELETE FROM entries WHERE id = ?'),
  updateResult:  db.prepare('UPDATE entries SET result_time=@result_time, result_rank=@result_rank WHERE id=@id'),

  // Bulk delete entries for a heat before re-import
  clearHeatEntries: db.prepare('DELETE FROM entries WHERE heat_id = ?'),
};

// ─── Exported API ─────────────────────────────────────────────────────────────

module.exports = {
  // Meets
  listMeets:   ()     => stmts.listMeets.all(),
  getMeet:     (id)   => stmts.getMeet.get(id),
  createMeet:  (data) => {
    const info = stmts.insertMeet.run(data);
    return stmts.getMeet.get(info.lastInsertRowid);
  },
  updateMeet:  (id, data) => {
    stmts.updateMeet.run({ ...data, id });
    return stmts.getMeet.get(id);
  },
  deleteMeet:  (id)   => stmts.deleteMeet.run(id),

  // Events
  listEvents:  (meetId)     => stmts.listEvents.all(meetId),
  getEvent:    (id)         => stmts.getEvent.get(id),
  createEvent: (data)       => {
    const info = stmts.insertEvent.run(data);
    return stmts.getEvent.get(info.lastInsertRowid);
  },
  updateEvent: (id, data)   => { stmts.updateEvent.run({ ...data, id }); return stmts.getEvent.get(id); },
  deleteEvent: (id)         => stmts.deleteEvent.run(id),

  // Heats
  listHeats:   (eventId)    => stmts.listHeats.all(eventId),
  getHeat:     (id)         => stmts.getHeat.get(id),
  createHeat:  (data)       => {
    const info = stmts.insertHeat.run(data);
    return stmts.getHeat.get(info.lastInsertRowid);
  },
  updateHeat:  (id, data)   => { stmts.updateHeat.run({ ...data, id }); return stmts.getHeat.get(id); },
  deleteHeat:  (id)         => stmts.deleteHeat.run(id),

  // Entries
  listEntries:  (heatId)    => stmts.listEntries.all(heatId),
  createEntry:  (data)      => {
    const info = stmts.insertEntry.run(data);
    return { id: info.lastInsertRowid, ...data };
  },
  bulkImportEntries: (heatId, rows) => {
    db.exec('BEGIN');
    try {
      stmts.clearHeatEntries.run(heatId);
      for (const r of rows) stmts.insertEntry.run({ heat_id: heatId, ...r });
      db.exec('COMMIT');
    } catch (e) {
      db.exec('ROLLBACK');
      throw e;
    }
  },
  updateEntry:  (id, data)  => { stmts.updateEntry.run({ ...data, id }); },
  deleteEntry:  (id)        => stmts.deleteEntry.run(id),
  updateResult: (id, data)  => { stmts.updateResult.run({ ...data, id }); },

  // Helper – load full meet with nested events/heats/entries
  loadMeetFull: (meetId) => {
    const meet = stmts.getMeet.get(meetId);
    if (!meet) return null;
    meet.events = stmts.listEvents.all(meetId).map(ev => {
      ev.heats = stmts.listHeats.all(ev.id).map(h => {
        h.entries = stmts.listEntries.all(h.id);
        return h;
      });
      return ev;
    });
    return meet;
  },
};
