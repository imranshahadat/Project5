# 4. Rate Limiting

## The Problem
A single user (or a buggy script) could send 1,000 upload requests per second. 

## Why It's Bad
- Your cloud providers (AWS, Pinecone, OpenAI) will instantly block your account for suspicious activity.
- You will wake up to a massive, unexpected cloud bill.

## The Fix
We added **SlowAPI**, a rate-limiting tool. 
We set a safe limit (for example, 10 uploads per minute per user). If a user tries to upload an 11th file within that minute, the app safely rejects the request with a `429 Too Many Requests` error, protecting your wallet and servers.

## How to Use It
The rate limiter is automatically applied to sensitive endpoints (like `/documents/upload`). 
You can adjust the limit in `src/app/api/v1/documents.py` by changing this line:
```python
@limiter.limit("10/minute") # Change to "50/hour" or whatever is safe for your budget