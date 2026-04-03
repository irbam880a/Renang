'use strict';

/**
 * tests/api.test.js
 * -----------------
 * Node.js built-in test runner tests for the swimming-timer API.
 * Uses a temporary in-memory-style database (separate file per test run).
 *
 * Run:  node --test tests/
 */

const test   = require('node:test');
const { after } = test;
const assert = require('node:assert/strict');
const http   = require('node:http');
const path   = require('node:path');
const fs     = require('node:fs');
const os     = require('node:os');

// ── Isolate DB ────────────────────────────────────────────────────────────────
const TMP_DB = path.join(os.tmpdir(), `swimming_timer_test_${Date.now()}.db`);
process.env.DB_PATH = TMP_DB;

// Require server AFTER setting DB_PATH so it picks up the temp DB.
const { app, server } = require('../server');

// ── Helper: make a JSON HTTP request to the Express app ──────────────────────
function request(method, urlPath, body) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : '';
    const options = {
      hostname: '127.0.0.1',
      port: 3000,
      path: urlPath,
      method,
      headers: {
        'Content-Type':   'application/json',
        'Content-Length': Buffer.byteLength(data)
      }
    };

    const req = http.request(options, res => {
      let raw = '';
      res.on('data', chunk => { raw += chunk; });
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(raw) }); }
        catch (e) { resolve({ status: res.statusCode, body: raw }); }
      });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

// ── Wait for server to be ready ───────────────────────────────────────────────
function waitForServer(port, retries = 20) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    function tryConnect() {
      const req = http.request({ hostname: '127.0.0.1', port, path: '/api/results', method: 'GET' }, res => {
        res.resume();
        resolve();
      });
      req.on('error', () => {
        if (++attempts >= retries) return reject(new Error('Server did not start'));
        setTimeout(tryConnect, 200);
      });
      req.end();
    }
    tryConnect();
  });
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test('GET /api/results returns empty when no race', async () => {
  await waitForServer(3000);
  const { status, body } = await request('GET', '/api/results', null);
  assert.equal(status, 200);
  assert.equal(body.race, null);
  assert.deepEqual(body.lanes, []);
});

test('POST /api/start with heat=1 creates a race', async () => {
  const { status, body } = await request('POST', '/api/start', { heat: 1 });
  assert.equal(status, 200);
  assert.equal(body.ok, true);
  assert.equal(body.race.heat, 1);
  assert.equal(body.race.active, 1);
});

test('POST /api/start with invalid heat returns 400', async () => {
  const { status } = await request('POST', '/api/start', { heat: 5 });
  assert.equal(status, 400);
});

test('POST /api/finish records a lane time', async () => {
  // Ensure a race is active
  await request('POST', '/api/start', { heat: 1 });

  const { status, body } = await request('POST', '/api/finish', { lane: 3, elapsedMs: 62500 });
  assert.equal(status, 200);
  assert.equal(body.ok, true);
  assert.equal(body.record.lane, 3);
  assert.equal(body.record.elapsed_ms, 62500);
});

test('POST /api/finish with invalid lane returns 400', async () => {
  const { status } = await request('POST', '/api/finish', { lane: 17, elapsedMs: 1000 });
  assert.equal(status, 400);
});

test('POST /api/finish with negative elapsedMs returns 400', async () => {
  const { status } = await request('POST', '/api/finish', { lane: 1, elapsedMs: -1 });
  assert.equal(status, 400);
});

test('GET /api/results returns lane times for active race', async () => {
  await request('POST', '/api/start', { heat: 2 });
  await request('POST', '/api/finish', { lane: 1, elapsedMs: 55000 });
  await request('POST', '/api/finish', { lane: 2, elapsedMs: 57000 });

  const { status, body } = await request('GET', '/api/results');
  assert.equal(status, 200);
  assert.ok(body.race);
  assert.equal(body.race.heat, 2);
  assert.equal(body.lanes.length, 2);
  // lanes are ordered by elapsed_ms ascending → lane 1 first
  assert.equal(body.lanes[0].lane, 1);
  assert.equal(body.lanes[1].lane, 2);
});

test('POST /api/reset clears active race', async () => {
  await request('POST', '/api/start', { heat: 1 });
  await request('POST', '/api/finish', { lane: 5, elapsedMs: 70000 });

  const { status, body } = await request('POST', '/api/reset', {});
  assert.equal(status, 200);
  assert.equal(body.ok, true);

  const { body: results } = await request('GET', '/api/results');
  assert.equal(results.race, null);
  assert.deepEqual(results.lanes, []);
});

test('POST /api/finish after reset returns 409', async () => {
  // No active race
  await request('POST', '/api/reset', {});
  const { status } = await request('POST', '/api/finish', { lane: 1, elapsedMs: 1000 });
  assert.equal(status, 409);
});

test('GET /api/races returns historical races', async () => {
  const { status, body } = await request('GET', '/api/races');
  assert.equal(status, 200);
  assert.ok(Array.isArray(body));
});

test('All 16 lanes can record finish times', async () => {
  await request('POST', '/api/start', { heat: 1 });

  for (let lane = 1; lane <= 16; lane++) {
    const { status, body } = await request('POST', '/api/finish', {
      lane,
      elapsedMs: lane * 1000
    });
    assert.equal(status, 200, `Lane ${lane} should record successfully`);
    assert.equal(body.record.lane, lane);
  }

  const { body: results } = await request('GET', '/api/results');
  assert.equal(results.lanes.length, 16);
});

// ── New metadata & entry endpoint tests ──────────────────────────────────────

