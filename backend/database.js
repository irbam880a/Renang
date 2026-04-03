'use strict';

/**
 * database.js
 * -----------
 * Thin wrapper around node:sqlite (built-in, Node.js ≥ 22.5) for the
 * swimming timer.
 *
 * Schema
 * ──────
 * races        – one row per heat/race started
 * lane_times   – one row per lane finish event (foreign key → races)
 * lane_entries – athlete registration per lane per race
 */

const { DatabaseSync } = require('node:sqlite');
const path = require('path');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, 'swimming_timer.db');

let db;

function getDb() {
  if (!db) {
    db = new DatabaseSync(DB_PATH);
    db.exec('PRAGMA journal_mode = WAL');
    db.exec('PRAGMA foreign_keys = ON');
    init(db);
  }
  return db;
}

/** Add a column to a table only if it does not already exist. */
function addColumnIfNotExists(database, table, column, definition) {
  try {
    database.exec(`ALTER TABLE "${table}" ADD COLUMN ${column} ${definition}`);
  } catch (_) { /* column already exists – safe to ignore */ }
}

function init(database) {
  database.exec(`
    CREATE TABLE IF NOT EXISTS races (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      heat          INTEGER NOT NULL DEFAULT 1,
      started_at    INTEGER NOT NULL,
      reset_at      INTEGER,
      active        INTEGER NOT NULL DEFAULT 1,
      acara         TEXT,
      seri          TEXT,
      nomor         TEXT,
      gaya          TEXT,
      gender        TEXT DEFAULT 'Putra',
      kategori      TEXT,
      nama_lomba    TEXT,
      tanggal_lomba TEXT
    );

    CREATE TABLE IF NOT EXISTS lane_times (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      race_id     INTEGER NOT NULL REFERENCES races(id) ON DELETE CASCADE,
      lane        INTEGER NOT NULL CHECK(lane BETWEEN 1 AND 16),
      elapsed_ms  INTEGER NOT NULL,
      recorded_at INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS lane_entries (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      race_id     INTEGER NOT NULL REFERENCES races(id) ON DELETE CASCADE,
      lane        INTEGER NOT NULL CHECK(lane BETWEEN 1 AND 16),
      nama_atlet  TEXT,
      klub        TEXT,
      limid_waktu TEXT,
      UNIQUE(race_id, lane)
    );

    CREATE INDEX IF NOT EXISTS idx_lane_times_race_id   ON lane_times(race_id);
    CREATE INDEX IF NOT EXISTS idx_lane_entries_race_id ON lane_entries(race_id);
  `);

  // Migrate existing races table – add columns that may be missing in older DBs
  const newCols = [
    ['acara',         'TEXT'],
    ['seri',          'TEXT'],
    ['nomor',         'TEXT'],
    ['gaya',          'TEXT'],
    ['gender',        "TEXT DEFAULT 'Putra'"],
    ['kategori',      'TEXT'],
    ['nama_lomba',    'TEXT'],
    ['tanggal_lomba', 'TEXT'],
  ];
  for (const [col, def] of newCols) {
    addColumnIfNotExists(database, 'races', col, def);
  }
}

// ── Race helpers ──────────────────────────────────────────────────────────────

/**
 * Create a new active race.  Any existing active race is closed first.
 * Returns the new race row.
 */
