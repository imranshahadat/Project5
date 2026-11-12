# 1. Database Migrations & Async Database

## The Problem
In the old code, if you added a new column to your database or changed a data type, your live (production) app would crash because the database and your code were out of sync. Also, the database code was "synchronous," meaning it could only handle one request at a time, making the app slow under heavy traffic.

## Why It's Bad
- App crashes when you try to update the database.
- Risk of losing data.
- The app becomes slow and unresponsive when many users are online.

## The Fix
1. **Added Alembic**: This is a tool that tracks changes to your database. Instead of manually changing tables, you now generate a "migration" file. Alembic safely applies these changes to your database.
2. **Upgraded to Async SQLAlchemy**: We switched the database driver to `asyncpg`. This allows the app to handle hundreds of requests at the exact same time without waiting in line, making it much faster.

## How to Use It
Whenever you change a database model (like adding a new field to `models.py`), run these two commands in your terminal:
```bash
# 1. Create a record of the change
alembic revision --autogenerate -m "describe your change here"

# 2. Apply the change to the database
alembic upgrade head