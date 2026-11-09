-- Migration: add metadata JSONB column to documents table
-- Run this once against your Postgres database before using the upload endpoint.
--
-- Usage:
--   psql "$DATABASE_URL" -f scripts/migrate_add_metadata.sql
-- OR paste this into your Render dashboard SQL editor.

ALTER TABLE documents ADD COLUMN IF NOT EXISTS metadata JSONB;

-- Optional: backfill existing rows with a default so NULLs don't cause issues.
UPDATE documents SET metadata = '{"tenant_id": "public", "tags": []}'::jsonb
WHERE metadata IS NULL;

-- Verify:
-- SELECT id, title, status, metadata FROM documents LIMIT 5;
