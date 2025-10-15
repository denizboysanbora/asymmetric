// Vercel serverless function for /api/signals/latest
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

  const afterIdParam = parseInt(req.query.afterId, 10);
  if (!Number.isFinite(afterIdParam)) {
    return res.status(400).json({ error: "afterId query parameter is required" });
  }

  // For Vercel deployment, we return empty data or connect to a cloud database
  // better-sqlite3 won't work on Vercel's serverless environment
  
  // TODO: Connect to a cloud database (Vercel Postgres, Planetscale, etc.)
  // or deploy the database API separately
  
  console.log(`Fetching latest signals after ID=${afterIdParam}`);
  
  // Return empty data for now - replace this with actual cloud DB connection
  res.json({
    data: [],
    meta: {
      count: 0,
      afterId: afterIdParam,
      note: "Database connection not configured for Vercel deployment. Please set up a cloud database or deploy the API separately.",
    },
  });
}