test('POST /api/start with metadata stores race fields', async () => {
  const { status, body } = await request('POST', '/api/start', {
    heat: 1,
    acara: '3',
    seri: '1',
    nomor: '50',
    gaya: 'Dada',
    gender: 'Putra',
    kategori: '2007-2008',
    nama_lomba: 'KEJURKAB 2024',
    tanggal_lomba: '30 November 2024',
  });
  assert.equal(status, 200);
  assert.equal(body.race.acara, '3');
  assert.equal(body.race.seri, '1');
  assert.equal(body.race.nomor, '50');
  assert.equal(body.race.gaya, 'Dada');
  assert.equal(body.race.gender, 'Putra');
  assert.equal(body.race.kategori, '2007-2008');
  assert.equal(body.race.nama_lomba, 'KEJURKAB 2024');
});

test('GET /api/results includes entries field', async () => {
  const { body } = await request('GET', '/api/results');
  assert.ok(body.race);
  assert.ok(typeof body.entries === 'object');
});

test('PUT /api/race/:id/meta updates race metadata', async () => {
  const { body: startBody } = await request('POST', '/api/start', { heat: 1 });
  const raceId = startBody.race.id;

  const { status, body } = await request('PUT', `/api/race/${raceId}/meta`, {
    acara: '5',
    seri: '2',
    nomor: '100',
    gaya: 'Bebas',
    gender: 'Putri',
    nama_lomba: 'LOMBA TEST',
    tanggal_lomba: '01 Jan 2025',
  });
  assert.equal(status, 200);
  assert.equal(body.race.acara, '5');
  assert.equal(body.race.gaya, 'Bebas');
  assert.equal(body.race.gender, 'Putri');
});

test('PUT /api/race/:id/meta on missing race returns 404', async () => {
  const { status } = await request('PUT', '/api/race/999999/meta', { acara: 'X' });
  assert.equal(status, 404);
});

test('GET /api/race/:id returns specific race', async () => {
  const { body: startBody } = await request('POST', '/api/start', { heat: 2 });
  const raceId = startBody.race.id;
  await request('POST', '/api/finish', { lane: 4, elapsedMs: 45000 });

  const { status, body } = await request('GET', `/api/race/${raceId}`);
  assert.equal(status, 200);
  assert.equal(body.race.id, raceId);
  assert.equal(body.lanes.length, 1);
  assert.equal(body.lanes[0].lane, 4);
});

test('GET /api/race/:id on missing race returns 404', async () => {
  const { status } = await request('GET', '/api/race/999999');
  assert.equal(status, 404);
});

test('POST /api/entry sets athlete for a lane', async () => {
  await request('POST', '/api/start', { heat: 1 });

  const { status, body } = await request('POST', '/api/entry', {
    lane: 7,
    nama_atlet: 'Ahmad Fulan',
    klub: 'SMPN 1 Genteng',
    limid_waktu: '00:32.50',
  });
  assert.equal(status, 200);
  assert.equal(body.entry.lane, 7);
  assert.equal(body.entry.nama_atlet, 'Ahmad Fulan');
  assert.equal(body.entry.klub, 'SMPN 1 Genteng');
});

test('POST /api/entry updates existing entry (UPSERT)', async () => {
  // Second call for same lane should update, not error
  const { status, body } = await request('POST', '/api/entry', {
    lane: 7,
    nama_atlet: 'Ahmad Updated',
    klub: 'SMAN 2 Banyuwangi',
  });
  assert.equal(status, 200);
  assert.equal(body.entry.nama_atlet, 'Ahmad Updated');
});

test('POST /api/entry with invalid lane returns 400', async () => {
  const { status } = await request('POST', '/api/entry', { lane: 0, nama_atlet: 'X' });
  assert.equal(status, 400);
});

test('POST /api/entry without active race returns 409', async () => {
  await request('POST', '/api/reset', {});
  const { status } = await request('POST', '/api/entry', { lane: 1, nama_atlet: 'X' });
  assert.equal(status, 409);
});

test('POST /api/entries batch-sets lane entries', async () => {
  await request('POST', '/api/start', { heat: 1 });

  const entries = [
    { lane: 1, nama_atlet: 'Budi', klub: 'SMPN 1', limid_waktu: '00:30.00' },
    { lane: 2, nama_atlet: 'Citra', klub: 'SMAN 2', limid_waktu: '00:31.00' },
    { lane: 3, nama_atlet: 'Dewi', klub: 'SMPN 3', limid_waktu: '00:32.00' },
  ];

  const { status, body } = await request('POST', '/api/entries', { entries });
  assert.equal(status, 200);
  assert.equal(body.entries.length, 3);

  // Verify entries are returned in GET /api/results
  const { body: results } = await request('GET', '/api/results');
  assert.ok(results.entries[1]);
  assert.equal(results.entries[1].nama_atlet, 'Budi');
  assert.equal(results.entries[2].nama_atlet, 'Citra');
});

test('GET /api/races includes entries per race', async () => {
  const { body } = await request('GET', '/api/races');
  assert.ok(Array.isArray(body));
  // Every race object should have an entries field
  body.forEach(race => {
    assert.ok(typeof race.entries === 'object', `race ${race.id} should have entries`);
  });
});

// ── Cleanup ───────────────────────────────────────────────────────────────────
process.on('exit', () => {
  try { fs.unlinkSync(TMP_DB); } catch (_) {}
});

// Close the HTTP server so the process exits cleanly after tests.
after(() => new Promise(resolve => server.close(resolve)));
