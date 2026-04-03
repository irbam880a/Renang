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

// ── Cleanup ───────────────────────────────────────────────────────────────────
process.on('exit', () => {
  try { fs.unlinkSync(TMP_DB); } catch (_) {}
});

// Close the HTTP server so the process exits cleanly after tests.
after(() => new Promise(resolve => server.close(resolve)));
