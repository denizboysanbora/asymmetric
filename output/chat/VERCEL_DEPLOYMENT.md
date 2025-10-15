# Vercel Deployment Guide

## Issues Fixed

### 1. **Missing Vercel Configuration**
- ✅ Created `vercel.json` with proper build and routing configuration
- ✅ Set output directory to `dist` (Vite's default build output)
- ✅ Configured API rewrites for serverless functions

### 2. **Backend API Migration**
- ✅ Migrated Express API endpoints to Vercel serverless functions
- ✅ Created `/api/signals.js` and `/api/signals/latest.js`
- ✅ Added CORS headers for cross-origin requests

### 3. **Database Issue (Critical)**

**Problem**: The original backend uses `better-sqlite3`, which is a **native Node.js module** that won't work on Vercel's serverless environment.

**Current Status**: API endpoints now return empty data with a note about database configuration.

**Solutions** (choose one):

#### Option A: Use Vercel Postgres (Recommended)
1. Set up [Vercel Postgres](https://vercel.com/docs/storage/vercel-postgres)
2. Migrate your SQLite schema to Postgres
3. Update the API functions to use `@vercel/postgres`:
   ```javascript
   import { sql } from '@vercel/postgres';
   
   export default async function handler(req, res) {
     const { rows } = await sql`
       SELECT * FROM signals 
       ORDER BY timestamp DESC 
       LIMIT ${limit} OFFSET ${offset}
     `;
     res.json({ data: rows });
   }
   ```

#### Option B: Use Planetscale or Other Cloud Database
1. Set up a MySQL/Postgres database on Planetscale, Railway, or Supabase
2. Add connection string to Vercel environment variables
3. Update API functions to connect to your cloud database

#### Option C: Deploy Backend Separately
1. Deploy the Express server (`server/index.js`) to:
   - Railway
   - Render
   - Fly.io
   - Digital Ocean
2. Update Vite config to proxy to your deployed backend URL
3. Add backend URL to Vercel environment variables

#### Option D: Use sql.js (JavaScript SQLite)
1. Install `sql.js`: `npm install sql.js`
2. Upload the database file to Vercel Blob Storage or similar
3. Load database in memory (note: cold starts will be slow)

## Deployment Steps

### 1. Install Vercel CLI
```bash
npm install -g vercel
```

### 2. Deploy from the chat directory
```bash
cd /Users/deniz/Code/asymmetric/chat
vercel
```

### 3. Configure Environment Variables (if using cloud database)
In your Vercel dashboard, add:
- `DATABASE_URL` - Your database connection string
- Any other required environment variables

### 4. Deploy
```bash
vercel --prod
```

## What Works Now

✅ **Frontend**: React app will build and deploy successfully  
✅ **Routing**: SPA routing is configured correctly  
✅ **API Endpoints**: Serverless functions are set up  
⚠️ **Database**: Returns empty data (needs configuration)

## Files Created/Modified

- `vercel.json` - Vercel configuration
- `.vercelignore` - Files to exclude from deployment
- `api/signals.js` - Serverless function for /api/signals
- `api/signals/latest.js` - Serverless function for /api/signals/latest

## Next Steps

1. Choose a database solution from the options above
2. Implement the database connection in the API functions
3. Test locally using `vercel dev`
4. Deploy to production with `vercel --prod`

## Testing Locally

```bash
# Install Vercel CLI if not already installed
npm install -g vercel

# Link to your Vercel project
vercel link

# Run development server with serverless functions
vercel dev
```

This will start a local server that mimics Vercel's production environment, including the serverless functions.

## Common Issues

### Issue: "Cannot find module 'better-sqlite3'"
**Solution**: The current API functions don't use better-sqlite3 anymore. If you see this error, make sure you're using the updated API files.

### Issue: API returns empty data
**Solution**: This is expected until you configure a cloud database connection.

### Issue: 404 on API routes
**Solution**: Make sure your `vercel.json` rewrites are configured correctly and redeploy.

## Support

If you encounter issues:
1. Check Vercel deployment logs: `vercel logs`
2. Test locally first: `vercel dev`
3. Verify environment variables are set in Vercel dashboard



