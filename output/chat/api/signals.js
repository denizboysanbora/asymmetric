// Vercel serverless function for /api/signals
const MAX_LIMIT = 500;

export default function handler(req, res) {
  // Enable CORS
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const limitParam = parseInt(req.query.limit, 10);
  const offsetParam = parseInt(req.query.offset, 10);

  const limit = Number.isFinite(limitParam)
    ? Math.min(Math.max(limitParam, 1), MAX_LIMIT)
    : 100;
  const offset = Number.isFinite(offsetParam) ? Math.max(offsetParam, 0) : 0;

  // For Vercel deployment, we return empty data or connect to a cloud database
  // better-sqlite3 won't work on Vercel's serverless environment
  
  // TODO: Connect to a cloud database (Vercel Postgres, Planetscale, etc.)
  // or deploy the database API separately
  
  console.log(`Fetching signals with limit=${limit}, offset=${offset}`);
  
  // Return empty data for now - replace this with actual cloud DB connection
  res.json({
    data: [],
    meta: {
      count: 0,
      limit,
      offset,
      note: "Database connection not configured for Vercel deployment. Please set up a cloud database or deploy the API separately.",
    },
  });
}
