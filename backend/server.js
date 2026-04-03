'use strict';
const express  = require('express');
const path     = require('path');
const multer   = require('multer');
const ExcelJS  = require('exceljs');
const db       = require('./database');

const app    = express();
const upload = multer({ storage: multer.memoryStorage() });

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ─── Helpers ──────────────────────────────────────────────────────────────────

function ok(res, data)     { res.json({ ok: true, data }); }
function fail(res, msg, status = 400) { res.status(status).json({ ok: false, error: msg }); }

function intParam(v, min = 1, max = 9999) {
  const n = parseInt(v, 10);
  return !isNaN(n) && n >= min && n <= max ? n : null;
}

// ─── Meets ────────────────────────────────────────────────────────────────────

// GET  /api/meets
app.get('/api/meets', (req, res) => ok(res, db.listMeets()));

// POST /api/meets
app.post('/api/meets', (req, res) => {
  const { nama, jumlah_lintasan = 8, tanggal = '' } = req.body;
  if (!nama || !nama.trim()) return fail(res, 'nama diperlukan');
  const jl = intParam(jumlah_lintasan, 1, 16);
  if (!jl) return fail(res, 'jumlah_lintasan harus antara 1–16');
  ok(res, db.createMeet({ nama: nama.trim(), jumlah_lintasan: jl, tanggal: tanggal || null }));
});

// GET  /api/meets/:id
app.get('/api/meets/:id', (req, res) => {
  const meet = db.getMeet(req.params.id);
  if (!meet) return fail(res, 'Meet tidak ditemukan', 404);
  ok(res, meet);
});

// PUT  /api/meets/:id
app.put('/api/meets/:id', (req, res) => {
  const meet = db.getMeet(req.params.id);
  if (!meet) return fail(res, 'Meet tidak ditemukan', 404);
  const nama            = (req.body.nama || meet.nama).trim();
  const tanggal         = req.body.tanggal !== undefined ? req.body.tanggal : meet.tanggal;
  const jumlah_lintasan = req.body.jumlah_lintasan !== undefined
    ? intParam(req.body.jumlah_lintasan, 1, 16)
    : meet.jumlah_lintasan;
  if (!nama) return fail(res, 'nama diperlukan');
  if (!jumlah_lintasan) return fail(res, 'jumlah_lintasan harus antara 1–16');
  ok(res, db.updateMeet(req.params.id, { nama, jumlah_lintasan, tanggal }));
});

// DELETE /api/meets/:id
app.delete('/api/meets/:id', (req, res) => {
  if (!db.getMeet(req.params.id)) return fail(res, 'Meet tidak ditemukan', 404);
  db.deleteMeet(req.params.id);
  ok(res, null);
});

// GET /api/meets/:id/full  – nested events/heats/entries
app.get('/api/meets/:id/full', (req, res) => {
  const data = db.loadMeetFull(req.params.id);
  if (!data) return fail(res, 'Meet tidak ditemukan', 404);
  ok(res, data);
});

// ─── Events ───────────────────────────────────────────────────────────────────

// GET  /api/meets/:meetId/events
app.get('/api/meets/:meetId/events', (req, res) => {
  if (!db.getMeet(req.params.meetId)) return fail(res, 'Meet tidak ditemukan', 404);
  ok(res, db.listEvents(req.params.meetId));
});

// POST /api/meets/:meetId/events
app.post('/api/meets/:meetId/events', (req, res) => {
  const meet = db.getMeet(req.params.meetId);
  if (!meet) return fail(res, 'Meet tidak ditemukan', 404);
  const { no, judul = '', jarak = '', gaya = '' } = req.body;
  const n = intParam(no, 1);
  if (!n) return fail(res, 'no event diperlukan');
  ok(res, db.createEvent({ meet_id: meet.id, no: n, judul, jarak, gaya }));
});

// PUT  /api/events/:id
app.put('/api/events/:id', (req, res) => {
  const ev = db.getEvent(req.params.id);
  if (!ev) return fail(res, 'Event tidak ditemukan', 404);
  const no    = intParam(req.body.no ?? ev.no, 1) ?? ev.no;
  const judul = req.body.judul ?? ev.judul;
  const jarak = req.body.jarak ?? ev.jarak;
  const gaya  = req.body.gaya  ?? ev.gaya;
  ok(res, db.updateEvent(req.params.id, { no, judul, jarak, gaya }));
});

// DELETE /api/events/:id
app.delete('/api/events/:id', (req, res) => {
  if (!db.getEvent(req.params.id)) return fail(res, 'Event tidak ditemukan', 404);
  db.deleteEvent(req.params.id);
  ok(res, null);
});

// ─── Heats ────────────────────────────────────────────────────────────────────

// GET  /api/events/:eventId/heats
app.get('/api/events/:eventId/heats', (req, res) => {
  if (!db.getEvent(req.params.eventId)) return fail(res, 'Event tidak ditemukan', 404);
  ok(res, db.listHeats(req.params.eventId));
});

// POST /api/events/:eventId/heats
app.post('/api/events/:eventId/heats', (req, res) => {
  const ev = db.getEvent(req.params.eventId);
  if (!ev) return fail(res, 'Event tidak ditemukan', 404);
  const heat     = intParam(req.body.heat ?? 1, 1) ?? 1;
  const lintasan = intParam(req.body.lintasan, 1, 16);
  ok(res, db.createHeat({ event_id: ev.id, heat, lintasan: lintasan || null }));
});

