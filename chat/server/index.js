import express from "express";
import cors from "cors";
import Database from "better-sqlite3";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const serverPort = Number(process.env.CHAT_API_PORT || 5174);
const databasePath = path.resolve(__dirname, "../../database/signals.db");
const MAX_LIMIT = 500;

app.use(cors());

const getSignals = (limit, offset) => {
  const db = new Database(databasePath, {
    readonly: true,
    fileMustExist: true,
  });
  db.pragma("busy_timeout = 3000");

  try {
    const stmt = db.prepare(`
      SELECT 
        id,
        timestamp,
        symbol,
        price,
        change_pct,
        tr_atr,
        z_score,
        signal_type,
        asset_class
      FROM signals
      ORDER BY datetime(timestamp) DESC
      LIMIT ? OFFSET ?
    `);

    const rows = stmt.all(limit, offset);
    return rows;
  } finally {
    db.close();
  }
};

app.get("/api/signals", (req, res) => {
  const limitParam = parseInt(req.query.limit, 10);
  const offsetParam = parseInt(req.query.offset, 10);

  const limit = Number.isFinite(limitParam)
    ? Math.min(Math.max(limitParam, 1), MAX_LIMIT)
    : 100;
  const offset = Number.isFinite(offsetParam) ? Math.max(offsetParam, 0) : 0;

  try {
    const signals = getSignals(limit, offset);
    res.json({
      data: signals,
      meta: {
        count: signals.length,
        limit,
        offset,
      },
    });
  } catch (error) {
    console.error("Error fetching signals:", error);
    res.status(500).json({
      error: "Failed to load signals",
    });
  }
});

app.get("/api/signals/latest", (req, res) => {
  const afterIdParam = parseInt(req.query.afterId, 10);
  if (!Number.isFinite(afterIdParam)) {
    return res.status(400).json({ error: "afterId query parameter is required" });
  }

  try {
    const db = new Database(databasePath, {
      readonly: true,
      fileMustExist: true,
    });
    db.pragma("busy_timeout = 3000");

    const stmt = db.prepare(`
      SELECT 
        id,
        timestamp,
        symbol,
        price,
        change_pct,
        tr_atr,
        z_score,
        signal_type,
        asset_class
      FROM signals
      WHERE id > ?
      ORDER BY id ASC
      LIMIT ?
    `);

    const rows = stmt.all(afterIdParam, MAX_LIMIT);
    db.close();

    res.json({
      data: rows,
      meta: {
        count: rows.length,
        afterId: afterIdParam,
      },
    });
  } catch (error) {
    console.error("Error fetching latest signals:", error);
    res.status(500).json({
      error: "Failed to load latest signals",
    });
  }
});

app.listen(serverPort, () => {
  console.log(`Investor chat API listening on http://localhost:${serverPort}`);
  console.log(`Using database at ${databasePath}`);
});

