# 6. Memory Leaks & Stale Credentials

## The Problem
To make the app fast, we use `@lru_cache` to save things like database connections and API keys in the server's memory. However, if you change your API key in the `.env` file, the app keeps using the old, saved key until you completely restart the server.

## Why It's Bad
- If your API keys rotate (which is a good security practice), the app will suddenly start failing.
- Over a long time, cached items can cause memory leaks, slowing down the server.

## The Fix
We created a central "Cache Invalidation" tool (`src/app/core/cache.py`). This tool safely clears all saved connections and settings, forcing the app to load the fresh, updated ones from your `.env` file.

## How to Use It
We added a special admin-only endpoint: `POST /health/reload-config`. 
If you ever update your `.env` file, an admin can send a request to this endpoint. The app will instantly clear its memory and start using the new settings without needing a server restart.
 to clear cache.