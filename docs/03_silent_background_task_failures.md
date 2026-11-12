# 3. Silent Background Task Failures

## The Problem
When a user uploaded a document, the app handed the heavy lifting (reading the file, creating AI embeddings) to a "background task." If this task failed (e.g., the file was corrupted), the app just logged the error silently. The user's screen would say "Uploading..." forever.

## Why It's Bad
- Terrible user experience (the app looks broken).
- Wasted storage space.
- No way for the user or developer to know *why* it failed or how to fix it.

## The Fix
We updated the background ingestion code to catch errors properly. 
Now, if a task fails:
1. The document status in the database is changed to `"failed"`.
2. The exact error message is saved in the document's metadata.
3. The frontend can now read this status and show the user: *"Upload failed: File is corrupted. Please try again."*

## How to Use It
No extra steps needed. The frontend can now check the `GET /documents/{id}` endpoint. If `status` is `"failed"`, it can display the `error_message` to the user and offer a "Retry" button.