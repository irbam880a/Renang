'use strict';

/**
 * database.js
 * -----------
 * Thin wrapper around node:sqlite (built-in, Node.js ≥ 22.5) for the
 * swimming timer.
 *
 * Schema
 * ──────
 * races      – one row per heat/race started
 * lane_times – one row per lane finish event (foreign key → races)
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

function init(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS races (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      heat       INTEGER NOT NULL DEFAULT 1,
      started_at INTEGER NOT NULL,          -- Unix ms (from ESP32 millis or server time)
      reset_at   INTEGER,                   -- Unix ms when reset was called
      active     INTEGER NOT NULL DEFAULT 1 -- 1 = current race, 0 = finished/reset
    );

    CREATE TABLE IF NOT EXISTS lane_times (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      race_id     INTEGER NOT NULL REFERENCES races(id) ON DELETE CASCADE,
      lane        INTEGER NOT NULL CHECK(lane BETWEEN 1 AND 16),
      elapsed_ms  INTEGER NOT NULL,          -- milliseconds from race start
      recorded_at INTEGER NOT NULL           -- server Unix ms
    );

    CREATE INDEX IF NOT EXISTS idx_lane_times_race_id ON lane_times(race_id);
  `);
}

// ── Race helpers ──────────────────────────────────────────────────────────────

/**
 * Create (or re-use) an active race for the given heat.
 * Returns the race row.
 */
function startRace(heat, startedAt) {
  const db = getDb();

  // Mark any existing active race as finished first
  db.prepare('UPDATE races SET active = 0 WHERE active = 1').run();

  const info = db.prepare(
    'INSERT INTO races (heat, started_at, active) VALUES (?, ?, 1)'
  ).run(heat, startedAt);

  return db.prepare('SELECT * FROM races WHERE id = ?').get(info.lastInsertRowid);
}

/**
 * Returns the current active race, or null.
 */
function getActiveRace() {
  return getDb().prepare('SELECT * FROM races WHERE active = 1').get() ?? null;
}

/**
 * Record a lane finish time on the active race.
 * Returns the inserted row, or null if no active race.
 */
function recordFinish(lane, elapsedMs) {
  const db = getDb();
  const race = getActiveRace();
  if (!race) return null;

  const now = Date.now();
  const info = db.prepare(
    'INSERT INTO lane_times (race_id, lane, elapsed_ms, recorded_at) VALUES (?, ?, ?, ?)'
  ).run(race.id, lane, elapsedMs, now);

  return db.prepare('SELECT * FROM lane_times WHERE id = ?').get(info.lastInsertRowid);
}

/**
 * Reset: mark active race as reset, delete its lane_times, and return the race.
 */
function resetRace() {
  const db = getDb();
  const race = getActiveRace();
  if (!race) return null;

  const now = Date.now();
  db.prepare('DELETE FROM lane_times WHERE race_id = ?').run(race.id);
  db.prepare('UPDATE races SET active = 0, reset_at = ? WHERE id = ?').run(now, race.id);

  return race;
}

/**
 * Get full results for the active race (or a specific race by id).
 */
function getResults(raceId) {
  const db = getDb();
  const race = raceId
    ? db.prepare('SELECT * FROM races WHERE id = ?').get(raceId)
    : getActiveRace();

  if (!race) return null;

  const lanes = db.prepare(
    'SELECT lane, elapsed_ms, recorded_at FROM lane_times WHERE race_id = ? ORDER BY elapsed_ms ASC'
  ).all(race.id);

  return { race, lanes };
}

/**
 * Get all historical races with their lane times.
 */
function getAllRaces() {
  const db = getDb();
  const races = db.prepare('SELECT * FROM races ORDER BY id DESC').all();

  return races.map(race => {
    const lanes = db.prepare(
      'SELECT lane, elapsed_ms FROM lane_times WHERE race_id = ? ORDER BY elapsed_ms ASC'
    ).all(race.id);
    return { ...race, lanes };
  });
}

module.exports = { startRace, getActiveRace, recordFinish, resetRace, getResults, getAllRaces, getDb };