// PUT  /api/heats/:id
app.put('/api/heats/:id', (req, res) => {
  const h = db.getHeat(req.params.id);
  if (!h) return fail(res, 'Heat tidak ditemukan', 404);
  const heat     = intParam(req.body.heat ?? h.heat, 1) ?? h.heat;
  const lintasan = req.body.lintasan !== undefined
    ? (intParam(req.body.lintasan, 1, 16) || null)
    : h.lintasan;
  ok(res, db.updateHeat(req.params.id, { heat, lintasan }));
});

// DELETE /api/heats/:id
app.delete('/api/heats/:id', (req, res) => {
  if (!db.getHeat(req.params.id)) return fail(res, 'Heat tidak ditemukan', 404);
  db.deleteHeat(req.params.id);
  ok(res, null);
});

// ─── Entries ──────────────────────────────────────────────────────────────────

// GET  /api/heats/:heatId/entries
app.get('/api/heats/:heatId/entries', (req, res) => {
  if (!db.getHeat(req.params.heatId)) return fail(res, 'Heat tidak ditemukan', 404);
  ok(res, db.listEntries(req.params.heatId));
});

// POST /api/heats/:heatId/entries  – single entry
app.post('/api/heats/:heatId/entries', (req, res) => {
  const heat = db.getHeat(req.params.heatId);
  if (!heat) return fail(res, 'Heat tidak ditemukan', 404);
  const lane = intParam(req.body.lane, 1, 16);
  if (!lane) return fail(res, 'lane harus antara 1–16');
  ok(res, db.createEntry({
    heat_id: heat.id,
    lane,
    name:    (req.body.name    || '').trim(),
    club:    (req.body.club    || '').trim(),
    country: (req.body.country || '').trim(),
    seed:    (req.body.seed    || '').trim(),
  }));
});

// POST /api/heats/:heatId/entries/import  – bulk from Excel
app.post('/api/heats/:heatId/entries/import', upload.single('file'), async (req, res) => {
  const heat = db.getHeat(req.params.heatId);
  if (!heat) return fail(res, 'Heat tidak ditemukan', 404);
  if (!req.file) return fail(res, 'File diperlukan');

  try {
    const wb = new ExcelJS.Workbook();
    await wb.xlsx.load(req.file.buffer);
    const ws = wb.worksheets[0];
    if (!ws) return fail(res, 'Sheet tidak ditemukan dalam file');

    // Detect header row (first row)
    const headerRow = ws.getRow(1).values; // 1-based index, index 0 is undefined
    const headers = {};
    headerRow.forEach((h, i) => {
      if (h) headers[String(h).toLowerCase().trim()] = i;
    });

    const colIdx = (names) => {
      for (const n of names) if (headers[n] !== undefined) return headers[n];
      return null;
    };

    const laneCol    = colIdx(['lane']);
    const nameCol    = colIdx(['name', 'nama']);
    const clubCol    = colIdx(['club', 'klub']);
    const countryCol = colIdx(['country', 'negara']);
    const seedCol    = colIdx(['seed', 'seed time']);

    if (laneCol === null) return fail(res, 'Kolom "Lane" tidak ditemukan dalam file');

    const entries = [];
    ws.eachRow((row, rowNum) => {
      if (rowNum === 1) return; // skip header
      const lane = intParam(row.getCell(laneCol).value, 1, 16);
      if (!lane) return;
      entries.push({
        lane,
        name:    String(nameCol    !== null ? (row.getCell(nameCol).value    || '') : '').trim(),
        club:    String(clubCol    !== null ? (row.getCell(clubCol).value    || '') : '').trim(),
        country: String(countryCol !== null ? (row.getCell(countryCol).value || '') : '').trim(),
        seed:    String(seedCol    !== null ? (row.getCell(seedCol).value    || '') : '').trim(),
      });
    });

    db.bulkImportEntries(heat.id, entries);
    ok(res, db.listEntries(heat.id));
  } catch (e) {
    fail(res, 'Gagal membaca file Excel: ' + e.message);
  }
});

// PUT  /api/entries/:id
app.put('/api/entries/:id', (req, res) => {
  const { name = '', club = '', country = '', seed = '' } = req.body;
  db.updateEntry(req.params.id, { name, club, country, seed });
  ok(res, null);
});

// DELETE /api/entries/:id
app.delete('/api/entries/:id', (req, res) => {
  db.deleteEntry(req.params.id);
  ok(res, null);
});

// ─── Excel template download ──────────────────────────────────────────────────

app.get('/api/template-entries', async (req, res) => {
  const jumlah = intParam(req.query.jumlah, 1, 16) || 8;
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet('Entries');
  ws.addRow(['Lane', 'Name', 'Club', 'Country', 'Seed']);
  for (let i = 1; i <= jumlah; i++) ws.addRow([i, '', '', '', '']);
  res.setHeader('Content-Disposition', 'attachment; filename="template-entries.xlsx"');
  res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
  await wb.xlsx.write(res);
  res.end();
});

// ─── Excel export – current heat entries ────────────────────────────────────

app.get('/api/heats/:heatId/export', async (req, res) => {
  const heat = db.getHeat(req.params.heatId);
  if (!heat) return fail(res, 'Heat tidak ditemukan', 404);
  const entries = db.listEntries(heat.id);
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet('Heat');
  ws.addRow(['Lane', 'Name', 'Club', 'Country', 'Seed', 'Result Time', 'Rank']);
  entries.forEach(e => ws.addRow([e.lane, e.name, e.club, e.country, e.seed, e.result_time, e.result_rank]));
  res.setHeader('Content-Disposition', `attachment; filename="heat-${heat.id}.xlsx"`);
  res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
  await wb.xlsx.write(res);
  res.end();
});

// ─── Start ────────────────────────────────────────────────────────────────────

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Renang Pro running at http://localhost:${PORT}`));