function startRace(heat, startedAt, meta = {}) {
  const database = getDb();
  database.prepare('UPDATE races SET active = 0 WHERE active = 1').run();

  const info = database.prepare(`
    INSERT INTO races
      (heat, started_at, active, acara, seri, nomor, gaya, gender, kategori, nama_lomba, tanggal_lomba)
    VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    heat, startedAt,
    meta.acara         ?? null,
    meta.seri          ?? null,
    meta.nomor         ?? null,
    meta.gaya          ?? null,
    meta.gender        ?? null,
    meta.kategori      ?? null,
    meta.nama_lomba    ?? null,
    meta.tanggal_lomba ?? null
  );

  return database.prepare('SELECT * FROM races WHERE id = ?').get(info.lastInsertRowid);
}

/**
 * Returns the current active race, or null.
 */
function getActiveRace() {
  return getDb().prepare('SELECT * FROM races WHERE active = 1').get() ?? null;
}

/**
 * Update metadata fields of an existing race row.
 * Returns the updated row, or null if not found.
 */
function updateRaceMeta(raceId, meta) {
  const database = getDb();
  database.prepare(`
    UPDATE races
    SET acara=?, seri=?, nomor=?, gaya=?, gender=?, kategori=?, nama_lomba=?, tanggal_lomba=?
    WHERE id=?
  `).run(
    meta.acara         ?? null,
    meta.seri          ?? null,
    meta.nomor         ?? null,
    meta.gaya          ?? null,
    meta.gender        ?? null,
    meta.kategori      ?? null,
    meta.nama_lomba    ?? null,
    meta.tanggal_lomba ?? null,
    raceId
  );
  return database.prepare('SELECT * FROM races WHERE id = ?').get(raceId) ?? null;
}

/**
 * Create or update a lane_entries row (UPSERT).
 * Returns the resulting row.
 */
function setLaneEntry(raceId, lane, namaAtlet, klub, limidWaktu) {
  const database = getDb();
  database.prepare(`
    INSERT INTO lane_entries (race_id, lane, nama_atlet, klub, limid_waktu)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(race_id, lane) DO UPDATE SET
      nama_atlet  = excluded.nama_atlet,
      klub        = excluded.klub,
      limid_waktu = excluded.limid_waktu
  `).run(raceId, lane, namaAtlet ?? null, klub ?? null, limidWaktu ?? null);

  return database.prepare(
    'SELECT * FROM lane_entries WHERE race_id = ? AND lane = ?'
  ).get(raceId, lane);
}

/**
 * Return all lane_entries for a race, keyed by lane number.
 */
function getLaneEntries(raceId) {
  const rows = getDb().prepare(
    'SELECT lane, nama_atlet, klub, limid_waktu FROM lane_entries WHERE race_id = ? ORDER BY lane ASC'
  ).all(raceId);
  const map = {};
  rows.forEach(r => { map[r.lane] = r; });
  return map;
}

/**
 * Record a lane finish time on the active race.
 * Returns the inserted row, or null if no active race.
 */
function recordFinish(lane, elapsedMs) {
  const database = getDb();
  const race = getActiveRace();
  if (!race) return null;

  const now = Date.now();
  const info = database.prepare(
    'INSERT INTO lane_times (race_id, lane, elapsed_ms, recorded_at) VALUES (?, ?, ?, ?)'
  ).run(race.id, lane, elapsedMs, now);

  return database.prepare('SELECT * FROM lane_times WHERE id = ?').get(info.lastInsertRowid);
}

/**
 * Reset: mark active race as reset, delete its lane_times, and return the race.
 */
function resetRace() {
  const database = getDb();
  const race = getActiveRace();
  if (!race) return null;

  const now = Date.now();
  database.prepare('DELETE FROM lane_times WHERE race_id = ?').run(race.id);
  database.prepare('UPDATE races SET active = 0, reset_at = ? WHERE id = ?').run(now, race.id);

  return race;
}

/**
 * Get full results for the active race (or a specific race by id).
 * Returns { race, lanes, entries } or null.
 */
function getResults(raceId) {
  const database = getDb();
  const race = raceId
    ? database.prepare('SELECT * FROM races WHERE id = ?').get(raceId)
    : getActiveRace();

  if (!race) return null;

  const lanes = database.prepare(
    'SELECT lane, elapsed_ms, recorded_at FROM lane_times WHERE race_id = ? ORDER BY elapsed_ms ASC'
  ).all(race.id);

  const entries = getLaneEntries(race.id);

  return { race, lanes, entries };
}

/**
 * Get all historical races with their lane times and entries.
 */
function getAllRaces() {
  const database = getDb();
  const races = database.prepare('SELECT * FROM races ORDER BY id DESC').all();

  return races.map(race => {
    const lanes = database.prepare(
      'SELECT lane, elapsed_ms FROM lane_times WHERE race_id = ? ORDER BY elapsed_ms ASC'
    ).all(race.id);
    const entries = getLaneEntries(race.id);
    return { ...race, lanes, entries };
  });
}

module.exports = {
  startRace, getActiveRace, recordFinish, resetRace,
  getResults, getAllRaces,
  updateRaceMeta, setLaneEntry, getLaneEntries,
  getDb,
};
