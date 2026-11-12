# 7. Frontend Contract Testing

## The Problem
We spent a lot of time fixing the backend, but if the frontend tries to use it and something is slightly wrong (like a missing header or a changed URL), the whole app breaks for the user. Manual testing is slow and misses things.

## Why It's Bad
- Bugs slip into production.
- Developers waste time guessing if the frontend and backend are actually talking to each other correctly.

## The Fix
We created **Frontend Contract Tests** (`tests/test_frontend_contract.py`). These are automated robot tests that pretend to be the frontend. They test the exact sequence of actions a real user would take: checking CORS, trying to access without a token, uploading a file, and triggering the rate limit.

## How to Use It
Whenever you make a change to the backend, run this command in your terminal:
```bash
pytest tests/test_frontend_contract.py -v