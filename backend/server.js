'use strict';

/**
 * server.js
 * ---------
 * Express REST API + static dashboard for the 16-lane ESP32 swimming timer.
 *
 * Endpoints
 * ─────────
 * POST /api/start          { heat, acara?, seri?, nomor?, gaya?, gender?, kategori?, nama_lomba?, tanggal_lomba? }
 * POST /api/finish         { lane, elapsedMs }
 * POST /api/reset          {}
 * GET  /api/results        → active race results (race + lanes + entries)
 * GET  /api/races          → all historical races
 * GET  /api/race/:id       → specific race results
 * PUT  /api/race/:id/meta  { acara, seri, nomor, gaya, gender, kategori, nama_lomba, tanggal_lomba }
 * POST /api/entry          { lane, nama_atlet, klub, limid_waktu }   (single, active race)
 * POST /api/entries        { race_id?, entries: [{lane, nama_atlet, klub, limid_waktu}] }
 * GET  /                   → HTML dashboard
 */

const express = require('express');
const path    = require('path');
const db      = require('./database');

const app  = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ── Helper: extract meta fields from request body ─────────────────────────────
function metaFrom(body) {
  return {
    acara:         body.acara         ?? null,
    seri:          body.seri          ?? null,
    nomor:         body.nomor         ?? null,
    gaya:          body.gaya          ?? null,
    gender:        body.gender        ?? null,
    kategori:      body.kategori      ?? null,
    nama_lomba:    body.nama_lomba    ?? null,
    tanggal_lomba: body.tanggal_lomba ?? null,
  };
}

// ── POST /api/start ───────────────────────────────────────────────────────────
app.post('/api/start', (req, res) => {
  const heat = parseInt(req.body.heat, 10);
  if (!heat || heat < 1 || heat > 2) {
    return res.status(400).json({ error: 'heat must be 1 or 2' });
  }

  const startedAt = req.body.startMillis ? Number(req.body.startMillis) : Date.now();
  const race = db.startRace(heat, startedAt, metaFrom(req.body));
  console.log(`[START] heat=${heat} race_id=${race.id}`);
  res.json({ ok: true, race });
});

// ── POST /api/finish ──────────────────────────────────────────────────────────
app.post('/api/finish', (req, res) => {
  const lane      = parseInt(req.body.lane, 10);
  const elapsedMs = parseInt(req.body.elapsedMs, 10);

  if (!lane || lane < 1 || lane > 16) {
    return res.status(400).json({ error: 'lane must be between 1 and 16' });
  }
  if (isNaN(elapsedMs) || elapsedMs < 0) {
    return res.status(400).json({ error: 'elapsedMs must be a non-negative number' });
  }

  const record = db.recordFinish(lane, elapsedMs);
  if (!record) {
    return res.status(409).json({ error: 'No active race. Press START first.' });
  }

  console.log(`[FINISH] lane=${lane} elapsed=${elapsedMs}ms`);
  res.json({ ok: true, record });
});

// ── POST /api/reset ───────────────────────────────────────────────────────────
app.post('/api/reset', (req, res) => {
  const race = db.resetRace();
  console.log(`[RESET] race_id=${race ? race.id : 'none'}`);
  res.json({ ok: true, resetRace: race });
});

// ── GET /api/results ──────────────────────────────────────────────────────────
app.get('/api/results', (req, res) => {
  const data = db.getResults();
  if (!data) {
    return res.json({ race: null, lanes: [], entries: {} });
  }
  res.json(data);
});

// ── GET /api/races ────────────────────────────────────────────────────────────
app.get('/api/races', (req, res) => {
  res.json(db.getAllRaces());
});

// ── GET /api/race/:id ─────────────────────────────────────────────────────────
app.get('/api/race/:id', (req, res) => {
  const data = db.getResults(parseInt(req.params.id, 10));
  if (!data) return res.status(404).json({ error: 'Race not found' });
  res.json(data);
});

// ── PUT /api/race/:id/meta ────────────────────────────────────────────────────
app.put('/api/race/:id/meta', (req, res) => {
  const raceId = parseInt(req.params.id, 10);
  const race   = db.updateRaceMeta(raceId, metaFrom(req.body));
  if (!race) return res.status(404).json({ error: 'Race not found' });
  console.log(`[META] race_id=${raceId} acara=${race.acara} seri=${race.seri}`);
  res.json({ ok: true, race });
});

// ── POST /api/entry ───────────────────────────────────────────────────────────
// Set one athlete entry for a lane in the active race.
app.post('/api/entry', (req, res) => {
  const race = db.getActiveRace();
  if (!race) return res.status(409).json({ error: 'No active race' });

  const lane = parseInt(req.body.lane, 10);
  if (!lane || lane < 1 || lane > 16) {
    return res.status(400).json({ error: 'lane must be between 1 and 16' });
  }

  const entry = db.setLaneEntry(race.id, lane, req.body.nama_atlet, req.body.klub, req.body.limid_waktu);
  res.json({ ok: true, entry });
});

// ── POST /api/entries ─────────────────────────────────────────────────────────
// Batch-set lane entries.  race_id is optional; defaults to active race.
app.post('/api/entries', (req, res) => {
  const raceId = req.body.race_id
    ? parseInt(req.body.race_id, 10)
    : db.getActiveRace()?.id;
  if (!raceId) return res.status(409).json({ error: 'No active race' });

  const items   = Array.isArray(req.body.entries) ? req.body.entries : [];
  const results = [];
  for (const item of items) {
    const lane = parseInt(item.lane, 10);
    if (lane >= 1 && lane <= 16) {
      results.push(db.setLaneEntry(raceId, lane, item.nama_atlet, item.klub, item.limid_waktu));
    }
  }
  console.log(`[ENTRIES] race_id=${raceId} count=${results.length}`);
  res.json({ ok: true, entries: results });
});

// ── Start server ──────────────────────────────────────────────────────────────
const server = app.listen(PORT, () => {
  console.log(`Swimming Timer server running on http://0.0.0.0:${PORT}`);
});

module.exports = { app, server };  // exported for testing
