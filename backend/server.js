'use strict';

/**
 * server.js
 * ---------
 * Express REST API + static dashboard for the 16-lane ESP32 swimming timer.
 *
 * Endpoints
 * ─────────
 * POST /api/start   { heat: 1|2, startMillis?: number }  → start/restart a race
 * POST /api/finish  { lane: 1-16, heat: number, elapsedMs: number }  → record finish
 * POST /api/reset   {}  → reset the active race
 * GET  /api/results → current active race results
 * GET  /api/races   → all historical races
 * GET  /            → HTML dashboard
 */

const express = require('express');
const path    = require('path');
const db      = require('./database');

const app  = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ── POST /api/start ───────────────────────────────────────────────────────────
app.post('/api/start', (req, res) => {
  const heat = parseInt(req.body.heat, 10);
  if (!heat || heat < 1 || heat > 2) {
    return res.status(400).json({ error: 'heat must be 1 or 2' });
  }

  const startedAt = req.body.startMillis ? Number(req.body.startMillis) : Date.now();
  const race = db.startRace(heat, startedAt);
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
    return res.json({ race: null, lanes: [] });
  }
  res.json(data);
});

// ── GET /api/races ────────────────────────────────────────────────────────────
app.get('/api/races', (req, res) => {
  res.json(db.getAllRaces());
});

// ── Start server ──────────────────────────────────────────────────────────────
const server = app.listen(PORT, () => {
  console.log(`Swimming Timer server running on http://0.0.0.0:${PORT}`);
});

module.exports = { app, server };  // exported for testing
